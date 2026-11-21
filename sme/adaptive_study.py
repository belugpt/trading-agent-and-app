"""Multi-timeframe research with mandatory confirmed higher-timeframe alignment."""
import argparse,bisect,hashlib,json,math,statistics
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
from . import optimize as opt,research,study2010 as study
from .adaptive_engine import simulate,EXITS,FILTERS
from .analytics import bootstrap,trade_stats,percentile
from .data import load_csv,ValidatedSeries,TIMEFRAMES
from .engine import Engine
from .model import moving_average
from .server import resample_h4
from .m15_history import DATA as M15

OUT=study.ROOT/'output'/'market-study'
TFS=['M15','H1','H4']

def plan():
    return dict(version='confirmed-alignment-1',timeframes=TFS,exits=EXITS,filters=FILTERS,
       mandatory='Swing-origin stop; SMA126/252 OPEN; midpoint limit; latest CLOSED higher SMA and closed lower SMA must agree before order creation and before fill.',
       higher={'M15':'H1','H1':'H4','H4':'UTC D1'},training='Six prior calendar years, minimum four actual years, 24h embargo; next two years frozen test; final 2026 partial',
       shortlist=2,min_training_trades=25,objective='Actual training CAGR / max(1%, MTM drawdown); positive return, mean R, PF>=1.05, two profitable years, no winner over 50% gross gains.',
       partial='Half at +1 initial R after fill bar, remaining runner with 2R trail; conservative stop-first before partial credit.',
       caveat='Retrospective research: prior history has already been inspected. Native M15 or real M1 aggregation only; not FBS costs/ticks or server candles. No averaging down or discretionary extra entries. At most one entry per setup; concurrent distinct setups remain possible under original engine leverage rules.')

def higher_series(bars,tf):
    step={'M15':3600,'H1':14400,'H4':86400}[tf]
    groups={}
    for b in bars:
        key=int(b.time.timestamp())//step*step
        if key not in groups:groups[key]=b.open
    keys=sorted(groups);prices=[groups[k] for k in keys]
    fast=moving_average(prices,126,'SMA');slow=moving_average(prices,252,'SMA')
    times=[datetime.fromtimestamp(k+step,timezone.utc) for k in keys]
    sides=[1 if a is not None and b is not None and a>b else -1 if a is not None and b is not None and a<b else 0 for a,b in zip(fast,slow)]
    return times,sides

def converter(symbol,tf):
    if symbol.endswith('USD') or symbol.startswith('USD'):return None
    quote=symbol[-3:];inverse=quote in ('JPY','CHF','CAD');reference='USD'+quote if inverse else quote+'USD'
    step=900 if tf=='M15' else 3600;folder=M15 if tf=='M15' else opt.DATA
    series=load_csv(folder/f'{reference}.csv');times=[b.time.timestamp()+step for b in series]
    def rate(stamp):
        at=bisect.bisect_right(times,stamp.timestamp())-1
        if at<0:
            if series and stamp==series[0].time:return 1/series[0].open if inverse else series[0].open
            raise ValueError('No past quote conversion '+reference+' at '+str(stamp))
        if stamp.timestamp()-times[at]>96*3600:raise ValueError('Stale conversion '+reference)
        return 1/series[at].close if inverse else series[at].close
    return rate

def signature(symbol):
    h=hashlib.sha256(json.dumps(plan(),sort_keys=True).encode())
    files=[M15/f'{symbol}.csv',M15/f'{symbol}.manifest.json',opt.DATA/f'{symbol}.csv']
    if not symbol.startswith('USD') and not symbol.endswith('USD'):
        q=symbol[-3:];ref='USD'+q if q in ('JPY','CHF','CAD') else q+'USD'
        files += [M15/f'{ref}.csv',opt.DATA/f'{ref}.csv']
    files += [Path(__file__),Path(__file__).with_name('adaptive_engine.py'),Path(__file__).with_name('swing_study.py'),Path(__file__).with_name('engine.py')]
    for p in files:h.update(p.read_bytes())
    return h.hexdigest()

def slim(r):return {k:v for k,v in r['metrics'].items() if not isinstance(v,(dict,list))}
def curve(r):
    points=r['equity'];stride=max(1,len(points)//120)
    return [dict(time=p['time'],equity=round(p['equity'],2)) for p in points[::stride]+[points[-1]]] if points else []

def movement_rows(result,bars,tf,symbol,gaps):
    rows=[]
    for t in result['trades']:
        if t['status']!='Closed':continue
        s=result['setups'][t['setup_id']-1];start=max(0,s['crossover_index']-504)
        if bisect.bisect_right(gaps,t['exit_index'])!=bisect.bisect_right(gaps,start):continue
        risk=t['initial_risk_price']
        if risk<=result['config']['pip_size']*1e-6:continue
        inside=bars[t['entry_index']+1:t['exit_index']];d=t['direction'];spread=result['config']['spread']
        mfe=max([0]+[d*((b.high if d==1 else b.low+spread)-t['entry'])/risk for b in inside])
        mae=max([0]+[-d*((b.low if d==1 else b.high+spread)-t['entry'])/risk for b in inside])
        follow=bars[t['exit_index']+1:t['exit_index']+21]
        rebound=max([0]+[d*((b.high if d==1 else b.low+spread)-t['entry'])/risk for b in follow])
        rows.append(dict(instrument=symbol,timeframe=tf,entry_time=t['entry_time'],exit_time=t['exit_time'],
                         r=t['r_multiple'],win=t['pnl']>0,exit_reason=t['exit_reason'],mfe_full_bars_r=mfe,mae_full_bars_r=mae,
                         favorable_1R=mfe>=1,favorable_2R=mfe>=2,favorable_3R=mfe>=3,
                         stopped_after_1R=t['exit_reason']=='stop_loss' and mfe>=1,
                         post_exit_20bar_favorable_r=rebound,**t['entry_features']))
    return rows

def run_asset(symbol):
    key=signature(symbol);folder=OUT/'assets'/symbol
    path=folder/'study.json'
    if path.exists() and json.loads(path.read_text())['signature']==key:print(symbol,'market study reused',flush=True);return
    base=opt.asset_base(symbol);hourly=load_csv(opt.DATA/f'{symbol}.csv')
    data={};cohorts=[];baselines=[];movement=[]
    for tf in TFS:
        bars=ValidatedSeries(load_csv(M15/f'{symbol}.csv') if tf=='M15' else hourly if tf=='H1' else resample_h4(hourly),tf)
        conv=converter(symbol,tf);higher=higher_series(hourly,tf)
        times=[b.time for b in bars];stamps=[(b.time+timedelta(seconds=TIMEFRAMES[tf])).isoformat() for b in bars]
        e=Engine(base,symbol,timeframe=tf,conversion=conv)
        rates={b.time:(e.rate(b,True),e.rate(b)) for b in bars} if conv else None
        gaps=[i for i in range(1,len(bars)) if (bars[i].time-bars[i-1].time).total_seconds()>7*86400]
        data[tf]=dict(bars=bars,times=times,stamps=stamps,conv=conv,rates=rates,higher=higher,gaps=gaps)
        for gate in ['all','higher']:
            r=simulate(bars,base,symbol,conv,tf,gate=gate,times=stamps,rates=rates,higher=higher)
            baselines.append(dict(instrument=symbol,timeframe=tf,alignment=gate,asset_class=opt.asset_class(symbol),metrics=slim(r),curve=curve(r),bars=len(bars),start=times[0].isoformat(),end=times[-1].isoformat()))
            if gate=='higher':movement+=movement_rows(r,bars,tf,symbol,gaps)
        for exit_name in EXITS:
            p=OUT/'cohorts'/symbol/(tf+'-'+exit_name+'.json');saved=json.loads(p.read_text()) if p.exists() else {}
            if saved.get('signature')==key:cohort=saved
            else:
                r=simulate(bars,replace(base,sizing='fixed_units',fixed_units=.000001),symbol,conv,tf,exit_name=exit_name,diagnostic=True,times=stamps,rates=rates,higher=higher)
                rows=[]
                for t in r['trades']:
                    if t['status']!='Closed' or t['initial_risk_price']<=base.pip_size*1e-6:continue
                    s=r['setups'][t['setup_id']-1];start=max(0,s['crossover_index']-504)
                    if bisect.bisect_right(gaps,t['exit_index'])!=bisect.bisect_right(gaps,start):continue
                    rows.append(dict(r=t['r_multiple'],entry_time=t['entry_time'],exit_time=t['exit_time'],crossover_time=t['crossover_time'],features=t['entry_features']))
                cohort=dict(signature=key,timeframe=tf,exit=exit_name,rows=rows);study.write_json(p,cohort)
            cohorts.append(cohort);print(symbol,tf,exit_name,'cohort',len(cohort['rows']),flush=True)
    def evaluate(tf,exit_name,gate,start,end,cost=1):
        q=data[tf];bars=q['bars'];first=bisect.bisect_left(q['times'],start);last=bisect.bisect_left(q['times'],end);warm=max(0,first-1260)
        c=replace(base,spread=base.spread*cost,slippage=base.slippage*cost,commission_per_million=base.commission_per_million*cost)
        return simulate(ValidatedSeries(bars[warm:last],tf),c,symbol,q['conv'],tf,exit_name=exit_name,gate=gate,activation=start,flatten=True,times=q['stamps'][warm:last],rates=q['rates'],higher=q['higher'])
    folds=[];exact_curves={}
    from .adaptive_engine import allowed
    for year in range(2016,2027,2):
        start=datetime(year,1,1,tzinfo=timezone.utc);end=min(datetime(year+2,1,1,tzinfo=timezone.utc),study.END)
        train=datetime(year-6,1,1,tzinfo=timezone.utc);cutoff=start-timedelta(days=1);eligible=[]
        for tf,q in data.items():
            a=[b for b in q['bars'] if train<=b.time<cutoff];b=[x for x in q['bars'] if start<=x.time<end]
            valid,reason=opt.window_ok(a,train,cutoff,True);validtest,reason_test=opt.window_ok(b,start,end)
            if valid and validtest and (a[-1].time-a[0].time).days>=4*365:eligible.append(tf)
        if 'H1' not in eligible:
            folds.append(dict(year=year,status='excluded',reason='Incomplete/gapped H1 comparator or less than four years training'));continue
        proposed=[];trials=0
        for c in cohorts:
            if c['timeframe'] not in eligible:continue
            rows=[r for r in c['rows'] if r['crossover_time']>=train.isoformat() and r['exit_time']<=cutoff.isoformat()]
            for gate in FILTERS:
                subset=sorted([r for r in rows if allowed(gate,r['features'])],key=lambda r:r['exit_time']);trials+=1
                score=opt.proxy(subset,6,min_trades=25)
                if score:proposed.append(dict(timeframe=c['timeframe'],exit=c['exit'],gate=gate,proxy=score))
        proposed.sort(key=lambda p:(-p['proxy']['score'],p['timeframe'],p['exit'],p['gate']))
        best=None;best_score=-math.inf;training_metrics=None
        for p in proposed[:2]:
            r=evaluate(p['timeframe'],p['exit'],p['gate'],train,cutoff);score=opt.actual_score(r)
            if r['metrics']['completed_trades']>=25 and score is not None and score>best_score:best=p;best_score=score;training_metrics=slim(r)
        best=best or dict(timeframe='H1',exit='original',gate='cash')
        r=evaluate(best['timeframe'],best['exit'],best['gate'],start,end)
        reference=evaluate('H1','original','higher',start,end)
        stress=evaluate(best['timeframe'],best['exit'],best['gate'],start,end,2)
        exact_curves[year,'selected']=[p['equity'] for p in r['equity']]
        exact_curves[year,'baseline']=[p['equity'] for p in reference['equity']]
        folds.append(dict(year=year,status='tested',train_start=train.isoformat(),selection_cutoff=cutoff.isoformat(),test_start=start.isoformat(),test_end=end.isoformat(),policy=best,training_metrics=training_metrics,trials=trials,
                          selected=slim(r),baseline=slim(reference),double_cost=slim(stress),selected_curve=curve(r),baseline_curve=curve(reference),selected_trades=r['trades'],baseline_trades=reference['trades']))
        print(symbol,'forward',year,best['timeframe'],best['exit'],best['gate'],round(r['metrics']['return_percent'],2),flush=True)
    def chain(field):
        wealth=10000.;points=[];worst=0.;peak=10000.;exact_dd=0.
        for f in folds:
            if f['status']!='tested':continue
            # Within-window DD remains exact in metrics. Chained DD bounds are reported separately.
            begin=wealth
            for value in exact_curves[f['year'],field]:
                value=begin*value/10000;peak=max(peak,value);exact_dd=max(exact_dd,100*(1-value/peak))
            for p in f[field+'_curve']:points.append(dict(time=p['time'],equity=round(begin*p['equity']/10000,2)))
            wealth*=1+f[field]['return_percent']/100
            worst=max(worst,f[field]['max_drawdown_percent'])
        peak=10000.;sample_dd=0.
        for p in points:peak=max(peak,p['equity']);sample_dd=max(sample_dd,100*(1-p['equity']/peak))
        return dict(return_percent=100*(wealth/10000-1),final_equity=wealth,curve=points,max_drawdown_percent=exact_dd,max_drawdown_sampled_percent=sample_dd,max_exact_fold_drawdown_percent=worst)
    valid=[f for f in folds if f['status']=='tested'];trades=[t for f in valid for t in f['selected_trades']]
    ordered=sorted(trades,key=lambda t:t['entry_time']);uncertainty=bootstrap([{**t,'entry_index':i} for i,t in enumerate(ordered)])
    forward=dict(selected=chain('selected'),baseline=chain('baseline'));stress=10000.
    for f in valid:stress*=1+f['double_cost']['return_percent']/100
    lower=(uncertainty.get('mean_r_95ci') or [None])[0]
    positive=sum(f['selected']['return_percent']>0 for f in valid)
    passes=len(valid)>=3 and len(trades)>=30 and forward['selected']['return_percent']>max(0,forward['baseline']['return_percent']) and forward['selected']['max_drawdown_percent']<forward['baseline']['max_drawdown_percent'] and stress>10000 and positive>=math.ceil(len(valid)/2) and lower is not None and lower>0
    result=dict(instrument=symbol,signature=key,asset_class=opt.asset_class(symbol),baselines=baselines,folds=folds,forward=forward,trade_stats=trade_stats(trades),bootstrap=uncertainty,double_cost_return=100*(stress/10000-1),valid_windows=len(valid),cash_windows=sum(f['policy']['gate']=='cash' for f in valid),passes_screen=passes)
    study.write_json(folder/'study.json',result);study.write_json(folder/'movement.json',movement)
    print(symbol,'MARKET STUDY COMPLETE',round(forward['selected']['return_percent'],2),'screen',passes,flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--symbols',nargs='+',default=opt.UNIVERSE);args=p.parse_args();OUT.mkdir(exist_ok=True);study.write_json(OUT/'PLAN.json',plan())
    for symbol in args.symbols:
        try:run_asset(symbol)
        except Exception as e:study.write_json(OUT/'failures'/f'{symbol}.json',dict(error=str(e)));print(symbol,'FAILED',repr(e),flush=True)
if __name__=='__main__':main()
