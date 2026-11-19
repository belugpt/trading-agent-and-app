"""Entry-known research features and explicitly experimental order filters."""
import math
import statistics
from datetime import timedelta
from .engine import Engine
from .analytics import summarize
from .data import quality

NUMERIC=['reward_risk','continuation','stop_range','swing_range','ma_separation',
         'aligned_slope','recent_volatility','cost_risk','setup_bars','impulse_bars']


def features(setup,bars,fast,slow,index,config):
    b=bars[index];d=setup['direction'];entry=setup['entry']
    recent=bars[max(0,index-47):index+1]
    typical=max(config.pip_size,sum(x.high-x.low for x in recent)/len(recent))
    returns=[math.log(recent[j].close/recent[j-1].close)*100 for j in range(1,len(recent))]
    risk=abs(entry-setup['stop']);span=setup['fibonacci']['range']
    stamp=b.time+timedelta(hours=1)
    slope=fast[max(0,index-24)]
    return dict(reward_risk=abs(setup['target']-entry)/risk,
        continuation=d*(setup['endpoint']-setup['breakout_price'])/span,
        stop_range=risk/typical,swing_range=span/typical,
        ma_separation=abs(fast[index]-slow[index])/typical,
        aligned_slope=d*(fast[index]-slope)/typical if slope is not None else 0.0,
        recent_volatility=statistics.pstdev(returns) if returns else 0.0,
        cost_risk=(config.spread+config.slippage+2*entry*config.commission_per_million/1e6)/risk,
        setup_bars=index-setup['crossover_index'],impulse_bars=setup['endpoint_index']-setup['origin_index'],
        direction=d,order_session=('Asia' if stamp.hour<7 else 'Europe' if stamp.hour<13 else 'US' if stamp.hour<21 else 'Late'),
        order_weekday=stamp.weekday(),known_at=stamp.isoformat())


def permits(rule,values):
    if not rule or rule.get('kind')=='all':return True
    if rule['kind']=='cash':return False
    if rule['kind']=='and':return all(permits(child,values) for child in rule['rules'])
    value=values.get(rule['feature'])
    if value is None:return False
    if rule['op']=='ge':return value>=rule['value']
    if rule['op']=='le':return value<=rule['value']
    if rule['op']=='in':return value in rule['value']
    raise ValueError('Unknown research filter operation')


class DiscardCurve(list):
    def append(self,value):pass


class PatternEngine(Engine):
    def __init__(self,*args,rule=None,activation=None,diagnostic=False,time_cache=None,rate_cache=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.rule=rule or {'kind':'all'};self.activation=activation;self.diagnostic=diagnostic
        self.feature_rows={};self.time_cache=time_cache;self.rate_cache=rate_cache
        if diagnostic:self.equity=DiscardCurve()

    def stamp(self,i,close=True):
        if close and self.time_cache is not None:return self.time_cache[i]
        return super().stamp(i,close)

    def rate(self,b,execution=False):
        if self.rate_cache is not None:return self.rate_cache[b.time][0 if execution else 1]
        return super().rate(b,execution)

    def event(self,s,state,i,at_open=False,**fields):
        if self.diagnostic:s['state']=state
        else:super().event(s,state,i,at_open=at_open,**fields)

    def new_setup(self,i,d):
        if self.activation is not None and self.bars[i].time<self.activation:return
        super().new_setup(i,d)

    def advance(self,s,i):
        super().advance(s,i)
        if s['state']=='PENDING_LIMIT_ORDER' and s.get('order_index')==i:
            f=features(s,self.bars,self.fast,self.slow,i,self.c)
            self.feature_rows[s['id']]=f
            if not permits(self.rule,f):self.cancel(s,i,'experimental_order_filter')


def simulate(bars,config,symbol,conversion,rule=None,activation=None,flatten=False,diagnostic=False,time_cache=None,rate_cache=None):
    engine=PatternEngine(config,symbol,conversion=conversion,rule=rule,activation=activation,
                         diagnostic=diagnostic,time_cache=time_cache,rate_cache=rate_cache)
    result=engine.run(bars)
    if flatten and engine.open_trades:
        last=len(bars)-1
        for trade in list(engine.open_trades):
            price=bars[-1].close if trade['direction']==1 else bars[-1].close+config.spread
            engine.close_trade(trade,last,price,'validation_boundary')
        if result['equity']:
            result['equity'][-1].update(balance=engine.balance,equity=engine.balance)
    if activation is not None:
        result['equity']=[p for p in result['equity'] if p['time']>(activation.isoformat())]
        result['quality']=quality([b for b in bars if b.time>=activation])
    if not diagnostic:result['metrics']=summarize(result)
    for trade in result['trades']:trade['entry_features']=engine.feature_rows[trade['setup_id']]
    result['experimental_order_filter']=engine.rule
    return result
