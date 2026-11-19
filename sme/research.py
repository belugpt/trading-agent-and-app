"""Reproducible batch research, exports, fixed holdout and cold-start yearly validation."""
import argparse
import bisect
import csv
import json
import hashlib
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from .model import Config
from .data import load_csv, ValidatedSeries
from .engine import Engine
from .analytics import bootstrap
from .download import FOREX, COMMODITIES, CRYPTO, ROOT, DATA

OUT=ROOT/'output'


def category(symbol):
    return 'forex' if symbol in FOREX else 'crypto' if symbol in CRYPTO else 'commodities'


def baseline(symbol):
    c=Config()
    if category(symbol)=='forex':
        pip=.01 if symbol.endswith('JPY') else .0001
        c.pip_size=pip
        c.spread=pip*(1 if symbol in FOREX[:7] else 2)
        c.slippage=pip*.2
    elif symbol in CRYPTO:
        c.commission_per_million=1000  # Explicit 0.1% per side illustrative trading fee.
        c.max_leverage=1
        c.contract_size=1
        c.pip_size=.01
        c.spread={'BTCUSD':2,'ETHUSD':.2,'BNBUSD':.02}[symbol]
        c.slippage=c.spread/2
    else:
        c.spread={'XAUUSD':.3,'XAGUSD':.03,'WTIUSD':.04,'BCOUSD':.04}.get(symbol,.02)
        c.slippage=c.spread/5
        c.max_leverage=10
        c.pip_size=.001 if symbol=='XAGUSD' else .01
        c.contract_size=100 if symbol=='XAUUSD' else 5000 if symbol=='XAGUSD' else 1000
    return c


def currency_converter(symbol,cache):
    if symbol.endswith('USD') or symbol.startswith('USD'):
        return None
    quote=symbol[-3:]
    inverse=quote in ('JPY','CHF','CAD')
    reference='USD'+quote if inverse else quote+'USD'
    if reference not in cache:
        cache[reference]=load_csv(DATA/f'{reference}.csv')
    series=cache[reference]
    stamps=[b.time.timestamp()+3600 for b in series]
    def rate(stamp):
        at=bisect.bisect_right(stamps,stamp.timestamp())-1
        if at<0:
            # At the first source candle, its open is the sole available observation.
            if series and stamp==series[0].time:
                return 1/series[0].open if inverse else series[0].open
            raise ValueError(f'No historical {reference} conversion at {stamp}')
        if stamp.timestamp()-stamps[at]>96*3600:
            raise ValueError(f'Stale {reference} conversion (>96 hours)')
        return 1/series[at].close if inverse else series[at].close
    return rate


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8')


def fingerprint(symbol,config):
    digest=hashlib.sha256(json.dumps(asdict(config),sort_keys=True).encode())
    paths=[DATA/f'{symbol}.csv']
    if not symbol.startswith('USD') and not symbol.endswith('USD'):
        quote=symbol[-3:]
        ref='USD'+quote if quote in ('JPY','CHF','CAD') else quote+'USD'
        paths.append(DATA/f'{ref}.csv')
    paths += [ROOT/'sme'/f'{name}.py' for name in ['model','data','engine','analytics','research','validation']]
    for p in paths:
        digest.update(p.read_bytes())
    return digest.hexdigest()


def export_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:
        path.write_text('',encoding='utf-8')
        return
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=keys)
        writer.writeheader()
        writer.writerows({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)


def run_one(symbol,config=None,cache=None):
    cache=cache if cache is not None else {}
    if symbol not in cache:
        cache[symbol]=ValidatedSeries(load_csv(DATA/f'{symbol}.csv'))
    bars=cache[symbol]
    return Engine(config or baseline(symbol),symbol,conversion=currency_converter(symbol,cache)).run(bars)


def experiments(symbol,bars,config,conversion):
    experiments=[]
    # Prespecified comparison only: there is no in-sample winner selection.
    variants=[('20 SMA / 50 SMA (open)',replace(config,fast_period=20,slow_period=50)),
              ('50 SMA / 100 SMA (open)',replace(config,fast_period=50,slow_period=100)),
              ('50 SMA / 200 SMA',replace(config,fast_period=50,slow_period=200)),
              ('126 EMA / 252 EMA (open)',replace(config,fast_type='EMA',slow_type='EMA')),
              ('retracement 0.05%',replace(config,retracement=.05)),
              ('retracement 0.2%',replace(config,retracement=.2)),
              ('double costs',replace(config,spread=config.spread*2,slippage=config.slippage*2,
                                       commission_per_million=config.commission_per_million*2)),
              ('zero costs diagnostic',replace(config,spread=0,slippage=0,commission_per_million=0))]
    for label,c in variants:
        r=Engine(replace(c,name=label),symbol,conversion=conversion).run(bars)
        experiments.append(dict(label=label,kind='full_sample_sensitivity',config=asdict(c),metrics=r['metrics']))
    split=datetime(2024,1,1,tzinfo=timezone.utc)
    for label,subset in [('in_sample_2020_2023',[b for b in bars if b.time<split]),
                         ('holdout_2024_onward',[b for b in bars if b.time>=split])]:
        if subset:
            r=Engine(config,symbol,conversion=conversion).run(subset)
            experiments.append(dict(label=label,kind='fixed_temporal_split',metrics=r['metrics']))
    for year in sorted({b.time.year for b in bars}):
        subset=[b for b in bars if b.time.year==year]
        r=Engine(config,symbol,conversion=conversion).run(subset)
        experiments.append(dict(label=str(year),kind='yearly_cold_start_forward_validation',metrics=r['metrics']))
    return experiments


def batch(symbols=None,deep=True):
    OUT.mkdir(exist_ok=True)
    cache={}
    rows,failures=[],[]
    universe=symbols or FOREX+['XAUUSD','XAGUSD','WTIUSD','BCOUSD']+CRYPTO
    for symbol in universe:
        try:
            c=baseline(symbol)
            signature=fingerprint(symbol,c)
            folder=OUT/'runs'/symbol
            previous=json.loads((folder/'result.json').read_text(encoding='utf-8')) if (folder/'result.json').exists() else {}
            if previous.get('research_fingerprint')==signature and (not deep or previous.get('experiments')):
                r=previous
                if symbol not in cache:
                    cache[symbol]=ValidatedSeries(load_csv(DATA/f'{symbol}.csv'))
                print(symbol,'reused verified unchanged run',flush=True)
            else:
                r=run_one(symbol,c,cache)
                r['bootstrap']=bootstrap(r['trades'])
                if deep:
                    r['experiments']=experiments(symbol,cache[symbol],c,currency_converter(symbol,cache))
                r['research_fingerprint']=signature
            manifest_path=DATA/f'{symbol}.manifest.json'
            provenance=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {'source':'User CSV; unverified provenance'}
            r['provenance']=provenance
            dump(folder/'result.json',r)
            export_csv(folder/'trades.csv',r['trades'])
            export_csv(folder/'setups.csv',r['setups'])
            export_csv(folder/'equity.csv',r['equity'])
            export_csv(folder/'events.csv',r['events'])
            dump(folder/'config.json',asdict(c))
            dump(folder/'quality.json',r['quality'])
            if deep:
                export_csv(folder/'experiments.csv',[dict(label=e['label'],kind=e['kind'],**{k:v for k,v in e['metrics'].items() if not isinstance(v,(dict,list))}) for e in r['experiments']])
            m=r['metrics']
            row=dict(instrument=symbol,category=category(symbol),start=r['quality']['start'],end=r['quality']['end'],
                     bars=len(cache[symbol]),source=provenance['source'],download_errors=len(provenance.get('errors',[])),
                     gaps=r['quality']['gap_count'],**{k:v for k,v in m.items() if not isinstance(v,(dict,list))})
            row['ranking_eligible'] = (not provenance.get('errors') and
                cache[symbol][0].time <= datetime(2020,1,4,tzinfo=timezone.utc) and
                cache[symbol][-1].time >= datetime(2026,11,13,tzinfo=timezone.utc))
            row['underlying_price_change_percent'] = 100*(cache[symbol][-1].close/cache[symbol][0].open-1)
            if deep:
                holdout=next(e for e in r['experiments'] if e['label']=='holdout_2024_onward')['metrics']
                row.update(holdout_return_percent=holdout['return_percent'],holdout_trades=holdout['completed_trades'],
                           holdout_profit_factor=holdout['profit_factor'],holdout_drawdown_percent=holdout['max_drawdown_percent'])
            rows.append(row)
            export_csv(OUT/'summary.csv',rows)
            dump(OUT/'summary.json',dict(results=rows,failures=failures))
            print(symbol,'trades',m['completed_trades'],'return',round(m['return_percent'],2),'DD',round(m['max_drawdown_percent'],2),flush=True)
        except Exception as exc:
            failures.append(dict(instrument=symbol,category=category(symbol),error=str(exc)))
            print(symbol,'FAILED',exc,flush=True)
    export_csv(OUT/'summary.csv',rows)
    dump(OUT/'summary.json',dict(results=rows,failures=failures))
    write_report(rows,failures)
    return rows,failures


def fmt(value,digits=2):
    return '—' if value is None else f'{value:,.{digits}f}' if isinstance(value,(float,int)) else str(value)


def write_report(rows,failures):
    lines=['# SME H1 historical research report','',
        'Requested window: 1 January 2020 through 17 November 2026 UTC (exclusive cutoff). Each row shows actual source coverage.',
        '', '## Read the results correctly','',
        'These are deterministic simulations under provisional swing definitions, not a verified reproduction of discretionary chart examples. No parameter was selected for historical yield. Rank means net marked-to-market account return among tested instruments, not future expected yield.',
        '', 'Every instrument starts with a separate $10,000 USD account, risks 1% of current realized balance per trade, and compounds. Accounts are independent; returns cannot be added into a portfolio. Open trades remain open at the cutoff; equity includes estimated liquidation costs. Realized profit metrics exclude open positions.',
        '', 'Baseline explicitly selected by the user: 126 SMA / 252 SMA, both calculated from candle OPEN prices; 50-bar previous-structure lookback; a close reversal of 0.1% of the directional extreme confirms both retracements. An open-price MA crossover is known at the candle open and cancels any unfilled prior setup before a possible same-bar limit fill. The new setup is finalized at close, when the crossover candle stop reference has its complete high/low; both signal and reference-availability timestamps are recorded. No post-crossover structure is inferred inside the crossover candle. The confirming retracement candle must not set a new directional extreme. Origin is the deepest known retracement low/high before breakout. The breakout candle cannot retroactively supply the origin. Frozen midpoint orders start on the next bar. A midpoint already passed at confirmation causes rejection. Stop is the crossover candle extreme, no buffer. Target is two full swing ranges beyond the endpoint.',
        '', 'Execution: bid OHLC for HistData; synthetic bid proxy for Binance trade-price candles. Buy limits fill only when ask reaches the limit, sells when bid reaches it. Stops use executable bid/ask and adverse gap-open prices plus slippage. Limit fills receive no favorable price improvement. On ambiguous bars the stop wins; a fill-bar target is credited only if the order was marketable at open. No assumed high/low path. Open-price crossovers cancel unfilled orders at open, before fills on that bar. Close-price MA experiments instead observe crossovers at close, after any intrabar fill. Existing filled positions retain their original stops and targets.',
        '', 'Costs: forex 1 pip spread for the seven USD majors, 2 pips for crosses, 0.2 pip stop slippage, $35 per $1m notional per side commission. Gold spread $0.30, silver $0.03, oils $0.04; stop slippage 20% of spread; $35/million commission. Crypto spreads BTC $2, ETH $0.20, BNB $0.02; stop slippage half the spread; 0.1% per side commission. These are illustrative fixed assumptions, not reconstructed historical broker quotes. Swaps, financing, borrow fees, futures rolls and variable spreads are excluded. Sensitivity tests include double and zero transaction costs.',
        '', 'Leverage caps: forex 30×, commodities 10×, crypto 1× total gross notional per independent account. No margin liquidation model or minimum lot rounding. USD cross-currency conversion uses the last known completed reference H1 close; direct USD-base instruments use the execution-bar open. Actual intrabar conversion is unavailable.',
        '', 'Crypto uses Binance spot BTC/ETH/BNB versus USDT, treats USDT as USD, and simulates symmetric shorts. Spot candles do not establish borrow availability or futures execution. Crypto results are indicative synthetic long/short research and exclude borrow/funding costs.',
        '', '## Rankings by historical net return','']
    eligible=[r for r in rows if r.get('ranking_eligible',True)]
    lines[4:4]=['## Research snapshot','',
        f"{len(rows)} instruments simulated; {len(eligible)} eligible for full-window ranking. {sum(r['total_setups'] for r in rows):,} crossover setups; {sum(r['completed_trades'] for r in rows):,} completed trades across separate accounts. {sum(r['return_percent']>0 for r in eligible)} of {len(eligible)} eligible instruments have positive full-period net returns; {sum((r.get('holdout_return_percent') or 0)>0 for r in eligible)} have positive cold-start 2024-onward returns. These counts are not a combined portfolio result.", '']
    for group in ['forex','commodities','crypto']:
        ordered=sorted((r for r in rows if r['category']==group and r.get('ranking_eligible',True)),key=lambda r:r['return_percent'],reverse=True)
        lines+=['### '+group.title(),'', '| Rank | Instrument | Return % | CAGR % | Max DD % | Closed trades | Win % | PF | Holdout return % |',
                 '|---:|---|---:|---:|---:|---:|---:|---:|---:|']
        for rank,r in enumerate(ordered,1):
            lines.append('| '+' | '.join(map(str,[rank,r['instrument'],fmt(r['return_percent']),fmt(r.get('cagr_percent')),fmt(r['max_drawdown_percent']),r['completed_trades'],fmt(100*r['win_rate'] if r['win_rate'] is not None else None),fmt(r['profit_factor']),fmt(r.get('holdout_return_percent'))]))+' |')
        if len(ordered)<5 and group!='crypto':
            lines+=['',f'Only {len(ordered)} distinct {group} markets have usable data. A top five cannot be substantiated; unavailable markets are not assigned invented results.']
        lines+=['']
    lines+=['## Coverage and data quality','', 'Rankings exclude failed source periods and require comparable history from the beginning of 2020 through the provider’s latest published data. Forex and commodity archives end on 13 November 2026; crypto ends on 16 November 2026. This does not claim forex or commodity coverage for 16 November. Gap-level quality limitations still apply. Shortened / incomplete simulations remain in exports for inspection.', '', '| Instrument | First UTC bar | Last UTC bar | Bars | Gaps | Failed source periods | Rank eligible |', '|---|---|---|---:|---:|---:|---|']
    for r in rows:
        lines.append(f"| {r['instrument']} | {r['start']} | {r['end']} | {r['bars']} | {r['gaps']} | {r['download_errors']} | {r.get('ranking_eligible',True)} |")
    lines+=['','Gaps include weekends, holidays, exchange maintenance and missing data; a complete trading-session calendar has not been reconciled. HistData minute bars use fixed EST without DST and are converted to UTC before hourly aggregation. Partial hours are retained and counted in source manifests. Source archives and SHA-256 hashes are retained locally. Binance monthly ZIPs are also checked against provider checksums. Coverage claims require inspection of failed periods, not just first/last dates.','', '## Per-instrument breakdown','']
    for r in rows:
        detail=json.loads((OUT/'runs'/r['instrument']/'result.json').read_text(encoding='utf-8'))
        m,b=detail['metrics'],detail['bootstrap']
        ci=m['win_rate_95ci']
        lines += [f"### {r['instrument']}",'',
            f"Setups {m['total_setups']}; structurally qualified {m['qualified_setups']}; filled {m['total_trades']}; closed {m['completed_trades']}; still open {m['open_trades']}. Realized P/L ${fmt(m['net_profit'])}; final liquidation equity ${fmt(m['final_equity'])}.",
            '',f"Wins/losses/breakeven: {m['winning_trades']}/{m['losing_trades']}/{m['breakeven_trades']}. Win-rate Wilson 95% interval: {fmt(ci[0]*100 if ci[0] is not None else None)}%–{fmt(ci[1]*100 if ci[1] is not None else None)}%. Expectancy ${fmt(m['expectancy'])}; mean R {fmt(m['average_r'])}; mean holding time {fmt(m['average_holding_hours'])}h. Longest winning/losing streak {m['consecutive_wins']}/{m['consecutive_losses']}.",
            '',f"Gross winning P/L ${fmt(m['gross_profit'])}; gross losing P/L ${fmt(m['gross_loss'])}; average winner ${fmt(m['average_win'])}; average loser ${fmt(m['average_loss'])}; best/worst ${fmt(m['best_trade'])}/${fmt(m['worst_trade'])}. Estimated spread, stop slippage and commissions ${fmt(m['total_transaction_costs'])}. Ambiguous closed-trade bars: {m['ambiguous_bars']}.",
            '', 'Stage rejections/unresolved: '+json.dumps(m['rejected_or_unresolved'])+'.',
            '', 'Block-bootstrap diagnostics: '+json.dumps(b)+'.',
            '', '| Analysis | Return % | Max DD % | Trades | PF | Mean R |', '|---|---:|---:|---:|---:|---:|']
        if not r.get('ranking_eligible',True):
            where=lines.index(f"### {r['instrument']}")+2
            lines[where:where]=['**Incomplete source coverage: excluded from full-window rankings.** '+json.dumps(detail['provenance'].get('errors',[])), '']
        for e in detail.get('experiments',[]):
            x=e['metrics']
            lines.append(f"| {e['label']} | {fmt(x['return_percent'])} | {fmt(x['max_drawdown_percent'])} | {x['completed_trades']} | {fmt(x['profit_factor'])} | {fmt(x['average_r'])} |")
        lines+=['','| Year | MTM return % |','|---|---:|']
        for year,value in m['annual_returns'].items():
            lines.append(f'| {year} | {fmt(value)} |')
        lines+=['','| Direction | Closed trades | Net P/L USD | Win % | PF | Mean R |','|---|---:|---:|---:|---:|---:|']
        for key,segment in m['segments'].items():
            if key.startswith('direction:'):
                lines.append(f"| {key.split(':')[1]} | {segment['completed_trades']} | {fmt(segment['net_profit'])} | {fmt(100*segment['win_rate'] if segment['win_rate'] is not None else None)} | {fmt(segment['profit_factor'])} | {fmt(segment['average_r'])} |")
        stages=Counter(s['stage_at_cancellation'] for s in detail['setups'] if s.get('reason')=='opposite_crossover')
        lines+=['', 'Opposite-crossover cancellations by prior stage: '+json.dumps(dict(stages))+'.',
            '', 'Session segments, all monthly returns, R distributions, full trades, equity and drawdown curves are in the JSON and CSV exports. Excursions are conservative close-observed lower bounds (plus executable exit), because intrabar ordering on entry/exit bars is unknown. Trade timestamps have H1 precision.','']
    lines+=['## Validation limits','',
        'The 2024-onward holdout was prespecified before examining results. Both temporal splits restart with flat accounts, warm their moving averages on their own data, and carry no prior setup. Annual forward-validation runs also restart flat with the unchanged baseline; they are not a trained walk-forward optimizer. The app supports rolling train/test windows separately. Comparisons are not evidence of independent returns; assets and overlapping trades are correlated. Bootstrap confidence intervals use circular blocks of five trades and do not fully model regime dependence. Drawdown bootstrap is additive R, not account-percent drawdown. Wilson intervals assume independent Bernoulli observations and may be too narrow with clustered trades.',
        '', 'Ranking instruments on the full period also uses their holdout performance. The holdout is a prespecified temporal diagnostic for the fixed strategy, but it is not an untouched independent test of an instrument selected from this ranking. Comparing many instruments and parameter variants creates selection bias; no multiple-comparison adjustment or new untouched post-selection dataset is claimed.',
        '', 'No claim of a reliable trading edge is justified solely by a positive rank or a small sample. Confirm strategy interpretation against trader-annotated examples and validate with broker-specific bid/ask, financing, lot limits and lower-timeframe execution before drawing deployment conclusions.','', '## Unavailable / blocked markets','',
        'A fifth distinct commodity was unavailable from the accessible H1 sources. Dukascopy returned HTTP 429 / 503, and FXCM returned HTTP 403. HistData WTI has missing source periods and is excluded from full-period ranking. No gold currency variants, equity indexes, fabricated history or daily-data substitutes were added to increase the commodity count.']
    for failure in failures:
        lines.append(f"- {failure['instrument']}: {failure['error']}")
    lines+=['','## Sources','',
        '[HistData provider FAQ and time convention](https://www.histdata.com/f-a-q/); [HistData instrument universe](https://www.histdata.com/); [Binance public-data schema, microsecond timestamp change and checksums](https://github.com/binance/binance-public-data); [Dukascopy historical export](https://www.dukascopy.com/swiss/english/marketwatch/historical/). Exact downloaded archive URLs and SHA-256 hashes are retained in each instrument manifest and result JSON.',
        '', 'Files: `summary.csv`, `summary.json`, and `runs/<instrument>/{result.json,trades.csv,setups.csv,equity.csv,events.csv,config.json,quality.json,experiments.csv}`.','']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--symbols',nargs='+')
    p.add_argument('--quick',action='store_true')
    args=p.parse_args()
    batch(args.symbols,not args.quick)

if __name__=='__main__':
    main()
