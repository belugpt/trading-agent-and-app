"""Extend the existing study to 2010 without overwriting the 2020 dataset or reports."""
import argparse
import concurrent.futures
import hashlib
import json
import time
import uuid
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from . import research
from .download import ROOT, FOREX, CRYPTO, request, histdata_period, binance_month
from .data import load_csv, save_csv, quality, ValidatedSeries
from .model import Bar, Config
from .engine import Engine
from .analytics import bootstrap
from .crypto_history import repair_misaligned
from .research import baseline, category, export_csv, fmt

DATA=ROOT/'data'/'h1_2010'
OUT=ROOT/'output'/'study2010'
BASE=ROOT/'data'/'h1'
START=datetime(2010,1,1,tzinfo=timezone.utc)
JOIN=datetime(2020,1,1,tzinfo=timezone.utc)
END=datetime(2026,11,17,tzinfo=timezone.utc)
UNIVERSE=FOREX+['XAUUSD','XAGUSD','WTIUSD','BCOUSD']+CRYPTO


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp-'+uuid.uuid4().hex)
    temporary.write_text(json.dumps(value,allow_nan=False,separators=(',',':')),encoding='utf-8')
    for attempt in range(8):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt==7:
                raise
            time.sleep(min(.05*2**attempt,1))


def decode_bars(rows):
    return [Bar(datetime.fromisoformat(r['time']),*(r[k] for k in ('open','high','low','close','volume'))) for r in rows]


def history_part(symbol,year,month=None):
    period=str(year)+(f'-{month:02}' if month else '')
    path=DATA/'parts'/f'{symbol}-{period}.json'
    if path.exists():
        saved=json.loads(path.read_text(encoding='utf-8'))
        return decode_bars(saved['bars']),saved['provenance']
    bars,meta=binance_month(symbol,year,month) if symbol in CRYPTO else histdata_period(symbol,year,month)
    if not bars:
        raise ValueError('Published archive contains no valid H1 candles')
    write_json(path,dict(bars=[b.json() for b in bars],provenance=meta))
    return bars,meta


def merge_histories(older,recent,start=START,end=END):
    by_time={}
    conflicts=set()
    for bar in older+recent:
        if not start<=bar.time or bar.time+timedelta(hours=1)>end:
            continue
        previous=by_time.get(bar.time)
        if previous is not None and previous!=bar:
            conflicts.add(bar.time)
        else:
            by_time[bar.time]=bar
    return [by_time[t] for t in sorted(by_time) if t not in conflicts],[t.isoformat() for t in sorted(conflicts)]


def download(symbols,workers=2):
    DATA.mkdir(parents=True,exist_ok=True)
    for symbol in symbols:
        base=load_csv(BASE/f'{symbol}.csv')
        original=json.loads((BASE/f'{symbol}.manifest.json').read_text(encoding='utf-8'))
        source_first=None
        if symbol in CRYPTO:
            pair=symbol.replace('USD','USDT')
            url=f'https://api.binance.com/api/v3/klines?symbol={pair}&interval=1h&startTime={int(START.timestamp()*1000)}&endTime={int(JOIN.timestamp()*1000)-1}&limit=1'
            first=json.loads(request(url))
            if not first:
                raise ValueError(f'{symbol}: source has no pre-2020 history')
            source_first=datetime.fromtimestamp(first[0][0]/1000,timezone.utc)
            write_json(DATA/'parts'/f'{symbol}-first-available.json',dict(url=url,response=first,first_available=source_first.isoformat()))
            tasks=[(year,month) for year in range(source_first.year,2020) for month in range(1,13)
                   if (year,month)>=(source_first.year,source_first.month)]
        else:
            tasks=[(year,None) for year in range(2010,2020)]
        older,files,errors=[],[],[]
        def fetch(task):
            year,month=task
            for attempt in range(3):
                try:
                    return history_part(symbol,year,month)
                except (ConnectionResetError,ConnectionAbortedError) as exc:
                    if attempt<2:
                        time.sleep(attempt+1)
                        continue
                    return [],dict(year=year,month=month,error=str(exc))
                except Exception as exc:
                    return [],dict(year=year,month=month,error=str(exc))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for bars,meta in pool.map(fetch,tasks):
                older.extend(bars)
                (errors if 'error' in meta else files).append(meta)
                write_json(DATA/f'{symbol}.progress.json',dict(completed=len(files),failed=len(errors),total=len(tasks),errors=errors))
                print(symbol,'historical periods',len(files),'/',len(tasks),'failed',len(errors),flush=True)
        crypto_repairs=[]
        if symbol in CRYPTO:
            older,crypto_repairs=repair_misaligned(symbol,older)
        bars,conflicts=merge_histories(older,base)
        combined_errors=errors+original.get('errors',[])
        if conflicts:
            combined_errors.append(dict(error='Conflicting overlapping H1 records excluded',hours=conflicts))
        q=quality(bars,continuous=symbol in CRYPTO)
        if not q['valid']:
            raise ValueError(f'{symbol}: '+str(q['errors'][:5]))
        save_csv(DATA/f'{symbol}.csv',bars,symbol)
        manifest={**original, 'requested_start':START.isoformat(),'requested_end_exclusive':END.isoformat(),
                  'source_first_available':source_first.isoformat() if source_first else None,
                  'shortened_history':bars[0].time>START+timedelta(days=4),
                  'quality':q,'files':files+original.get('files',[]),'errors':combined_errors,
                  'early_crypto_timestamp_repairs':crypto_repairs,
                  'fetched_at':datetime.now(timezone.utc).isoformat(),
                  'merge_policy':'Identical overlap deduplicated; whole conflicting hours excluded; original 2020 files untouched.'}
        write_json(DATA/f'{symbol}.manifest.json',manifest)
        print(symbol,'EXTENDED',q['start'],'to',q['end'],'bars',len(bars),'failed periods',len(combined_errors),flush=True)


def signature(symbol,config):
    digest=hashlib.sha256(json.dumps(asdict(config),sort_keys=True).encode())
    paths=[DATA/f'{symbol}.csv']
    if not symbol.startswith('USD') and not symbol.endswith('USD'):
        quote=symbol[-3:]
        paths.append(DATA/(('USD'+quote if quote in ('JPY','CHF','CAD') else quote+'USD')+'.csv'))
    paths += [ROOT/'sme'/f'{name}.py' for name in ['model','data','engine','analytics','study2010','crypto_history']]
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def comparisons(symbol,bars,config,conversion):
    rows=[]
    windows=[('Additional historical period 2010–2019',lambda b:b.time<JOIN),
             ('2020–2023',lambda b:JOIN<=b.time<datetime(2024,1,1,tzinfo=timezone.utc)),
             ('2024 onward (previously seen diagnostic)',lambda b:b.time>=datetime(2024,1,1,tzinfo=timezone.utc))]
    for label,predicate in windows:
        subset=[b for b in bars if predicate(b)]
        if subset:
            r=Engine(config,symbol,conversion=conversion).run(subset)
            rows.append(dict(label=label,kind='separate_flat_start_era',metrics=r['metrics']))
    for year in sorted({b.time.year for b in bars}):
        r=Engine(config,symbol,conversion=conversion).run([b for b in bars if b.time.year==year])
        rows.append(dict(label=str(year),kind='separate_flat_start_year',metrics=r['metrics']))
    stressed=replace(config,name=config.name+' / double costs',spread=config.spread*2,
                     slippage=config.slippage*2,commission_per_million=config.commission_per_million*2)
    r=Engine(stressed,symbol,conversion=conversion).run(bars)
    rows.append(dict(label='Double modeled transaction costs',kind='cost_sensitivity',metrics=r['metrics']))
    return rows


def run_research(symbols):
    research.DATA=DATA  # Reference conversions use the extended source in this process only.
    OUT.mkdir(parents=True,exist_ok=True)
    cache={}
    for symbol in symbols:
        try:
            config=baseline(symbol)
            code_signature=signature(symbol,config)
            folder=OUT/'runs'/symbol
            saved=json.loads((folder/'result.json').read_text(encoding='utf-8')) if (folder/'result.json').exists() else {}
            if saved.get('study_signature')==code_signature:
                print(symbol,'unchanged completed study reused',flush=True)
                continue
            if symbol not in cache:
                cache[symbol]=ValidatedSeries(load_csv(DATA/f'{symbol}.csv'))
            bars=cache[symbol]
            conversion=research.currency_converter(symbol,cache)
            result=Engine(config,symbol,conversion=conversion).run(bars)
            result.update(study_signature=code_signature,
                          provenance=json.loads((DATA/f'{symbol}.manifest.json').read_text(encoding='utf-8')),
                          bootstrap=bootstrap(result['trades']),
                          comparisons=comparisons(symbol,bars,config,conversion))
            write_json(folder/'result.json',result)
            write_json(folder/'config.json',asdict(config))
            write_json(folder/'quality.json',result['quality'])
            for name in ['trades','setups','events','equity']:
                export_csv(folder/f'{name}.csv',result[name])
            export_csv(folder/'comparisons.csv',[dict(label=e['label'],kind=e['kind'],**{k:v for k,v in e['metrics'].items() if not isinstance(v,(list,dict))}) for e in result['comparisons']])
            m=result['metrics']
            print(symbol,'DONE return',round(m['return_percent'],2),'DD',round(m['max_drawdown_percent'],2),'closed',m['completed_trades'],flush=True)
        except Exception as exc:
            write_json(OUT/'failures'/f'{symbol}.json',dict(instrument=symbol,error=str(exc)))
            print(symbol,'RESEARCH FAILED',exc,flush=True)


def report():
    results,rows,failures=[],[],[]
    original=json.loads((ROOT/'output'/'summary.json').read_text(encoding='utf-8'))
    original_by={r['instrument']:r for r in original['results']}
    for symbol in UNIVERSE:
        path=OUT/'runs'/symbol/'result.json'
        if not path.exists():
            failures.append(dict(instrument=symbol,error='No completed extended run'))
            continue
        r=json.loads(path.read_text(encoding='utf-8'))
        if r['study_signature']!=signature(symbol,Config(**r['config'])):
            failures.append(dict(instrument=symbol,error='Saved run is stale relative to source/settings/code'))
            continue
        results.append(r)
        m,p=r['metrics'],r['provenance']
        comparable=not p['errors'] and datetime.fromisoformat(r['quality']['start'])<=START+timedelta(days=4)
        row=dict(instrument=symbol,category=category(symbol),start=r['quality']['start'],end=r['quality']['end'],
                 bars=r['quality']['bars'],failed_source_periods=len(p['errors']),
                 full_2010_history=comparable,crypto_available_history=(symbol in CRYPTO and not p['errors']),
                 ranking_eligible=(not p['errors'] if symbol in CRYPTO else comparable),
                 **{k:v for k,v in m.items() if not isinstance(v,(dict,list))},
                 original_2020_return_percent=original_by[symbol]['return_percent'])
        rows.append(row)
    write_json(OUT/'summary.json',dict(results=rows,failures=failures))
    export_csv(OUT/'summary.csv',rows)
    lines=['# SME H1 extended-history backtest: 2010–2026','',
      'Requested window: 1 January 2010 through 17 November 2026 UTC (exclusive cutoff). The original 2020 study and dataset are preserved. Actual source coverage is shown for every instrument. Forex/commodity suffixes end 13 November 2026; crypto suffixes end 16 November 2026.',
      '',f'{len(results)} completed runs; {sum(r["bars"] for r in rows):,} H1 candles; {sum(r["completed_trades"] for r in rows):,} completed trades across independent accounts. Figures are cumulative simulated returns, not annual yields or a combined portfolio.',
      '', '## Unchanged strategy and assumptions','',
      '126 SMA / 252 SMA calculated from OPEN, H1; 50-bar prior structure; 0.1% price reversal to confirm retracement; deepest retracement extreme before breakout as origin. Wick breakout required; endpoint extends until qualifying retracement, then freezes. Midpoint limit entry; stop at original crossover candle; target two swing ranges beyond the endpoint. Open-MA opposite crosses cancel unfilled orders at open; new stops become known only at that candle’s close. New pending orders are eligible next bar; no retrospective fills. Ambiguous execution uses the original conservative stop-first policy.',
      '', 'Each instrument starts with a separate $10,000 USD balance and 1% balance risk, subject to the same exposure caps and fractional sizing conventions as the 2020 study. Fixed spread, stop slippage and commission assumptions are unchanged, including when applied to older years. They are not reconstructed historical broker costs. Financing, swaps, borrow/funding, roll adjustments and margin-liquidation mechanics remain excluded. Crypto is Binance USDT spot-price proxy data with synthetic shorts and USDT treated as USD. Pip/contract conventions and exact costs are recorded in every config JSON.',
      '', '2010–2019 provides additional historical observations with the already chosen baseline; no parameters are optimized. The 2024-onward segment has already been inspected in the earlier study and is a temporal diagnostic, not a new untouched holdout. Selecting instruments from these rankings adds selection bias. Bootstrap intervals do not correct for multiple comparisons or fully capture regime dependence.',
      '', '## Rankings','']
    for group in ['forex','commodities','crypto']:
        selected=[row for row in rows if row['category']==group and (row['crypto_available_history'] if group=='crypto' else row['full_2010_history'])]
        selected.sort(key=lambda row:row['return_percent'],reverse=True)
        lines += ['### '+group.title()+(' — available exchange history, not 2010' if group=='crypto' else ' — full 2010 coverage only'),'',
                  '| Rank | Instrument | First bar | Return % | CAGR % | Max DD % | Closed trades | Win % | PF | Original 2020-run return % |',
                  '|---:|---|---|---:|---:|---:|---:|---:|---:|---:|']
        for i,row in enumerate(selected,1):
            lines.append('| '+' | '.join(map(str,[i,row['instrument'],row['start'][:10],fmt(row['return_percent']),fmt(row.get('cagr_percent')),fmt(row['max_drawdown_percent']),row['completed_trades'],fmt(row['win_rate']*100 if row['win_rate'] is not None else None),fmt(row['profit_factor']),fmt(row['original_2020_return_percent'])]))+' |')
        if group!='crypto' and len(selected)<5:
            lines+=['',f'Only {len(selected)} instruments meet complete requested-history criteria; a top five is not substantiated. Shortened/incomplete histories are shown below, not mixed into this ranking.']
        lines+=['']
    lines+=['## All coverage and results','', '| Instrument | Start UTC | Last UTC bar | Bars | Failed periods | Full 2010? | Return % | DD % |', '|---|---|---|---:|---:|---|---:|---:|']
    for row in rows:
        lines.append(f"| {row['instrument']} | {row['start']} | {row['end']} | {row['bars']} | {row['failed_source_periods']} | {row['full_2010_history']} | {fmt(row['return_percent'])} | {fmt(row['max_drawdown_percent'])} |")
    lines+=['','Source archives are cached with hashes and URLs. Minute timestamps use the provider’s fixed EST convention and are converted to UTC. Conflicting duplicate-minute hours are excluded and recorded, as in the original study. Identical overlap is deduplicated; conflicting overlapping H1 hours are excluded. Off-hour timestamps in early crypto archives are repaired by rebuilding entire affected UTC days from checksum-verified aggregate trades; old candle timestamps are never merely rounded. Both source versions and repair metadata are retained. Gaps are reported, not filled. Market-session and holiday calendars have not been independently reconciled. Missing annual archives and shorter exchange histories do not become invented 2010 candles.','', '## Per-instrument breakdown','']
    for r in results:
        symbol=r['instrument'];m=r['metrics'];ci=m['win_rate_95ci']
        lines += [f'### {symbol}','',f"Coverage: {r['quality']['start']} through {r['quality']['end']}; {len(r['provenance']['errors'])} failed source periods. Actual starts and missing periods govern comparability.",'',
          f"Setups {m['total_setups']}; structural breakouts {m['qualified_setups']}; filled {m['total_trades']}; closed {m['completed_trades']}; open {m['open_trades']}. Terminal MTM equity ${fmt(m['final_equity'])}; realized net P/L ${fmt(m['net_profit'])}; expectancy ${fmt(m['expectancy'])}; mean R {fmt(m['average_r'])}.",'',
          f"Win-rate Wilson 95% interval {fmt(ci[0]*100 if ci[0] is not None else None)}%–{fmt(ci[1]*100 if ci[1] is not None else None)}%. Gross winning/losing P/L ${fmt(m['gross_profit'])}/${fmt(m['gross_loss'])}; average winner/loser ${fmt(m['average_win'])}/${fmt(m['average_loss'])}; best/worst ${fmt(m['best_trade'])}/${fmt(m['worst_trade'])}. Closed-trade modeled costs ${fmt(m['total_transaction_costs'])}; mean holding time {fmt(m['average_holding_hours'])}h; longest win/loss streak {m['consecutive_wins']}/{m['consecutive_losses']}.",'',
          'Rejections/unresolved: '+json.dumps(m['rejected_or_unresolved'])+'.','',
          'Bootstrap: '+json.dumps(r['bootstrap'])+'.','',
          '| Separate restart / sensitivity | Return % | DD % | Closed trades | PF | Mean R |','|---|---:|---:|---:|---:|---:|']
        for comparison in r['comparisons']:
            x=comparison['metrics']
            lines.append(f"| {comparison['label']} | {fmt(x['return_percent'])} | {fmt(x['max_drawdown_percent'])} | {x['completed_trades']} | {fmt(x['profit_factor'])} | {fmt(x['average_r'])} |")
        lines += ['', 'Yearly returns from the continuously carried full-history account: '+json.dumps(m['annual_returns'])+'.','',
                  'Bootstrap profit factor is R-weighted; primary table PF is dollar-weighted. Drawdown resampling is in additive R. Excursions remain conservative close-observed lower bounds, not tick-exact maxima. Entry/exit times have H1 candle precision. Full source errors: '+json.dumps(r['provenance']['errors'])+'.','']
    lines += ['## Audit and source files','',
              'Per-instrument result JSON contains all events, setups, trades, equity, drawdowns, segments and monthly returns. CSVs and exact configs are in `runs/<instrument>/`. `audit.json` records independent replay checks when the audit command completes.',
              '', '[HistData source conventions](https://www.histdata.com/f-a-q/) · [Binance public data and checksums](https://github.com/binance/binance-public-data)',
              '', 'Failed/unavailable study runs: '+json.dumps(failures), '']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Extended report assembled',len(rows),'runs;',len(failures),'missing/stale',flush=True)


def audit():
    research.DATA=DATA
    cache={};records=[]
    for symbol in UNIVERSE:
        path=OUT/'runs'/symbol/'result.json'
        if not path.exists():
            continue
        old=json.loads(path.read_text(encoding='utf-8'));c=Config(**old['config'])
        fresh=Engine(c,symbol,conversion=research.currency_converter(symbol,cache)).run(ValidatedSeries(load_csv(DATA/f'{symbol}.csv')))
        for field in ['trades','setups','events','equity','metrics','fast','slow']:
            if old[field]!=fresh[field]:
                raise AssertionError(f'{symbol}: {field} does not reproduce')
        records.append(dict(instrument=symbol,reproduced=True,signature_matches=old['study_signature']==signature(symbol,c)))
        print(symbol,'extended baseline reproduced',flush=True)
    write_json(OUT/'audit.json',records)


def repair():
    """Retry operational failures; do not repeatedly request unpublished archives."""
    for attempt in range(2):
        symbols=[]
        for path in DATA.glob('*.manifest.json'):
            manifest=json.loads(path.read_text(encoding='utf-8'))
            if any(e.get('year',2020)<2020 and 'No downloadable archive' not in e.get('error','')
                   for e in manifest['errors']):
                symbols.append(manifest['instrument'])
        if not symbols:
            print('No transient pre-2020 source failures remain',flush=True)
            return
        print('Retrying incomplete historical downloads',symbols,'pass',attempt+1,flush=True)
        download(symbols,workers=1)


def serve(port):
    from . import server
    research.DATA=DATA
    server.DATA=DATA
    server.OUT=OUT
    print(f'2010 study dashboard: http://127.0.0.1:{port}',flush=True)
    server.ThreadingHTTPServer(('127.0.0.1',port),server.Handler).serve_forever()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['download','research','report','audit','repair','serve'])
    parser.add_argument('--symbols',nargs='+',choices=UNIVERSE)
    parser.add_argument('--workers',type=int,default=2,choices=[1,2,3])
    parser.add_argument('--port',type=int,default=8767)
    args=parser.parse_args();symbols=args.symbols or UNIVERSE
    if args.action=='download': download(symbols,args.workers)
    elif args.action=='research': run_research(symbols)
    elif args.action=='report': report()
    elif args.action=='repair': repair()
    elif args.action=='serve': serve(args.port)
    else: audit()

if __name__=='__main__': main()
