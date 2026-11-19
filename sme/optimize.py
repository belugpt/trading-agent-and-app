"""Retrospective, chronological optimization with entry-known pattern filters."""
import argparse
import bisect
import hashlib
import itertools
import json
import math
import statistics
from dataclasses import asdict,replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
from . import research,study2010 as study
from .model import Config
from .data import load_csv,ValidatedSeries
from .engine import Engine
from .analytics import percentile,trade_stats,wilson,bootstrap
from .opt_features import NUMERIC,simulate,permits

DATA=study.DATA
OUT=study.ROOT/'output'/'optimization'
UNIVERSE=study.FOREX+['CHFJPY','XAUUSD','XAGUSD','WTIUSD','BCOUSD']+study.CRYPTO
MIN_TRAIN=20
EMBARGO=timedelta(hours=24)


def asset_base(symbol):
    return research.baseline('AUDJPY' if symbol=='CHFJPY' else symbol)


def asset_class(symbol):
    return 'forex' if symbol in study.FOREX or symbol=='CHFJPY' else research.category(symbol)


def specs():
    result=[dict(id='baseline',changes={})]
    for lookback,retracement,origin in itertools.product([25,50,100],[.05,.1,.2],['retracement_extreme','latest_confirmed_pivot']):
        if (lookback,retracement,origin)==(50,.1,'retracement_extreme'):continue
        result.append(dict(id=f'L{lookback}-R{retracement:g}-'+('deep' if origin=='retracement_extreme' else 'pivot'),
                           changes=dict(lookback=lookback,retracement=retracement,origin_method=origin)))
    for fast,slow in [(63,126),(100,200),(189,378),(252,504)]:
        result.append(dict(id=f'SMA-{fast}-{slow}',changes=dict(fast_period=fast,slow_period=slow)))
    result.append(dict(id='EMA-126-252',changes=dict(fast_type='EMA',slow_type='EMA')))
    for expiry in [24,72,168]:result.append(dict(id=f'expiry-{expiry}',changes=dict(expiry_bars=expiry)))
    return result


def plan():
    return dict(protocol='SME optimization v1',universe=UNIVERSE,core_candidates=specs(),
        mandatory_rules='0.5 limit entry; crossover-candle stop with no buffer; 200% extension beyond frozen endpoint; wick breakout; opposite-open-MA cancellation',
        numeric_features=NUMERIC,thresholds='Training-only 25th/50th/75th percentiles, both sides; categorical direction/session/weekday; limited two-feature conjunctions',
        objective='Maximize actual training CAGR / max(1%, maximum MTM drawdown), not win rate alone',
        training_gate=dict(min_closed_trades=MIN_TRAIN,min_profit_factor=1.05,positive_mean_r=True,positive_return=True,
                           min_profitable_years=2,max_largest_winner_share=.5),
        windows='Four prior calendar years; two forward calendar years; 2026 partial final window',
        embargo_hours=24,training_replay_shortlist=2,
        min_actual_training_years=3,
        promotion_screen='At least 3 forward windows, 30 forward trades, positive return, improved return and drawdown, positive majority of windows, positive double-cost compounded return, positive block-bootstrap lower mean-R bound',
        costs='Original fixed costs; selected policies frozen before double-cost and half-risk tests',
        cash='If no training candidate qualifies, do not trade the following test window',
        data='All available history contributes diagnostics. Incomplete/gapped train or test windows are excluded. Crypto uses actual exchange history.',
        caveat='All history has previously been inspected. This is retrospective walk-forward research, not a genuinely untouched prospective test.',
        risk_percent=1.0,half_risk_percent=.5)


def signature(symbol):
    digest=hashlib.sha256(json.dumps(plan(),sort_keys=True).encode())
    files=[DATA/f'{symbol}.csv',DATA/f'{symbol}.manifest.json']
    if not symbol.startswith('USD') and not symbol.endswith('USD'):
        quote=symbol[-3:];ref='USD'+quote if quote in ('JPY','CHF','CAD') else quote+'USD'
        files.append(DATA/f'{ref}.csv')
    files += [study.ROOT/'sme'/f'{name}.py' for name in ['model','data','engine','analytics','opt_features','optimize']]
    for file in files:digest.update(file.read_bytes())
    return digest.hexdigest()


def safe_trade(trade,setups,gaps):
    start=max(0,setups[trade['setup_id']-1]['crossover_index']-504)
    return bisect.bisect_right(gaps,trade['exit_index'])==bisect.bisect_right(gaps,start)


def flat_metrics(m):
    return {k:v for k,v in m.items() if not isinstance(v,(dict,list))}


def proxy(rows,years,min_trades=MIN_TRAIN):
    if len(rows)<min_trades:return None
    rs=[r['r'] for r in rows];wins=[r for r in rs if r>0];loss=-sum(r for r in rs if r<0)
    if not loss or sum(wins)/loss<1.05 or statistics.mean(rs)<=0:return None
    yearly={}
    for row in rows:yearly[row['exit_time'][:4]]=yearly.get(row['exit_time'][:4],0)+row['r']
    if sum(v>0 for v in yearly.values())<2 or max(wins,default=0)/max(sum(wins),1e-12)>.5:return None
    equity=peak=1.0;dd=0.0
    for value in rs:
        equity*=1+.01*value
        if equity<=0:return None
        peak=max(peak,equity);dd=max(dd,100*(1-equity/peak))
    cagr=100*(equity**(1/max(years,.01))-1)
    if cagr<=0:return None
    return dict(score=cagr/max(dd,1),trades=len(rows),mean_r=statistics.mean(rs),r_profit_factor=sum(wins)/loss,
                proxy_return_percent=100*(equity-1),proxy_drawdown_percent=dd)


def rules_for(rows):
    rules=[{'kind':'all'}]
    for feature in NUMERIC:
        values=[r['features'][feature] for r in rows]
        for threshold in sorted({percentile(values,p) for p in [.25,.5,.75]}):
            for op in ['ge','le']:rules.append(dict(kind='condition',feature=feature,op=op,value=threshold))
    for direction in [1,-1]:rules.append(dict(kind='condition',feature='direction',op='in',value=[direction]))
    for hours in [['Asia'],['Europe'],['US'],['Europe','US']]:
        rules.append(dict(kind='condition',feature='order_session',op='in',value=hours))
    for days in [[0,1,2],[2,3,4]]:rules.append(dict(kind='condition',feature='order_weekday',op='in',value=days))
    return rules


def proposals(cohorts,start,end,min_trades=MIN_TRAIN):
    years=(end-start).total_seconds()/31557600
    proposals=[];trials=0
    for cohort in cohorts:
        rows=sorted((r for r in cohort['rows'] if r['safe'] and r['crossover_time']>=start.isoformat()
                     and r['entry_time']>=start.isoformat() and r['exit_time']<=end.isoformat()),key=lambda r:r['exit_time'])
        if len(rows)<min_trades:continue
        local=[]
        for rule in rules_for(rows):
            selected=[r for r in rows if permits(rule,r['features'])]
            score=proxy(selected,years,min_trades);trials+=1
            if score:local.append(dict(candidate=cohort['id'],rule=rule,proposal=score))
        local.sort(key=lambda p:p['proposal']['score'],reverse=True)
        simple=[p for p in local if p['rule']['kind']=='condition'][:4]
        for a,b in itertools.combinations(simple,2):
            if a['rule']['feature']==b['rule']['feature']:continue
            rule=dict(kind='and',rules=[a['rule'],b['rule']])
            score=proxy([r for r in rows if permits(rule,r['features'])],years,min_trades);trials+=1
            if score:local.append(dict(candidate=cohort['id'],rule=rule,proposal=score))
        proposals.extend(local)
    proposals.sort(key=lambda p:(-p['proposal']['score'],p['candidate'],json.dumps(p['rule'],sort_keys=True)))
    return proposals,trials


def actual_score(result):
    m=result['metrics'];closed=[t for t in result['trades'] if t['status']=='Closed']
    if m['completed_trades']<MIN_TRAIN or (m['profit_factor'] or 0)<1.05 or (m['average_r'] or 0)<=0 or m['return_percent']<=0:return None
    if sum((v or 0)>0 for v in m['annual_returns'].values())<2:return None
    winners=[t['pnl'] for t in closed if t['pnl']>0]
    if not winners or max(winners)/sum(winners)>.5:return None
    return (m.get('cagr_percent') or 0)/max(1,m['max_drawdown_percent'])


def window_ok(bars,start,end,training=False):
    if not bars:return False,'empty window'
    if training and (bars[-1].time-bars[0].time).days<3*365:return False,'less than three years of actual training history'
    if not training and bars[0].time>start+timedelta(days=4):return False,'test history begins late'
    if bars[-1].time<end-timedelta(days=4):return False,'source ends before window'
    if any((b.time-a.time).total_seconds()>168*3600 for a,b in zip(bars,bars[1:])):return False,'source gap exceeds seven days'
    return True,None


def run_asset(symbol):
    research.DATA=DATA
    key=signature(symbol);folder=OUT/'assets'/symbol
    if (folder/'study.json').exists():
        saved=json.loads((folder/'study.json').read_text(encoding='utf-8'))
        if saved.get('signature')==key:
            print(symbol,'completed optimization reused',flush=True);return
    bars=ValidatedSeries(load_csv(DATA/f'{symbol}.csv'));base=asset_base(symbol)
    conversion=research.currency_converter(symbol,{})
    time_cache=[(b.time+timedelta(hours=1)).isoformat() for b in bars]
    rate_engine=Engine(base,symbol,conversion=conversion)
    rates={b.time:(rate_engine.rate(b,True),rate_engine.rate(b)) for b in bars} if conversion else None
    gaps=[i for i in range(1,len(bars)) if (bars[i].time-bars[i-1].time).total_seconds()>168*3600]
    configs={s['id']:replace(base,name='SME experiment / '+s['id'],**s['changes']) for s in specs()}
    baseline=simulate(bars,base,symbol,conversion,time_cache=time_cache,rate_cache=rates)
    baseline_rows=[]
    for t in baseline['trades']:
        if t['status']!='Closed':continue
        s=baseline['setups'][t['setup_id']-1]
        baseline_rows.append(dict(instrument=symbol,trade_id=t['id'],asset_class=asset_class(symbol),win=t['pnl']>0,
            r=t['r_multiple'],pnl=t['pnl'],entry_time=t['entry_time'],exit_time=t['exit_time'],
            pending_wait_bars=t['entry_index']-s['order_index'],safe=safe_trade(t,baseline['setups'],gaps),**t['entry_features']))
    study.write_json(folder/'baseline-patterns.json',baseline_rows)
    cohorts=[]
    for number,(candidate,c) in enumerate(configs.items(),1):
        path=OUT/'cohorts'/symbol/(candidate+'.json')
        saved=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        if saved.get('signature')==key:cohort=saved
        else:
            normalized=replace(c,sizing='fixed_units',fixed_units=.000001)
            r=simulate(bars,normalized,symbol,conversion,diagnostic=True,time_cache=time_cache,rate_cache=rates)
            rows=[dict(r=t['r_multiple'],entry_time=t['entry_time'],exit_time=t['exit_time'],
                       crossover_time=t['crossover_time'],safe=safe_trade(t,r['setups'],gaps),features=t['entry_features'])
                  for t in r['trades'] if t['status']=='Closed']
            cohort=dict(id=candidate,signature=key,rows=rows,
                        note='Tiny fixed-unit opportunity population. Only R is used for proposals; this is not account performance.')
            study.write_json(path,cohort)
        cohorts.append(cohort)
        print(symbol,'core candidates',number,'/',len(configs),flush=True)
    times=[b.time for b in bars]
    def evaluation(c,rule,start,end,flatten=True):
        first=bisect.bisect_left(times,start);last=bisect.bisect_left(times,end)
        warm=max(0,first-max(c.slow_period*5,c.lookback,64))
        block=ValidatedSeries(bars[warm:last])
        return simulate(block,c,symbol,conversion,rule=rule,activation=start,flatten=flatten,
                        time_cache=time_cache[warm:last],rate_cache=rates)
    folds=[];total_trials=0
    for year in range(2014,2027,2):
        start=datetime(year,1,1,tzinfo=timezone.utc);end=min(datetime(year+2,1,1,tzinfo=timezone.utc),study.END)
        train_start=datetime(year-4,1,1,tzinfo=timezone.utc);cutoff=start-EMBARGO
        training=[b for b in bars if train_start<=b.time<cutoff];testing=[b for b in bars if start<=b.time<end]
        valid,reason=window_ok(training,train_start,cutoff,True)
        valid_test,reason_test=window_ok(testing,start,end)
        if not valid or not valid_test:
            folds.append(dict(year=year,status='excluded',reason=reason or reason_test));continue
        proposed,trials=proposals(cohorts,train_start,cutoff);total_trials+=trials
        chosen=None;chosen_train=None;best=-math.inf
        for proposal in proposed[:2]:
            trained=evaluation(configs[proposal['candidate']],proposal['rule'],train_start,cutoff)
            score=actual_score(trained)
            if score is not None and score>best:
                chosen=proposal;chosen_train=flat_metrics(trained['metrics']);best=score
        reference=evaluation(base,{'kind':'all'},start,end)
        chosen=chosen or dict(candidate='baseline',rule={'kind':'cash'},proposal=None)
        selected=configs[chosen['candidate']]
        tested=evaluation(selected,chosen['rule'],start,end)
        stressed=evaluation(replace(selected,spread=selected.spread*2,slippage=selected.slippage*2,
                                    commission_per_million=selected.commission_per_million*2),chosen['rule'],start,end)
        stress_base=evaluation(replace(base,spread=base.spread*2,slippage=base.slippage*2,
                                      commission_per_million=base.commission_per_million*2),{'kind':'all'},start,end)
        half=evaluation(replace(selected,risk_percent=.5),chosen['rule'],start,end)
        fold=dict(year=year,status='tested',train_start=train_start.isoformat(),selection_cutoff=cutoff.isoformat(),
            test_start=start.isoformat(),test_end=end.isoformat(),trials=trials,selected=chosen,
            config=asdict(selected),training_metrics=chosen_train,
            baseline_metrics=flat_metrics(reference['metrics']),selected_metrics=flat_metrics(tested['metrics']),
            double_cost_metrics=flat_metrics(stressed['metrics']),double_cost_baseline_metrics=flat_metrics(stress_base['metrics']),
            half_risk_metrics=flat_metrics(half['metrics']),
            baseline_curve=reference['equity'],selected_curve=tested['equity'],half_risk_curve=half['equity'],
            baseline_trades=reference['trades'],selected_trades=tested['trades'])
        folds.append(fold)
        print(symbol,'walk-forward',year,'choice',chosen['candidate'],chosen['rule']['kind'],
              'baseline',round(reference['metrics']['return_percent'],2),'selected',round(tested['metrics']['return_percent'],2),flush=True)
    full_proposals,full_trials=proposals(cohorts,bars[0].time,study.END,min_trades=60 if bars[0].time.year<=2015 else 30)
    best_fit=None;best_fit_policy=None;best_score=-math.inf
    for proposal in full_proposals[:2]:
        r=simulate(bars,configs[proposal['candidate']],symbol,conversion,rule=proposal['rule'],time_cache=time_cache,rate_cache=rates)
        score=actual_score(r)
        if score is not None and score>best_score:best_fit=r;best_fit_policy=proposal;best_score=score
    if best_fit is not None:
        best_fit['fit_warning']='Full-sample fitted illustration. Not the walk-forward performance and not independently validated.'
        study.write_json(OUT/'runs'/symbol/'result.json',best_fit)
        study.write_json(folder/'full-sample-policy.json',dict(base_config=best_fit['config'],order_filter=best_fit_policy['rule'],warning=best_fit['fit_warning']))
        research.export_csv(folder/'full-sample-trades.csv',best_fit['trades'])
    def stitch(name):
        wealth=peak=10000.0;maxdd=0.0;curve=[]
        for fold in folds:
            if fold['status']!='tested':continue
            values=fold[name]
            if wealth<=0:break
            start_wealth=wealth
            for p in values:
                value=start_wealth*p['equity']/10000
                peak=max(peak,value);maxdd=max(maxdd,100*(1-value/peak))
            wealth=start_wealth*values[-1]['equity']/10000
            stride=max(1,len(values)//250)
            curve.extend(dict(time=p['time'],equity=start_wealth*p['equity']/10000) for p in values[::stride])
            curve.append(dict(time=values[-1]['time'],equity=wealth))
        return dict(return_percent=100*(wealth/10000-1),max_drawdown_percent=maxdd,final_equity=wealth,curve=curve)
    forward=dict(baseline=stitch('baseline_curve'),selected=stitch('selected_curve'),half_risk=stitch('half_risk_curve'))
    for fold in folds:
        for field in ['baseline_curve','selected_curve','half_risk_curve']:fold.pop(field,None)
    validated=[f for f in folds if f['status']=='tested']
    all_selected=[t for f in validated for t in f['selected_trades']]
    all_baseline=[t for f in validated for t in f['baseline_trades']]
    stats=trade_stats(all_selected);base_stats=trade_stats(all_baseline)
    improved=forward['selected']['return_percent']>forward['baseline']['return_percent'] and forward['selected']['max_drawdown_percent']<forward['baseline']['max_drawdown_percent']
    positive_windows=sum(f['selected_metrics']['return_percent']>0 for f in validated)
    stressed_wealth=10000.0
    for f in validated:
        if stressed_wealth<=0:break
        stressed_wealth*=1+f['double_cost_metrics']['return_percent']/100
    ordered=sorted(all_selected,key=lambda t:(t['entry_time'],t['id']))
    uncertainty=bootstrap([{**t,'entry_index':i} for i,t in enumerate(ordered)])
    lower=(uncertainty.get('mean_r_95ci') or [None])[0]
    promote=(len(validated)>=3 and stats['completed_trades']>=30 and improved and forward['selected']['return_percent']>0
             and positive_windows>=math.ceil(len(validated)*.5) and stressed_wealth>10000 and lower is not None and lower>0)
    result=dict(instrument=symbol,asset_class=asset_class(symbol),signature=key,baseline=flat_metrics(baseline['metrics']),
        folds=folds,forward=forward,forward_trade_stats=stats,baseline_forward_trade_stats=base_stats,
        training_rule_trials=total_trials,full_sample_rule_trials=full_trials,
        full_sample_fit=flat_metrics(best_fit['metrics']) if best_fit else None,full_sample_policy=best_fit_policy,
        valid_windows=len(validated),cash_windows=sum(f['selected']['rule']['kind']=='cash' for f in validated),
        forward_bootstrap=uncertainty,double_cost_forward_return=100*(stressed_wealth/10000-1),
        positive_windows=positive_windows,passes_basic_promotion_screen=promote,
        promotion_warning='Retrospective screen only. All data was previously inspected; passing is not proof of a future edge.')
    study.write_json(folder/'study.json',result)
    print(symbol,'OPTIMIZATION COMPLETE','forward baseline',round(forward['baseline']['return_percent'],2),
          'selected',round(forward['selected']['return_percent'],2),'screen',promote,flush=True)


def summary():
    results=[];missing=[];pattern_rows=[]
    for symbol in UNIVERSE:
        path=OUT/'assets'/symbol/'study.json'
        if not path.exists():missing.append(symbol);continue
        r=json.loads(path.read_text(encoding='utf-8'))
        if r['signature']!=signature(symbol):missing.append(symbol+' stale');continue
        results.append(r)
        pattern_rows+=json.loads((path.parent/'baseline-patterns.json').read_text(encoding='utf-8'))
    rows=[]
    for r in results:
        rows.append(dict(instrument=r['instrument'],asset_class=r['asset_class'],valid_windows=r['valid_windows'],cash_windows=r['cash_windows'],
            baseline_return=r['forward']['baseline']['return_percent'],optimized_return=r['forward']['selected']['return_percent'],
            baseline_drawdown=r['forward']['baseline']['max_drawdown_percent'],optimized_drawdown=r['forward']['selected']['max_drawdown_percent'],
            half_risk_return=r['forward']['half_risk']['return_percent'],half_risk_drawdown=r['forward']['half_risk']['max_drawdown_percent'],
            baseline_trades=r['baseline_forward_trade_stats']['completed_trades'],optimized_trades=r['forward_trade_stats']['completed_trades'],
            baseline_win_rate=r['baseline_forward_trade_stats']['win_rate'],optimized_win_rate=r['forward_trade_stats']['win_rate'],
            optimized_mean_r=r['forward_trade_stats']['average_r'],optimized_profit_factor=r['forward_trade_stats']['profit_factor'],
            double_cost_return=r['double_cost_forward_return'],mean_r_95ci_low=(r['forward_bootstrap'].get('mean_r_95ci') or [None])[0],
            passes_screen=r['passes_basic_promotion_screen'],training_trials=r['training_rule_trials']))
    study.write_json(OUT/'summary.json',dict(results=rows,missing=missing))
    research.export_csv(OUT/'summary.csv',rows)
    research.export_csv(OUT/'baseline-trade-features.csv',pattern_rows)
    safe=[r for r in pattern_rows if r['safe']]
    groups=[]
    def add_group(feature,label,selected,**bounds):
        if not selected:return
        wins=sum(r['win'] for r in selected);rs=[r['r'] for r in selected]
        gain=sum(x for x in rs if x>0);loss=-sum(x for x in rs if x<0)
        ids={(r['instrument'],r['trade_id']) for r in selected}
        rest=[r for r in safe if (r['instrument'],r['trade_id']) not in ids]
        eras={}
        for name,first,last in [('2010-2015',2010,2015),('2016-2020',2016,2020),('2021-2026',2021,2026)]:
            subset=[r for r in selected if first<=int(r['entry_time'][:4])<=last]
            eras[name]=dict(n=len(subset),win_rate=sum(r['win'] for r in subset)/len(subset) if subset else None,
                            mean_r=statistics.mean(r['r'] for r in subset) if subset else None)
        groups.append(dict(feature=feature,group=label,n=len(selected),wins=wins,win_rate=wins/len(selected),
                           mean_r=statistics.mean(rs),risk_normalized_pf=gain/loss if loss else None,win_rate_95ci=wilson(wins,len(selected)),
                           rest_win_rate=sum(r['win'] for r in rest)/len(rest) if rest else None,
                           rest_mean_r=statistics.mean(r['r'] for r in rest) if rest else None,era_statistics=eras,**bounds))
    for feature in NUMERIC:
        cut=[percentile([r[feature] for r in safe],p) for p in [.25,.5,.75]]
        for i in range(4):
            lo=cut[i-1] if i else None;hi=cut[i] if i<3 else None
            label=f'Q{i+1}: '+(f'> {lo:.4g}' if lo is not None else 'lowest')+(f' to {hi:.4g}' if hi is not None else ' and above')
            add_group(feature,label,[r for r in safe if (lo is None or r[feature]>lo) and (hi is None or r[feature]<=hi)],lower_bound=lo,upper_bound=hi)
    for feature in ['direction','order_session','order_weekday','instrument','asset_class']:
        for value in sorted({str(r[feature]) for r in safe}):add_group(feature,value,[r for r in safe if str(r[feature])==value])
    research.export_csv(OUT/'winning-patterns.csv',groups)
    study.write_json(OUT/'winning-patterns.json',dict(groups=groups,safe_trades=len(safe),excluded_quality_trades=len(pattern_rows)-len(safe),
        warning='Exploratory full-sample associations, not independently predictive facts. Train-window filters are learned separately.'))
    lines=['# SME full-ground retrospective optimization','',
      'Original baseline: 126/252 SMA OPEN, H1. Twenty-six core configurations were evaluated without changing midpoint limit entry, crossover-candle stop, wick breakout, or the two-range target. Learned order filters are explicit experimental variants. CHFJPY is included as the 22nd forex pair.',
      '', 'All data has already been inspected. These are retrospective chronological validations, not a prospectively untouched sample. Rules and thresholds for each forward window use only earlier closed trades, with a 24-hour selection embargo. Full-sample best-fit results are separately labelled and are not the forward results.',
      '', '## Protocol','',json.dumps(plan(),indent=2),
      '', '## What winning trades share','',
      f'{len(safe):,} quality-screened baseline closed trades were compared with losers; {len(pattern_rows)-len(safe)} trades spanning missing-data/indicator windows were excluded from pattern discovery. Features use prices and structure already known when the order was created. Exit duration, MFE, MAE and future price action are not predictors. Pending wait is recorded for description, not used as an entry-time predictor; expiry is tested as a separate configured rule.',
      '', '| Pattern group | Trades | Win % | Mean R | R-weighted PF |','|---|---:|---:|---:|---:|']
    for g in sorted((g for g in groups if g['n']>=50 and g['feature'] in NUMERIC),key=lambda g:g['mean_r'],reverse=True)[:15]:
        lines.append(f"| {g['feature']} / {g['group']} | {g['n']} | {research.fmt(g['win_rate']*100)} | {research.fmt(g['mean_r'])} | {research.fmt(g['risk_normalized_pf'])} |")
    lines+=['','Quartiles above are descriptive full-history bins and may be confounded by instrument/regime. They are not advertised as statistically confirmed predictors. The CSV contains every group, sample sizes and Wilson intervals. Higher win rate alone is not the optimization target.',
      '', 'Feature units: stop_range and swing_range divide the respective price distance by the previous 48 observed bars’ average high–low range; ma_separation divides MA distance by that same range; aligned_slope is directional fast-MA change over 24 bars divided by the range. continuation is the fraction of the frozen swing beyond the first breakout candle extreme. cost_risk is a pre-entry estimated spread/slippage/commission ratio to stop distance. recent_volatility is the standard deviation of recent log returns in percent. setup_bars/impulse_bars are observed-bar counts, not elapsed wall-clock hours.',
      '', '## Forward-window comparison','',
      'Returns chain independently restarted, boundary-liquidated test accounts at fixed proportional risk. Each fold resets flat, preserves prior-price MA warm-up, and requires a fresh crossover. Both baseline and optimized comparators use identical boundaries. This is not the continuously carried original 2010 account. Test dates and available fold counts differ by history; assets are not ranked across unequal windows as if exposure were identical.',
      '', '| Instrument | Windows | Cash windows | Baseline % | Selected % | Baseline DD % | Selected DD % | Half-risk % | Half-risk DD % | Screen passes |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in sorted(rows,key=lambda r:r['optimized_return']-r['baseline_return'],reverse=True):
        lines.append('| '+' | '.join(map(str,[r['instrument'],r['valid_windows'],r['cash_windows'],research.fmt(r['baseline_return']),research.fmt(r['optimized_return']),research.fmt(r['baseline_drawdown']),research.fmt(r['optimized_drawdown']),research.fmt(r['half_risk_return']),research.fmt(r['half_risk_drawdown']),r['passes_screen']]))+' |')
    lines+=['','## Per-instrument decisions','']
    for r in results:
        lines += [f"### {r['instrument']}",'',
          f"Training pattern trials: {r['training_rule_trials']:,}; full-sample proposal trials: {r['full_sample_rule_trials']:,}. Selected forward trade statistics: {json.dumps(r['forward_trade_stats'])}",'',
          '| Test year | Decision | Candidate | Baseline % | Selected % | Double-cost selected % | Double-cost baseline % |','|---|---|---|---:|---:|---:|---:|']
        for f in r['folds']:
            if f['status']!='tested':lines.append(f"| {f['year']} | Excluded: {f['reason']} | — | — | — | — | — |");continue
            lines.append(f"| {f['year']} | {json.dumps(f['selected']['rule'])} | {f['selected']['candidate']} | {research.fmt(f['baseline_metrics']['return_percent'])} | {research.fmt(f['selected_metrics']['return_percent'])} | {research.fmt(f['double_cost_metrics']['return_percent'])} | {research.fmt(f['double_cost_baseline_metrics']['return_percent'])} |")
        lines+=['','Full-sample best-fit (not validation): '+json.dumps(r['full_sample_fit'])+'.','']
    lines+=['## Limits and evidence','',
      'The proxy search uses tiny fixed-unit opportunity runs to compare R, not to claim account returns. Every shortlisted training policy and forward policy is re-simulated with the real 1% account-risk sizing and execution engine. A cash decision means no eligible training policy, not a 100% win-rate strategy. Lower risk is evaluated separately and must not be confused with discovering an edge.',
      '', 'Source gaps exclude affected folds. AUDJPY/WTI may therefore have fewer valid windows; crypto starts at exchange availability. Costs remain illustrative fixed spreads, slippage and commissions, excluding financing, swap/borrow/funding and roll effects. Synthetic crypto shorts and the original conversion, fractional-lot and margin approximations remain. Double-cost stress does not re-optimize the rule.',
      '', 'Large searches increase selection risk. No result establishes future reliability, and the basic promotion screen is not a significance test. Research context: [Bailey et al., probability of backtest overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).',
      '', 'Missing/stale runs: '+json.dumps(missing), '']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Optimization report',len(results),'assets;',len(missing),'missing',flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','run','report']);p.add_argument('--symbols',nargs='+',choices=UNIVERSE)
    args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    if args.action=='plan':study.write_json(OUT/'PLAN.json',plan());print('Locked plan:',len(specs()),'core configurations across',len(UNIVERSE),'assets')
    elif args.action=='report':summary()
    else:
        for symbol in args.symbols or UNIVERSE:
            try:run_asset(symbol)
            except Exception as exc:
                study.write_json(OUT/'failures'/f'{symbol}.json',dict(instrument=symbol,error=str(exc)))
                print(symbol,'OPTIMIZATION FAILED',repr(exc),flush=True)

if __name__=='__main__':main()
