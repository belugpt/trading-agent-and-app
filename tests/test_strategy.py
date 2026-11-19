import unittest
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from unittest.mock import patch
from sme.model import Bar, Config, moving_average, crossover, fibonacci
from sme.engine import Engine
from sme.data import quality


def fixture(bear=False):
    # Pre high=10, cross low=5; post=12, origin=8, breakout=13,
    # continuation=16, freeze at close=14, entry=12, target=32.
    prices=[(8,10,7,8),(8,9,6,7),(7,9,5,8),(9,12,8,11),
            (10,11,8,9),(10,13,9,12),(13,16,12.5,15),
            (15,15.5,13,14),(13,14,11.5,13),(14,33,13,32)]
    bars=[]
    for i,(o,h,l,c) in enumerate(prices):
        if bear:
            o,h,l,c=40-o,40-l,40-h,40-c
        bars.append(Bar(datetime(2020,1,1,tzinfo=timezone.utc)+timedelta(hours=i),o,h,l,c))
    return bars


def controlled(bars=None,bear=False,instrument='EURUSD',**kwargs):
    bars=bars or fixture(bear)
    c=Config(fast_period=2,slow_period=3,lookback=2,retracement_mode='price',retracement=1,
             commission_per_million=0,max_leverage=100,**kwargs)
    e=Engine(c,instrument)
    d=-1 if bear else 1
    fast=[-d,-d]+[d]*max(0,len(bars)-2)
    slow=[0]*len(bars)
    with patch('sme.engine.moving_average',side_effect=[fast,slow]):
        return e.run(bars)


class Rules(unittest.TestCase):
    def test_user_baseline_is_126_252_sma_open(self):
        c=Config()
        self.assertEqual((c.fast_period,c.slow_period,c.fast_type,c.slow_type,c.ma_source),(126,252,'SMA','SMA','open'))

    def test_ma_uses_open_prices(self):
        bars=fixture()
        e=Engine(Config(fast_period=2,slow_period=3,ma_source='open'))
        r=e.run(bars)
        self.assertEqual(r['fast'],moving_average([b.open for b in bars],2,'SMA'))

    def test_bullish_crossover(self):
        self.assertEqual(crossover(1,2,3,2),1)

    def test_bearish_crossover(self):
        self.assertEqual(crossover(3,2,1,2),-1)

    def test_no_cross_without_passage(self):
        self.assertEqual(crossover(3,2,4,2),0)

    def test_warmup_equality_is_not_a_crossover(self):
        prices=[1]*4+[2]*4+[1]*4
        bars=[Bar(fixture()[0].time+timedelta(hours=i),p,p+.1,p-.1,p) for i,p in enumerate(prices)]
        r=Engine(Config(fast_period=2,slow_period=3)).run(bars)
        self.assertEqual([s['direction'] for s in r['setups']],[-1])

    def test_equality_bridge_retains_strict_previous_side(self):
        bars=fixture()[:7]
        e=Engine(Config(fast_period=2,slow_period=3))
        with patch('sme.engine.moving_average',side_effect=[[-1,-1,0,0,1,1,1],[0]*7]):
            r=e.run(bars)
        self.assertEqual([s['crossover_index'] for s in r['setups']],[4])

    def test_sma_and_ema_are_causal_seeded(self):
        self.assertEqual(moving_average([1,2,3,4],3,'SMA'),[None,None,2,3])
        self.assertEqual(moving_average([1,2,3,6],3,'EMA'),[None,None,2,4])

    def test_crossover_never_automatically_trades(self):
        r=controlled(fixture()[:3])
        self.assertEqual(len(r['setups']),1)
        self.assertEqual(r['trades'],[])

    def test_crossover_stop_both_directions(self):
        for bear in (False,True):
            r=controlled(bear=bear)
            s=r['setups'][0]
            self.assertEqual(s['stop'],fixture(bear)[2].high if bear else fixture()[2].low)

    def test_previous_extreme_excludes_crossover(self):
        for bear,expected in [(False,10),(True,30)]:
            s=controlled(bear=bear)['setups'][0]
            self.assertEqual(s['previous_price'],expected)
            self.assertEqual(s['previous_time'],fixture(bear)[0].time.isoformat())

    def test_structure_retracement_breakout_order(self):
        r=controlled()
        s=r['setups'][0]
        self.assertLess(s['crossover_index'],s['post_index'])
        self.assertLess(s['post_index'],s['retracement_index'])
        self.assertLess(s['retracement_index'],s['breakout_index'])

    def test_wick_breakout_without_close_confirmation(self):
        bars=fixture()
        bars[5]=replace(bars[5],close=11)
        s=controlled(bars)['setups'][0]
        self.assertEqual(s['breakout_index'],5)
        self.assertLess(bars[5].close,s['structure_broken'])

    def test_equal_wick_not_breakout(self):
        bars=fixture()[:6]
        bars[5]=replace(bars[5],high=12)
        self.assertNotIn('breakout_index',controlled(bars)['setups'][0])

    def test_origin_is_retracement_extreme(self):
        s=controlled()['setups'][0]
        self.assertEqual(s['origin'],8)
        self.assertEqual(s['origin_index'],4)
        self.assertNotEqual(s['origin'],s['stop'])

    def test_dynamic_endpoint_and_freeze(self):
        s=controlled()['setups'][0]
        self.assertEqual(s['breakout_price'],13)
        self.assertEqual(s['endpoint'],16)
        self.assertEqual(s['endpoint_index'],6)
        self.assertEqual(s['fibonacci_index'],7)
        self.assertEqual(s['fibonacci']['endpoint'],16)

    def test_bearish_origin_endpoint(self):
        s=controlled(bear=True)['setups'][0]
        self.assertEqual(s['origin'],32)
        self.assertEqual(s['endpoint'],24)
        self.assertEqual(s['target'],8)

    def test_half_and_negative_two_fibonacci(self):
        self.assertEqual(fibonacci(8,16,1)['entry'],12)
        self.assertEqual(fibonacci(8,16,1)['target'],32)
        self.assertEqual(fibonacci(32,24,-1)['entry'],28)
        self.assertEqual(fibonacci(32,24,-1)['target'],8)

    def test_pending_exists_before_fill(self):
        r=controlled()
        s,t=r['setups'][0],r['trades'][0]
        self.assertEqual(s['order_index'],7)
        self.assertEqual(t['entry_index'],8)
        self.assertGreater(t['entry_index'],s['order_index'])
        self.assertEqual(t['entry'],12)

    def test_target_both_directions(self):
        for bear in (False,True):
            t=controlled(bear=bear)['trades'][0]
            self.assertEqual(t['exit_reason'],'take_profit')
            self.assertGreater(t['pnl'],0)

    def test_stop_execution(self):
        bars=fixture()
        bars[9]=Bar(bars[9].time,12,13,4,6)
        t=controlled(bars)['trades'][0]
        self.assertEqual(t['exit'],5)
        self.assertEqual(t['exit_reason'],'stop_loss')

    def test_ambiguous_open_trade_stop_first(self):
        bars=fixture()
        bars[9]=Bar(bars[9].time,13,33,4,10)
        t=controlled(bars)['trades'][0]
        self.assertEqual(t['exit_reason'],'stop_loss')
        self.assertGreater(t['ambiguous_bars'],0)

    def test_ambiguous_fill_stop_first(self):
        bars=fixture()
        bars[8]=Bar(bars[8].time,13,33,4,10)
        t=controlled(bars)['trades'][0]
        self.assertEqual(t['exit_reason'],'stop_loss')
        self.assertEqual(t['exit_index'],8)

    def test_ambiguous_skip_entry(self):
        bars=fixture()[:9]
        bars[8]=Bar(bars[8].time,13,33,4,10)
        r=controlled(bars,ambiguity='skip_entry')
        self.assertEqual(r['trades'],[])
        self.assertEqual(r['setups'][0]['skipped_ambiguous_bars'],1)

    def test_opposite_crossover_cancels_before_fill(self):
        bars=fixture()[:9]
        bars[8]=Bar(bars[8].time,14,15,13,14)
        fast=[-1,-1,1,1,1,1,1,1,-1]
        e=Engine(Config(fast_period=2,slow_period=3,lookback=2,retracement_mode='price',retracement=1))
        with patch('sme.engine.moving_average',side_effect=[fast,[0]*9]):
            r=e.run(bars)
        self.assertEqual(r['setups'][0]['reason'],'opposite_crossover')
        self.assertEqual(r['setups'][0]['order_status'],'Cancelled')
        self.assertEqual(len(r['setups']),2)
        self.assertEqual(r['trades'],[])

    def test_open_crossover_cancels_before_same_bar_limit_touch(self):
        bars=fixture()[:9]
        e=Engine(Config(fast_period=2,slow_period=3,lookback=2,retracement_mode='price',retracement=1))
        with patch('sme.engine.moving_average',side_effect=[[-1,-1,1,1,1,1,1,1,-1],[0]*9]):
            r=e.run(bars)
        self.assertEqual(r['trades'],[])
        cancelled=next(x for x in r['events'] if x['state']=='SETUP_CANCELLED')
        self.assertEqual(cancelled['known_at'],bars[8].time.isoformat())
        self.assertEqual(r['setups'][0]['order_status'],'Cancelled')

    def test_close_crossover_is_observed_after_intrabar_limit_touch(self):
        bars=fixture()[:9]
        e=Engine(Config(fast_period=2,slow_period=3,lookback=2,retracement_mode='price',retracement=1,ma_source='close'))
        with patch('sme.engine.moving_average',side_effect=[[-1,-1,1,1,1,1,1,1,-1],[0]*9]):
            r=e.run(bars)
        self.assertEqual(len(r['trades']),1)
        self.assertEqual(r['setups'][0]['order_status'],'Filled')

    def test_open_signal_precedes_completed_stop_reference(self):
        s=controlled()['setups'][0]
        self.assertEqual(s['crossover_time'],fixture()[2].time.isoformat())
        self.assertEqual(s['crossover_reference_known_at'],fixture()[3].time.isoformat())
        self.assertLess(s['crossover_reference_known_at'],s['order_time'])

    def test_prefix_invariance_no_future_decisions(self):
        full=controlled()
        for n in range(3,10):
            short=controlled(fixture()[:n])
            past=[event for event in full['events'] if event['index']<n]
            self.assertEqual(short['events'],past)
            self.assertEqual(short['equity'],full['equity'][:n])

    def test_no_retroactive_fill(self):
        bars=fixture()[:8]
        bars[7]=Bar(bars[7].time,15,15.5,10,11)
        r=controlled(bars)
        self.assertEqual(r['trades'],[])
        self.assertEqual(r['setups'][0]['reason'],'midpoint_passed_before_order_creation')

    def test_spread_prevents_touch_fill(self):
        bars=fixture()[:9]
        bars[8]=Bar(bars[8].time,13,14,12,13)
        self.assertEqual(controlled(bars,spread=.1)['trades'],[])

    def test_one_tick_penetration(self):
        bars=fixture()[:9]
        bars[8]=Bar(bars[8].time,13,14,12,13)
        self.assertEqual(controlled(bars,penetration=.01)['trades'],[])
        self.assertEqual(len(controlled(bars)['trades']),1)

    def test_commission_reduces_profit(self):
        baseline=controlled()['trades'][0]
        bars=fixture()
        e=Engine(Config(fast_period=2,slow_period=3,lookback=2,retracement_mode='price',retracement=1,commission_per_million=100))
        with patch('sme.engine.moving_average',side_effect=[[-1,-1]+[1]*8,[0]*10]):
            t=e.run(bars)['trades'][0]
        self.assertGreater(t['commission'],0)
        self.assertLess(t['pnl'],baseline['pnl'])

    def test_mandatory_rules_cannot_change(self):
        for field,value in [('entry_fraction',.6),('extension',1),('risk_percent',0)]:
            with self.assertRaises(ValueError):
                replace(Config(),**{field:value}).validate()

    def test_invalid_data(self):
        bars=fixture()
        for mutated in [[bars[1],bars[0]],[bars[0],bars[0]],
                        [replace(bars[0],low=20)],[replace(bars[0],time=datetime(2020,1,1))]]:
            self.assertFalse(quality(mutated)['valid'])

    def test_gap_report(self):
        self.assertEqual(quality([fixture()[0],fixture()[3]])['absent_intervals'],2)

    def test_no_implicit_cross_currency_conversion(self):
        with self.assertRaises(ValueError):
            Engine(Config(),'AUDJPY').run(fixture())

    def test_endpoint_never_freezes_on_new_high_candle(self):
        bars=fixture()[:8]
        bars[7]=Bar(bars[7].time,15,17,12,13)
        s=controlled(bars)['setups'][0]
        self.assertNotIn('fibonacci',s)
        self.assertEqual(s['endpoint'],17)

    def test_real_ma_full_run_prefix(self):
        bars=fixture()*1
        r=Engine(Config(fast_period=2,slow_period=3)).run(bars)
        for n in range(4,len(bars)):
            short=Engine(Config(fast_period=2,slow_period=3)).run(bars[:n])
            self.assertEqual(short['events'],[x for x in r['events'] if x['index']<n])

    def test_entry_sizing_uses_open_not_future_conversion_close(self):
        bars=fixture()[:9]
        altered=list(bars)
        altered[8]=replace(altered[8],close=13.9)
        first=controlled(bars,instrument='USDJPY')['trades'][0]
        second=controlled(altered,instrument='USDJPY')['trades'][0]
        self.assertEqual(first['units'],second['units'])
        self.assertEqual(first['entry_conversion'],1/bars[8].open)

    def test_fill_bar_target_not_assumed_after_entry(self):
        bars=fixture()[:9]
        bars[8]=Bar(bars[8].time,13,33,11,13)
        t=controlled(bars)['trades'][0]
        self.assertEqual(t['status'],'Open')
        self.assertEqual(t['ambiguous_bars'],1)

    def test_limit_never_fills_adversely_beyond_its_price(self):
        t=controlled(slippage=.5)['trades'][0]
        self.assertEqual(t['entry'],12)

    def test_no_chasing_without_midpoint_retracement(self):
        bars=fixture()[:8]
        bars.append(Bar(bars[-1].time+timedelta(hours=1),14,20,13,19))
        r=controlled(bars)
        self.assertEqual(r['trades'],[])
        self.assertEqual(r['setups'][0]['order_status'],'Pending')

    def test_no_qualifying_retracement_keeps_dynamic_impulse(self):
        s=controlled(fixture()[:7])['setups'][0]
        self.assertEqual(s['state'],'TRACKING_BREAKOUT_IMPULSE')
        self.assertNotIn('order_time',s)

    def test_invalid_crossover_stop_geometry_rejected(self):
        bars=fixture()[:8]
        bars[2]=replace(bars[2],open=13,low=12.5,high=14,close=13)
        r=controlled(bars)
        self.assertEqual(r['setups'][0]['reason'],'crossover_stop_on_wrong_side_of_entry')

    def test_latest_pivot_method_is_explicit(self):
        r=controlled(origin_method='latest_confirmed_pivot')
        self.assertEqual(r['setups'][0]['origin'],8)

    def test_fixed_lots(self):
        t=controlled(sizing='fixed_lots',fixed_lots=.001,contract_size=100000)['trades'][0]
        self.assertEqual(t['units'],100)

    def test_stop_gap_is_not_filled_at_stale_stop(self):
        bars=fixture()
        bars[9]=Bar(bars[9].time,3,4,2,3)
        t=controlled(bars,slippage=.1)['trades'][0]
        self.assertEqual(t['exit'],2.9)

    def test_no_breakout_without_initial_retracement(self):
        bars=fixture()[:5]
        bars[4]=Bar(bars[4].time,11,13,10,12)
        s=controlled(bars)['setups'][0]
        self.assertEqual(s['state'],'WAITING_FOR_INITIAL_RETRACEMENT')
        self.assertFalse(s['qualified'])


if __name__=='__main__':
    unittest.main()
