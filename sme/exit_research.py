"""Prespecified target and causal trailing-stop comparisons, separate from optimization."""
import argparse
import bisect
import hashlib
import json
import math
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from . import optimize as opt,research,study2010 as study
from .analytics import summarize
from .data import ValidatedSeries,load_csv,quality
from .engine import Engine
from .opt_features import PatternEngine

OUT=study.ROOT/'output'/'exit-research'
VARIANTS=[
    dict(id='TP-200',extension=2,trail=None,runner=False),
    dict(id='TP-100',extension=1,trail=None,runner=False),
    dict(id='TP-200-trail-1R',extension=2,trail='R',distance=1,runner=False),
    dict(id='TP-100-trail-1R',extension=1,trail='R',distance=1,runner=False),
    dict(id='runner-1R',extension=2,trail='R',distance=1,runner=True),
    dict(id='runner-2R',extension=2,trail='R',distance=2,runner=True),
    dict(id='runner-ATR2',extension=2,trail='ATR',distance=2,runner=True),
    dict(id='runner-ATR3',extension=2,trail='ATR',distance=3,runner=True)]


class ExitEngine(PatternEngine):
    def __init__(self,*args,exit_policy=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.exit_policy=exit_policy or VARIANTS[0]

    def advance(self,s,i):
        super().advance(s,i)
        if self.exit_policy['extension']!=2 and s.get('fibonacci_index')==i:
            f=s['fibonacci']
            target=s['endpoint']+s['direction']*self.exit_policy['extension']*f['range']
            f.update(target=target,target_label='-1.0');s['target']=target
            for event in self.events:
                if event.get('setup_id')==s['id'] and event.get('index')==i:
                    if 'target' in event:event['target']=target
                    if 'target_label' in event:event['target_label']='-1.0'
            if s['id'] in self.feature_rows:
                self.feature_rows[s['id']]['reward_risk']=abs(target-s['entry'])/abs(s['entry']-s['stop'])

    def execute_pending(self,s,i):
        target=s['target'];before=len(self.trades)
        if self.exit_policy['runner']:s['target']=math.inf*s['direction']
        try:super().execute_pending(s,i)
        finally:s['target']=target
        if len(self.trades)>before:
            t=self.trades[-1]
            t.update(initial_stop=t['stop'],target=target,target_active=not self.exit_policy['runner'])
            t.update(potential_reward_price=abs(target-t['entry']),
                     potential_reward_pips=abs(target-t['entry'])/self.c.pip_size,
                     reward_risk=abs(target-t['entry'])/t['initial_risk_price'])

    def update_trail(self,t,i):
        p=self.exit_policy
        # Fill-bar extrema cannot be ordered relative to an intrabar limit fill.
        if not p['trail'] or i-1<=t['entry_index']:return
        previous=self.bars[i-1];d=t['direction'];risk=t['initial_risk_price']
        liquidation=previous.close if d==1 else previous.close+self.c.spread
        if d*(liquidation-t['entry'])>=risk:t['trail_activated']=True
        if not t.get('trail_activated'):return
        extreme=previous.high if d==1 else previous.low+self.c.spread
        watermark=t.get('trail_watermark',extreme)
        watermark=max(watermark,extreme) if d==1 else min(watermark,extreme)
        t['trail_watermark']=watermark
        if p['trail']=='R':distance=p['distance']*risk
        else:
            first=max(1,i-14)
            ranges=[max(self.bars[j].high-self.bars[j].low,
                        abs(self.bars[j].high-self.bars[j-1].close),
                        abs(self.bars[j].low-self.bars[j-1].close)) for j in range(first,i)]
            if not ranges:return
            distance=p['distance']*sum(ranges)/len(ranges)
        # Submit the ratchet after the previous close; it becomes active this bar.
        candidate=watermark-d*distance
        candidate=min(candidate,liquidation-self.c.pip_size) if d==1 else max(candidate,liquidation+self.c.pip_size)
        if d*(candidate-t['stop'])>0:
            t['stop']=candidate
            t.setdefault('trail_updates',[]).append(dict(active_from=self.stamp(i,False),
                known_at=self.stamp(i-1),stop=candidate))

    def execute_open(self,t,i):
        self.update_trail(t,i)
        target=t['target']
        if self.exit_policy['runner']:t['target']=math.inf*t['direction']
        try:super().execute_open(t,i)
        finally:t['target']=target
        if t['status']=='Closed' and t['exit_reason']=='stop_loss':
            t['trailing_stop_exit']=t['stop']!=t['initial_stop']


def simulate_exit(bars,config,symbol,conversion,policy,activation=None,flatten=False,time_cache=None,rate_cache=None):
    e=ExitEngine(config,symbol,conversion=conversion,exit_policy=policy,activation=activation,
                 time_cache=time_cache,rate_cache=rate_cache)
    r=e.run(bars)
    if flatten:
        for t in list(e.open_trades):
            price=bars[-1].close if t['direction']==1 else bars[-1].close+config.spread
            e.close_trade(t,len(bars)-1,price,'validation_boundary')
        r['equity'][-1].update(balance=e.balance,equity=e.balance)
    if activation:
        r['equity']=[p for p in r['equity'] if p['time']>activation.isoformat()]
        r['quality']=quality([b for b in bars if b.time>=activation])
    r['metrics']=summarize(r);r['exit_policy']=policy
    return r


def save_run(path,result):
    # Metrics retain every H1 mark; saved display curves are sampled to bound storage.
    stride=max(1,len(result['equity'])//1000)
    display=result['equity'][::stride]
    if display and display[-1]!=result['equity'][-1]:display.append(result['equity'][-1])
    stored={k:v for k,v in result.items() if k not in ('fast','slow','events','equity')}
    stored.update(equity=display,equity_note='Display curve sampled to approximately 1,000 marks; metrics use all H1 marks. Full setups/trades and trailing updates retained.')
    study.write_json(path,stored)


def run_asset(symbol):
    research.DATA=opt.DATA
    key=hashlib.sha256((opt.signature(symbol)+json.dumps(VARIANTS,sort_keys=True)).encode()+__file_bytes()).hexdigest()
    path=OUT/'assets'/symbol/'study.json'
    if path.exists() and json.loads(path.read_text())['signature']==key:
        print(symbol,'exit study reused',flush=True);return
    bars=ValidatedSeries(load_csv(opt.DATA/f'{symbol}.csv'));base=opt.asset_base(symbol)
    converter=research.currency_converter(symbol,{})
    times=[b.time for b in bars];stamps=[(b.time+timedelta(hours=1)).isoformat() for b in bars]
    rate_engine=Engine(base,symbol,conversion=converter)
    rates={b.time:(rate_engine.rate(b,True),rate_engine.rate(b)) for b in bars} if converter else None
    rows=[]
    start=datetime(2024,1,1,tzinfo=timezone.utc)
    first=bisect.bisect_left(times,start);warm=max(0,first-5*base.slow_period)
    recent=ValidatedSeries(bars[warm:])
    valid,reason=opt.window_ok([b for b in bars if b.time>=start],start,study.END)
    for policy in VARIANTS:
        c=base  # The separate exit_policy overrides the experimental target; core Config stays unchanged.
        full=simulate_exit(bars,c,symbol,converter,policy,time_cache=stamps,rate_cache=rates)
        save_run(OUT/'runs'/symbol/(policy['id']+'.json'),full)
        record=dict(instrument=symbol,asset_class=opt.asset_class(symbol),variant=policy['id'],
                    full_history=opt.flat_metrics(full['metrics']),recent=None,recent_exclusion=reason)
        if valid:
            r=simulate_exit(recent,c,symbol,converter,policy,activation=start,flatten=True,
                            time_cache=stamps[warm:],rate_cache=rates)
            record['recent']=opt.flat_metrics(r['metrics'])
            save_run(OUT/'recent'/symbol/(policy['id']+'.json'),r)
        rows.append(record)
        print(symbol,policy['id'],'full',round(record['full_history']['return_percent'],2),
              'recent',round(record['recent']['return_percent'],2) if valid else 'excluded',flush=True)
    study.write_json(path,dict(instrument=symbol,signature=key,rows=rows))


def __file_bytes():
    from pathlib import Path
    return Path(__file__).read_bytes()


def report():
    rows=[];missing=[]
    for symbol in opt.UNIVERSE:
        path=OUT/'assets'/symbol/'study.json'
        if not path.exists():missing.append(symbol);continue
        rows+=json.loads(path.read_text())['rows']
    study.write_json(OUT/'summary.json',dict(results=rows,missing=missing))
    flat=[]
    for row in rows:
        for period in ['full_history','recent']:
            m=row[period]
            if m:flat.append(dict(instrument=row['instrument'],asset_class=row['asset_class'],variant=row['variant'],period=period,**m))
    research.export_csv(OUT/'summary.csv',flat)
    lines=['# Target −100 and trailing-stop study','',
      'Exit-only comparisons retain the original 126/252 SMA OPEN entry rules, 1% risk sizing and costs. −100 means endpoint plus one swing range; −200 means plus two. All eight alternatives are prespecified comparisons, not validated optimized recommendations.',
      '', 'Trailing policies activate only after a completed post-entry candle closes at least +1 initial R. They ratchet from subsequent completed-bar highs/lows by 1R, 2R, or 2/3 times the last 14 bars’ simple mean true range. Fill-bar extrema are excluded. Stops never loosen, are clamped outside the last liquidation close by one pip, and become active on the next bar. Gap/slippage and stop-first ambiguity rules remain. Runner variants remove the take-profit; fixed-target variants keep it.',
      '', 'Full-history accounts carry positions continuously and include end-date MTM. The separate recent period starts flat on 2024-01-01 with historical MA warm-up and a fresh crossover, then liquidates at the cutoff. It is retrospective, not an untouched holdout. Full-history coverage differs; missing-data caveats from the baseline study apply. Gapped recent windows are excluded. Costs exclude financing/funding and commodity roll.',
      '', '| Instrument | Exit policy | Full return % | Full DD % | Trades | Win % | Recent return % | Recent DD % |',
      '|---|---|---:|---:|---:|---:|---:|---:|']
    for row in rows:
        m=row['full_history'];n=row['recent'] or {}
        vals=[row['instrument'],row['variant'],research.fmt(m['return_percent']),research.fmt(m['max_drawdown_percent']),
              m['completed_trades'],research.fmt(m['win_rate']*100),research.fmt(n.get('return_percent')),research.fmt(n.get('max_drawdown_percent'))]
        lines.append('| '+' | '.join(map(str,vals))+' |')
    lines+=['','Missing runs: '+json.dumps(missing),'']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Exit report',len(rows),'rows; missing',missing,flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','report']);p.add_argument('--symbols',nargs='+',choices=opt.UNIVERSE)
    args=p.parse_args()
    if args.action=='report':report()
    else:
        for symbol in args.symbols or opt.UNIVERSE:run_asset(symbol)


if __name__=='__main__':main()
