"""Source-aware crossover timing, next-bar eligible limits, conservative OHLC execution."""
from dataclasses import asdict
from datetime import timedelta
from .model import moving_average, crossover, fibonacci
from .data import quality, TIMEFRAMES, ValidatedSeries


class Engine:
    def __init__(self, config, instrument='EURUSD', timeframe='H1', conversion=None):
        config.validate()
        self.c = config
        self.instrument = instrument.upper()
        self.timeframe = timeframe
        self.conversion = conversion
        self.balance = config.initial_balance
        self.setups, self.trades, self.equity, self.events = [], [], [], []
        self.open_trades = []
        self.active = None
        self.bars = []

    def rate(self, b, execution=False):
        if self.instrument.endswith('USD'):
            return 1.0
        if self.instrument.startswith('USD'):
            return 1/(b.open if execution else b.close)
        if self.conversion is None:
            raise ValueError(f'{self.instrument}: historical quote-to-USD conversion series required')
        return self.conversion(b.time if execution else b.time+timedelta(seconds=TIMEFRAMES[self.timeframe]))

    def stamp(self, i, close=True):
        return (self.bars[i].time + timedelta(seconds=TIMEFRAMES[self.timeframe] if close else 0)).isoformat()

    def event(self, s, state, i, at_open=False, **fields):
        s['state'] = state
        self.events.append(dict(setup_id=s['id'], index=i, known_at=self.stamp(i,not at_open), state=state, **fields))

    def threshold(self, price):
        return self.c.retracement if self.c.retracement_mode == 'price' else abs(price)*self.c.retracement/100

    def cancel(self, s, i, reason, expired=False, at_open=False):
        s['reason'] = reason
        s['stage_at_cancellation'] = s['state']
        s['ended_index'] = i
        if s.get('order_status') == 'Pending':
            s['order_status'] = 'Expired' if expired else 'Cancelled'
        self.event(s, 'SETUP_CANCELLED', i, at_open=at_open, reason=reason)

    def new_setup(self, i, d):
        if self.active and self.active['state'] not in ('TRADE_OPEN','TRADE_COMPLETED','SETUP_CANCELLED'):
            self.cancel(self.active, i, 'opposite_crossover')
        b = self.bars[i]
        history = self.bars[max(0,i-self.c.lookback):i]
        s = dict(id=len(self.setups)+1, instrument=self.instrument, timeframe=self.timeframe,
                 direction=d, crossover_index=i, crossover_time=self.stamp(i,self.c.ma_source!='open'), crossover_candle=b.json(),
                 crossover_reference_known_at=self.stamp(i),
                 fast_ma=self.fast[i], slow_ma=self.slow[i], qualified=False,
                 stop=b.low-self.c.stop_buffer if d==1 else b.high+self.c.stop_buffer)
        self.setups.append(s)
        self.active = s
        self.event(s, 'CROSSOVER_DETECTED', i)
        if not history:
            self.cancel(s,i,'insufficient_structure_history')
            return
        extreme = max(history,key=lambda x:x.high) if d==1 else min(history,key=lambda x:x.low)
        s['previous_price'] = extreme.high if d==1 else extreme.low
        s['previous_time'] = extreme.time.isoformat()
        s['previous_known_index'] = i
        self.event(s, 'WAITING_FOR_POST_CROSSOVER_STRUCTURE', i)

    def advance(self, s, i):
        b, d = self.bars[i], s['direction']
        extreme = b.high if d==1 else b.low
        opposite = b.low if d==1 else b.high
        state = s['state']
        if state == 'WAITING_FOR_POST_CROSSOVER_STRUCTURE':
            if d*(extreme-s['previous_price']) > 0:
                s.update(post_price=extreme,post_index=i,post_known_index=i)
                self.event(s,'WAITING_FOR_INITIAL_RETRACEMENT',i, price=extreme)
        elif state == 'WAITING_FOR_INITIAL_RETRACEMENT':
            if d*(extreme-s['post_price']) > 0:
                s.update(post_price=extreme,post_index=i,post_known_index=i)
            elif d*(s['post_price']-b.close) >= self.threshold(s['post_price']):
                s.update(retracement_index=i, origin=opposite,origin_index=i,
                         candidate=opposite,candidate_index=i)
                self.event(s,'WAITING_FOR_STRUCTURE_BREAKOUT',i, origin=opposite)
        elif state == 'WAITING_FOR_STRUCTURE_BREAKOUT':
            # Origin is known before breakout bar; its low/high sequence is unknowable.
            if d*(extreme-s['post_price']) > 0:
                s.update(breakout_index=i,breakout_time=self.stamp(i),breakout_high=b.high,
                         breakout_low=b.low,breakout_price=extreme,structure_broken=s['post_price'],
                         endpoint=extreme,endpoint_index=i,qualified=True)
                self.event(s,'TRACKING_BREAKOUT_IMPULSE',i, endpoint=extreme,origin=s['origin'])
            else:
                if d*(opposite-s['candidate']) < 0:
                    s.update(candidate=opposite,candidate_index=i)
                if self.c.origin_method == 'retracement_extreme':
                    s.update(origin=s['candidate'],origin_index=s['candidate_index'])
                elif d*(b.close-s['candidate']) >= self.threshold(s['candidate']):
                    s.update(origin=s['candidate'],origin_index=s['candidate_index'])
                    # A later reversal can confirm a more recent initiating pivot.
                    s.update(candidate=opposite,candidate_index=i)
        elif state == 'TRACKING_BREAKOUT_IMPULSE':
            if d*(extreme-s['endpoint']) > 0:
                s.update(endpoint=extreme,endpoint_index=i)
                self.event(s,'TRACKING_BREAKOUT_IMPULSE',i,endpoint=extreme,origin=s['origin'])
            elif d*(s['endpoint']-b.close) >= self.threshold(s['endpoint']):
                self.event(s,'WAITING_FOR_QUALIFYING_RETRACEMENT',i)
                f = fibonacci(s['origin'],s['endpoint'],d)
                s.update(fibonacci=f, fibonacci_index=i, fibonacci_time=self.stamp(i),
                         endpoint_time=self.bars[s['endpoint_index']].time.isoformat(),
                         entry=f['entry'], target=f['target'])
                self.event(s,'FIBONACCI_LEVELS_CONFIRMED',i,**f)
                if d*(s['entry']-s['stop']) <= 0:
                    self.cancel(s,i,'crossover_stop_on_wrong_side_of_entry')
                elif d*(b.close-s['entry']) <= 0:
                    # Already crossed midpoint before the order could exist. Never backfill.
                    self.cancel(s,i,'midpoint_passed_before_order_creation')
                else:
                    s.update(order_index=i,order_time=self.stamp(i),order_status='Pending')
                    self.event(s,'PENDING_LIMIT_ORDER',i,entry=s['entry'],stop=s['stop'],target=s['target'])

    def execute_pending(self, s, i):
        b,d,c = self.bars[i],s['direction'],self.c
        if c.expiry_bars and i-s['order_index'] > c.expiry_bars:
            self.cancel(s,i,'pending_expired',True)
            return
        touched = b.low+c.spread <= s['entry']-c.penetration if d==1 else b.high >= s['entry']+c.penetration
        if not touched:
            return
        stop_touch = b.low <= s['stop'] if d==1 else b.high+c.spread >= s['stop']
        target_touch = b.high >= s['target'] if d==1 else b.low+c.spread <= s['target']
        market_open = b.open+c.spread if d==1 else b.open
        marketable_at_open = d*(market_open-s['entry']) <= 0
        ambiguous = stop_touch or (target_touch and not marketable_at_open)
        if ambiguous and c.ambiguity == 'skip_entry':
            self.events.append(dict(setup_id=s['id'],index=i,known_at=self.stamp(i),state='AMBIGUOUS_ENTRY_SKIPPED'))
            s['skipped_ambiguous_bars'] = s.get('skipped_ambiguous_bars',0)+1
            return
        # Limit orders receive no assumed favourable gap improvement and never adverse entry slippage.
        entry = s['entry']
        rate = self.rate(b,True)
        risk_distance = abs(entry-s['stop'])
        budget = self.balance*c.risk_percent/100
        unit_cost = (risk_distance+c.slippage)*rate + 2*entry*rate*c.commission_per_million/1e6
        units = budget/unit_cost if c.sizing=='risk_percent' else c.fixed_lots*c.contract_size if c.sizing=='fixed_lots' else c.fixed_units
        used = sum(t['units']*t['entry']*rate for t in self.open_trades)
        available = max(0,self.balance*c.max_leverage-used)
        units = min(units,available/(entry*rate))
        if self.balance <= 0 or units <= 0:
            self.cancel(s,i,'insufficient_equity_or_leverage')
            return
        fee = units*entry*rate*c.commission_per_million/1e6
        self.balance -= fee
        t = dict(id=len(self.trades)+1,setup_id=s['id'],instrument=self.instrument,timeframe=self.timeframe,
                 direction=d,entry=entry,stop=s['stop'],target=s['target'],units=units,
                 entry_index=i,entry_time=self.stamp(i,False),entry_time_precision=f'{self.timeframe} candle; intrabar time unknown',
                 crossover_time=s['crossover_time'],breakout_time=s['breakout_time'],
                 status='Open',initial_risk=units*risk_distance*rate,entry_conversion=rate,
                 initial_risk_price=risk_distance,potential_reward_price=abs(s['target']-entry),
                 initial_risk_pips=risk_distance/c.pip_size,potential_reward_pips=abs(s['target']-entry)/c.pip_size,
                 pip_size=c.pip_size,lots=units/c.contract_size,
                 reward_risk=abs(s['target']-entry)/risk_distance,
                 entry_commission=fee,commission=fee,spread_cost=units*c.spread*rate if d==1 else 0,
                 slippage_cost=0.0,mfe=0.0,mae=0.0,ambiguous_bars=int(ambiguous),
                 balance_at_entry=self.balance+fee)
        self.trades.append(t)
        self.open_trades.append(t)
        s.update(order_status='Filled',trade_id=t['id'],fill_index=i)
        self.event(s,'TRADE_OPEN',i,trade_id=t['id'])
        # Stop wins an ambiguous fill bar. A target is credited only if order filled at open.
        if stop_touch:
            stop_market = min(s['stop'],b.open) if d==1 else max(s['stop'],b.open+c.spread)
            self.close_trade(t,i,stop_market-d*c.slippage,'stop_loss')
        elif target_touch and marketable_at_open:
            self.close_trade(t,i,s['target'],'take_profit')

    def close_trade(self, t, i, price, reason):
        b,c,d = self.bars[i],self.c,t['direction']
        rate = self.rate(b,True)
        gross = d*(price-t['entry'])*t['units']*rate
        fee = t['units']*price*rate*c.commission_per_million/1e6
        t['commission'] += fee
        t['slippage_cost'] = t['units']*c.slippage*rate if reason=='stop_loss' else 0.0
        if d==-1:
            t['spread_cost'] = t['units']*c.spread*rate
        pnl = gross-t['commission']
        self.balance += gross-fee
        t.update(status='Closed',exit_index=i,exit_time=self.stamp(i),exit=price,exit_reason=reason,
                 gross_price_pnl=gross,pnl=pnl,r_multiple=pnl/t['initial_risk'],
                 profit_pips=d*(price-t['entry'])/c.pip_size,
                 return_percent=100*pnl/t['balance_at_entry'],
                 duration_hours=(self.bars[i].time-self.bars[t['entry_index']].time).total_seconds()/3600,
                 total_costs=t['commission']+t['spread_cost']+t['slippage_cost'])
        # Entry/exit-bar full extrema cannot be assigned an ordering. Excursions use known closes.
        t['mae'] = max(t['mae'],max(0,-d*(price-t['entry'])))
        t['mfe'] = max(t['mfe'],max(0,d*(price-t['entry'])))
        s = self.setups[t['setup_id']-1]
        self.event(s,'TRADE_COMPLETED',i,result=reason)
        self.open_trades.remove(t)

    def execute_open(self, t, i):
        b,c,d = self.bars[i],self.c,t['direction']
        stop = b.low <= t['stop'] if d==1 else b.high+c.spread >= t['stop']
        target = b.high >= t['target'] if d==1 else b.low+c.spread <= t['target']
        if stop and target:
            t['ambiguous_bars'] += 1
        # At a gap open the first executable quote is known; otherwise stop-first.
        opening = b.open if d==1 else b.open+c.spread
        if d*(opening-t['target']) >= 0:
            self.close_trade(t,i,t['target'],'take_profit')
        elif stop:
            price = min(opening,t['stop']) if d==1 else max(opening,t['stop'])
            self.close_trade(t,i,price-d*c.slippage,'stop_loss')
        elif target:
            self.close_trade(t,i,t['target'],'take_profit')
        else:
            liquidation = b.close if d==1 else b.close+c.spread
            movement = d*(liquidation-t['entry'])
            t['mfe'] = max(t['mfe'],movement)
            t['mae'] = max(t['mae'],-movement)

    def run(self, bars):
        if self.bars:
            raise ValueError('Create a fresh Engine for each run')
        q = bars.quality if isinstance(bars,ValidatedSeries) and bars.timeframe==self.timeframe else quality(bars,self.timeframe)
        if not q['valid']:
            raise ValueError('; '.join(q['errors'][:8]))
        self.bars = bars
        prices = [getattr(b,self.c.ma_source) for b in bars]
        self.fast = moving_average(prices,self.c.fast_period,self.c.fast_type)
        self.slow = moving_average(prices,self.c.slow_period,self.c.slow_type)
        last_side = None
        for i,b in enumerate(bars):
            self.rate(b)  # Fail before reporting results if conversion is unavailable.
            direction = 0
            if self.fast[i] is not None and self.slow[i] is not None:
                delta = self.fast[i]-self.slow[i]
                side = 1 if delta>0 else -1 if delta<0 else 0
                if last_side is not None and side and side!=last_side:
                    direction = side
                if side:
                    last_side = side
            # Open-price MAs are available at open. Cancel before a possible same-bar fill.
            # The fresh setup is finalized at close, when its candle stop reference is known.
            if self.c.ma_source=='open' and direction and self.active and self.active['state'] not in ('TRADE_OPEN','TRADE_COMPLETED','SETUP_CANCELLED'):
                self.cancel(self.active,i,'opposite_crossover',at_open=True)
            for t in list(self.open_trades):
                self.execute_open(t,i)
            s = self.active
            if s and s['state']=='PENDING_LIMIT_ORDER' and i>s['order_index']:
                self.execute_pending(s,i)
            if direction:
                self.new_setup(i,direction)
            elif s and s['state'] not in ('SETUP_CANCELLED','TRADE_OPEN','TRADE_COMPLETED','PENDING_LIMIT_ORDER'):
                self.advance(s,i)
            unrealized = 0.0
            for t in self.open_trades:
                liquidation = b.close if t['direction']==1 else b.close+self.c.spread
                unrealized += t['direction']*(liquidation-t['entry'])*t['units']*self.rate(b)
                unrealized -= t['units']*liquidation*self.rate(b)*self.c.commission_per_million/1e6
            self.equity.append(dict(time=self.stamp(i),balance=self.balance,equity=self.balance+unrealized))
        if self.active and self.active['state'] not in ('TRADE_OPEN','TRADE_COMPLETED','SETUP_CANCELLED'):
            stage = self.active['state']
            self.active['unresolved_at_end'] = stage
            self.active['reason'] = {'WAITING_FOR_POST_CROSSOVER_STRUCTURE':'no_post_crossover_structure',
                'WAITING_FOR_INITIAL_RETRACEMENT':'no_initial_retracement','WAITING_FOR_STRUCTURE_BREAKOUT':'no_breakout',
                'TRACKING_BREAKOUT_IMPULSE':'no_qualifying_retracement','PENDING_LIMIT_ORDER':'pending_not_filled'}.get(stage,'unqualified')
        from .analytics import summarize
        result = dict(instrument=self.instrument,timeframe=self.timeframe,config=asdict(self.c),quality=q,
                      setups=self.setups,trades=self.trades,events=self.events,equity=self.equity,
                      fast=self.fast,slow=self.slow)
        result['metrics'] = summarize(result)
        return result
