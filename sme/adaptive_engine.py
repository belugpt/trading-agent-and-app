"""Causal swing-stop exit research; optional experimental pre-entry filters."""
import bisect,calendar,math
from datetime import datetime,timedelta,timezone
from .swing_study import SwingEngine
from .analytics import summarize
from .data import TIMEFRAMES,quality

EXITS=['original','minus100','twoR','runner2R','atr3','partial1R_runner2R']
FILTERS=['higher','higher_trend','higher_liquid','higher_low_cost','higher_minimum_stop']

def session(stamp):
    """Post-2007 UK/US DST rules, UTC input; broad research windows, not an exchange calendar."""
    def sunday(month,n):
        days=[d for d in range(1,calendar.monthrange(stamp.year,month)[1]+1) if datetime(stamp.year,month,d).weekday()==6]
        return days[n]
    uk_start=datetime(stamp.year,3,sunday(3,-1),1,tzinfo=timezone.utc)
    uk_end=datetime(stamp.year,10,sunday(10,-1),1,tzinfo=timezone.utc)
    us_start=datetime(stamp.year,3,sunday(3,1),7,tzinfo=timezone.utc)
    us_end=datetime(stamp.year,11,sunday(11,0),6,tzinfo=timezone.utc)
    london=(stamp+timedelta(hours=int(uk_start<=stamp<uk_end))).hour
    ny=(stamp+timedelta(hours=-4 if us_start<=stamp<us_end else -5)).hour
    london_open=8<=london<16;ny_open=8<=ny<16
    return 'Overlap' if london_open and ny_open else 'London' if london_open else 'NewYork' if ny_open else 'Tokyo' if 9<=(stamp.hour+9)%24<17 else 'Other'

def allowed(name,f):
    if name.startswith('higher_'):return f['higher_aligned'] and allowed(name[7:],f)
    if name=='cash':return False
    if name=='all':return True
    if name=='trend':return f['trend']=='aligned'
    if name=='liquid':return f['session'] in ('London','NewYork','Overlap')
    if name=='low_cost':return f['cost_risk']<=.10
    if name=='minimum_stop':return f['risk_atr']>=1.0
    if name=='higher':return f['higher_aligned']
    if name=='higher_liquid':return f['higher_aligned'] and f['session'] in ('London','NewYork','Overlap')
    raise ValueError('Unknown filter')

class Discard(list):
    def append(self,value):pass

class AdaptiveEngine(SwingEngine):
    def __init__(self,*args,exit_name='original',gate='all',activation=None,diagnostic=False,times=None,rates=None,higher=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.exit_name=exit_name;self.gate=gate;self.activation=activation;self.diagnostic=diagnostic
        self.order_features={};self.times=times;self.rates=rates
        self.higher=higher
        if diagnostic:self.equity=Discard()

    def stamp(self,i,close=True):
        if close and self.times is not None:return self.times[i]
        return super().stamp(i,close)

    def rate(self,b,execution=False):
        if self.rates is not None:return self.rates[b.time][0 if execution else 1]
        return super().rate(b,execution)

    def event(self,s,state,i,at_open=False,**fields):
        if self.diagnostic:s['state']=state
        else:super().event(s,state,i,at_open=at_open,**fields)

    def new_setup(self,i,d):
        if self.activation is not None and self.bars[i].time<self.activation:return
        super().new_setup(i,d)

    def atr(self,i):
        first=max(1,i-13)
        values=[max(self.bars[j].high-self.bars[j].low,abs(self.bars[j].high-self.bars[j-1].close),abs(self.bars[j].low-self.bars[j-1].close)) for j in range(first,i+1)]
        return max(self.c.pip_size/10,sum(values)/len(values)) if values else self.c.pip_size

    def higher_side(self,stamp):
        if not self.higher:return 0
        stamps,sides=self.higher;at=bisect.bisect_right(stamps,stamp)-1
        return sides[at] if at>=0 else 0

    def advance(self,s,i):
        super().advance(s,i)
        if s['state']!='PENDING_LIMIT_ORDER' or s.get('order_index')!=i:return
        atr=self.atr(i);risk=abs(s['entry']-s['stop']);d=s['direction']
        slope=d*(self.fast[i]-self.fast[max(0,i-24)])/atr
        separation=abs(self.fast[i]-self.slow[i])/atr
        f=dict(session=session(self.bars[i].time+timedelta(seconds=TIMEFRAMES[self.timeframe])),
               trend='aligned' if slope>=.5 and separation>=.5 else 'weak',slope=slope,separation=separation,
               risk_atr=risk/atr,volatility_percent=atr/self.bars[i].close*100,
               cost_risk=(self.c.spread+self.c.slippage+2*s['entry']*self.c.commission_per_million/1e6)/risk,
               known_at=self.stamp(i),direction=d,
               higher_aligned=self.higher_side(self.bars[i].time+timedelta(seconds=TIMEFRAMES[self.timeframe]))==d and d*(self.fast[i]-self.slow[i])>0)
        self.order_features[s['id']]=f
        if not allowed(self.gate,f):self.cancel(s,i,'experimental_entry_filter');return
        if self.exit_name=='minus100':s['target']=s['endpoint']+d*s['fibonacci']['range']
        elif self.exit_name=='twoR':s['target']=s['entry']+d*2*risk
        s['fibonacci']['target']=s['target']

    def runner(self):return self.exit_name in ('runner2R','atr3','partial1R_runner2R')

    def execute_pending(self,s,i):
        if self.gate.startswith('higher') and (self.higher_side(self.bars[i].time)!=s['direction'] or i<1 or s['direction']*(self.fast[i-1]-self.slow[i-1])<=0):
            self.cancel(s,i,'higher_timeframe_alignment_lost',at_open=True);return
        target=s['target'];count=len(self.trades)
        if self.runner():s['target']=math.inf*s['direction']
        try:super().execute_pending(s,i)
        finally:s['target']=target
        if len(self.trades)>count:
            t=self.trades[-1];t.update(initial_stop=t['stop'],target=target,entry_features=self.order_features[s['id']],
                original_units=t['units'],partial_gross=0.0,partial_spread=0.0,target_active=not self.runner())
            t.update(potential_reward_price=abs(target-t['entry']),potential_reward_pips=abs(target-t['entry'])/self.c.pip_size,reward_risk=abs(target-t['entry'])/t['initial_risk_price'])

    def trail(self,t,i):
        if not self.runner() or i-1<=t['entry_index']:return
        b=self.bars[i-1];d=t['direction'];risk=t['initial_risk_price']
        liquidation=b.close if d==1 else b.close+self.c.spread
        if d*(liquidation-t['entry'])>=risk:t['trail_active']=True
        if not t.get('trail_active'):return
        extreme=b.high if d==1 else b.low+self.c.spread
        old=t.get('watermark',extreme);watermark=max(old,extreme) if d==1 else min(old,extreme);t['watermark']=watermark
        distance=3*self.atr(i-1) if self.exit_name=='atr3' else 2*risk
        candidate=watermark-d*distance
        candidate=min(candidate,liquidation-self.c.pip_size/10) if d==1 else max(candidate,liquidation+self.c.pip_size/10)
        if d*(candidate-t['stop'])>0:t['stop']=candidate

    def partial(self,t,i):
        if self.exit_name!='partial1R_runner2R' or t.get('partial_taken'):return
        b=self.bars[i];d=t['direction'];trigger=t['entry']+d*t['initial_risk_price']
        touch=b.high>=trigger if d==1 else b.low+self.c.spread<=trigger
        if not touch:return
        units=t['units']*.5;rate=self.rate(b,True);gross=d*(trigger-t['entry'])*units*rate
        fee=units*trigger*rate*self.c.commission_per_million/1e6
        self.balance+=gross-fee;t['commission']+=fee;t['units']-=units;t['partial_gross']+=gross
        if d==-1:t['partial_spread']+=units*self.c.spread*rate
        t['partial_taken']=True;t['partial_exit']=dict(time=self.stamp(i),price=trigger,units=units,gross=gross,commission=fee)

    def execute_open(self,t,i):
        self.trail(t,i);target=t['target']
        if self.runner():t['target']=math.inf*t['direction']
        try:super().execute_open(t,i)
        finally:t['target']=target
        # Conservative: stop-first bar processing precedes partial credit; no fill-bar partials.
        if t['status']=='Open':self.partial(t,i)

    def close_trade(self,t,i,price,reason):
        super().close_trade(t,i,price,reason)
        gross=t.get('partial_gross',0)
        if gross:
            t['gross_price_pnl']+=gross;t['pnl']+=gross;t['r_multiple']=t['pnl']/t['initial_risk'];t['return_percent']=100*t['pnl']/t['balance_at_entry']
            t['spread_cost']+=t.get('partial_spread',0);t['total_costs']=t['commission']+t['spread_cost']+t['slippage_cost']

def simulate(bars,config,symbol,conversion,tf='H1',exit_name='original',gate='all',activation=None,flatten=False,diagnostic=False,times=None,rates=None,higher=None):
    e=AdaptiveEngine(config,symbol,timeframe=tf,conversion=conversion,exit_name=exit_name,gate=gate,activation=activation,diagnostic=diagnostic,times=times,rates=rates,higher=higher)
    r=e.run(bars)
    if flatten:
        for t in list(e.open_trades):e.close_trade(t,len(bars)-1,bars[-1].close+(config.spread if t['direction']==-1 else 0),'validation_boundary')
        if r['equity']:r['equity'][-1].update(balance=e.balance,equity=e.balance)
    if activation:
        r['equity']=[p for p in r['equity'] if p['time']>activation.isoformat()]
        r['quality']=quality([b for b in bars if b.time>=activation],tf)
    if not diagnostic:r['metrics']=summarize(r)
    return r
