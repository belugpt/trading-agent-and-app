"""Publish completed research evidence without editing locked study implementations."""
import base64,gzip,json,statistics
from collections import Counter
from pathlib import Path
from sme import adaptive_study as a,study2010 as study,research
from sme.analytics import percentile

def main():
    results=[];movements=[];missing=[]
    for symbol in a.opt.UNIVERSE:
        p=a.OUT/'assets'/symbol/'study.json'
        if not p.exists():missing.append(symbol);continue
        r=json.loads(p.read_text())
        if r['signature']!=a.signature(symbol):missing.append(symbol+' stale');continue
        results.append(r);movements+=json.loads((p.parent/'movement.json').read_text())
    if missing:raise ValueError('Incomplete study: '+str(missing))
    rows=[];baselines=[b for r in results for b in r['baselines']]
    for r in results:
        folds=[f for f in r['folds'] if f['status']=='tested'];last=folds[-1]['policy'] if folds else {}
        sel=r['forward']['selected'];ref=r['forward']['baseline'];ts=r['trade_stats']
        rows.append(dict(instrument=r['instrument'],asset_class=r['asset_class'],timeframe=last.get('timeframe','none'),exit=last.get('exit','none'),filter=last.get('gate','cash'),
            baseline_return=ref['return_percent'],selected_return=sel['return_percent'],baseline_dd=ref['max_drawdown_percent'],selected_dd=sel['max_drawdown_percent'],
            trades=ts['completed_trades'],win_rate=ts['win_rate'],windows=r['valid_windows'],cash_windows=r['cash_windows'],double_cost_return=r['double_cost_return'],passes_screen=r['passes_screen']))
    groups=[]
    def group(label,selected):
        if not selected:return
        n=len(selected);rs=[r['r'] for r in selected]
        groups.append(dict(group=label,n=n,win_rate=sum(r['win'] for r in selected)/n,mean_r=statistics.mean(rs),
            median_mfe_r=percentile([r['mfe_full_bars_r'] for r in selected],.5),p75_mfe_r=percentile([r['mfe_full_bars_r'] for r in selected],.75),
            median_mae_r=percentile([r['mae_full_bars_r'] for r in selected],.5),favorable_1R_percent=100*sum(r['favorable_1R'] for r in selected)/n,
            stopped_after_1R_percent=100*sum(r['stopped_after_1R'] for r in selected)/n,
            median_rebound_after_stop_r=percentile([r['post_exit_20bar_favorable_r'] for r in selected if r['exit_reason']=='stop_loss'],.5)))
    for tf in a.TFS:
        subset=[r for r in movements if r['timeframe']==tf];group(tf+' / all',subset)
        for feature in ['session','trend','instrument']:
            for value in sorted({r[feature] for r in subset}):group(tf+' / '+feature+' / '+str(value),[r for r in subset if r[feature]==value])
    research.export_csv(a.OUT/'profiles.csv',rows);research.export_csv(a.OUT/'post-entry-patterns.csv',groups);research.export_csv(a.OUT/'post-entry-trades.csv',movements)
    research.export_csv(a.OUT/'baseline-comparison.csv',[dict(instrument=b['instrument'],timeframe=b['timeframe'],alignment=b['alignment'],**b['metrics']) for b in baselines])
    bundle_path=study.ROOT/'platform'/'research.json';bundle=json.loads(bundle_path.read_text())
    for tf in a.TFS:
        for gate in ['all','higher']:
            key=('swing' if tf=='H1' else 'swing'+tf)+('Aligned' if gate=='higher' else '')
            bundle[key]=dict(timeframe=tf,alignment=gate,results=[b for b in baselines if b['timeframe']==tf and b['alignment']==gate],warning='Mandatory alignment uses closed UTC higher-timeframe candles; research source, not FBS tick/cost validation.')
    bundle['management']=dict(results=rows,behaviour=groups,plan=a.plan(),passes=sum(r['passes_screen'] for r in rows),curves={r['instrument']:dict(selected=r['forward']['selected']['curve'],baseline=r['forward']['baseline']['curve']) for r in results},
        caveat='Training-selected retrospective policies, not production EA settings. Every candidate requires confirmed higher alignment. Earlier history has been inspected. Cash is an explicit decision when evidence fails.')
    bundle_path.write_text(json.dumps(bundle,separators=(',',':')),encoding='utf-8')
    bundle_path.with_suffix('.json.gz').write_bytes(gzip.compress(bundle_path.read_bytes(),mtime=0))
    lines=['# Multi-timeframe strategy and trade-management research','',json.dumps(a.plan(),indent=2),'',
        '## Findings','',f"{len(rows)} markets; {sum(r['passes_screen'] for r in rows)} pass the prespecified retrospective screen. No settings have been automatically applied to live execution.",
        '', 'H1 comparator and selected policies reset flat at identical forward boundaries. Rules are selected using earlier closed trades only with a 24-hour embargo. Minimum 25 training trades, positive training return/mean R, PF >=1.05, two profitable years and capped winner concentration are required. Top two proxy candidates are replayed with actual sizing. If none passes, the next window stays in cash. Timeframe, exit and filter are frozen before testing. Double-cost stress keeps parameters fixed, but cost-sensitive eligibility can change. All candidates require closed lower/higher SMA agreement at formation and again before fill.',
        '', '| Market | Latest tested timeframe | Exit | Filter | Windows | Cash | H1 reference % | Selected % | H1 DD % | Selected DD % | Trades | Double cost % | Screen |',
        '|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in rows:
        vals=[r['instrument'],r['timeframe'],r['exit'],r['filter'],r['windows'],r['cash_windows'],research.fmt(r['baseline_return']),research.fmt(r['selected_return']),research.fmt(r['baseline_dd']),research.fmt(r['selected_dd']),r['trades'],research.fmt(r['double_cost_return']),r['passes_screen']]
        lines.append('| '+' | '.join(map(str,vals))+' |')
    lines+=['','## What happened after entry','',
        'These are descriptive outcomes of the aligned original −200 baseline, not future-known predictors. MFE/MAE use only fully observed bars strictly between fill and exit; ambiguous fill/exit-bar extrema are excluded. Therefore reach frequencies are conservative lower bounds, not exact target probabilities. Trades spanning major data gaps or numerical near-zero risk are excluded. R divides movement by initial price risk. Post-stop rebound examines the next 20 bars after exit; it is counterfactual description, not proof that a wider stop or re-entry is profitable. Means alone are inadequate: report medians, quartiles and sample counts by timeframe, formation session and trend environment.',
        '', '| Group | N | Win % | Mean R | Median MFE R | P75 MFE R | Median MAE R | Confirmed +1R % | Stopped after +1R % |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for g in groups:
        if 'instrument' in g['group']:continue
        vals=[g['group'],g['n'],research.fmt(100*g['win_rate']),research.fmt(g['mean_r']),research.fmt(g['median_mfe_r']),research.fmt(g['p75_mfe_r']),research.fmt(g['median_mae_r']),research.fmt(g['favorable_1R_percent']),research.fmt(g['stopped_after_1R_percent'])]
        lines.append('| '+' | '.join(map(str,vals))+' |')
    lines+=['','H4 forms far fewer setups. Many six-year H4 training windows fail the minimum-25-trade gate; not selecting H4 is insufficient evidence that it is intrinsically inferior. Do not lower sample requirements simply to manufacture a winning profile.',
        '', 'Taking half off at +1R illustrates the trade-off: if the rest returns to the original −1R stop, gross trade profit is approximately zero before costs; if a fixed 5R target would have won, the half-at-1R/half-at-5R payout falls to 3R. The tested partial runner removes the final fixed target and uses a 2R trail. Its actual forward evidence, not the higher apparent win rate, determines whether it qualifies.',
        '', '## Data, clocks and execution','',
        'M15 comes from genuine HistData M1 aggregation or checksum-verified Binance 15m archives. HistData fixed EST is converted to UTC without invented missing minutes; partial buckets are counted. Legacy misaligned crypto days are rebuilt from aggregate trades. Existing AUDJPY and WTI gaps remain. Source manifests retain hashes and failures. Crypto is a USDT spot proxy with synthetic short/margin assumptions, not an FBS CFD. H4 groups require four H1 bars. Higher confirmation series use nonempty UTC H1/H4/calendar-day groups and become available only at the group close. Daily partial/weekend bars and UTC boundaries can differ from FBS-REAL server candles.',
        '', 'Formation sessions are research windows: London 08–16 local, New York 08–16 local, overlap, Tokyo 09–17 local, or Other. Post-2007 UK/US daylight-saving rules are applied explicitly; no missing timezone package is silently replaced with fixed UTC offsets. These are broad financial-session proxies, including on crypto weekends, not exchange trading calendars. Trend environment uses only known directional fast-MA change over 24 bars and MA separation divided by ATR14; aligned means both >=0.5. Low-cost filter requires estimated costs <=10% of stop distance; minimum-stop filter requires initial stop distance >=ATR14. No news-calendar filter is claimed.',
        '', 'Risk is 1% per entry with original account-currency conversion and leverage approximations. Multiple independent setups may overlap; there is no added averaging down or discretionary pyramiding, but this research is not an account-wide risk-reservation implementation. Partial exits take half at +1R only after the fill candle; stop-first ambiguity precedes partial credit. Runners activate a trail after a fully closed post-entry candle reaches +1R, use only completed bars, and ratchet for the next bar. ATR3 uses a simple mean of 14 true ranges. Limit/stop execution is OHLC-conservative; funding, financing, swaps and commodity roll costs are omitted. FBS contract values and server data still require terminal verification.',
        '', 'Exact forward MTM drawdown is computed from all equity marks; display curves are sampled. Forward returns chain independently restarted test accounts; full-history results are a separate comparison. Unequal valid windows prohibit a fair universal cross-asset yield ranking. Retrospective multiple testing remains even with chronological splits; a passing basic screen is not proof of future edge.',
        '', '## Per-market frozen decisions','']
    for r in results:
        lines += ['### '+r['instrument'],'']
        for f in r['folds']:
            if f['status']!='tested':lines.append(str(f['year'])+': excluded — '+f['reason']);continue
            lines.append(str(f['year'])+': '+json.dumps(f['policy'])+'; selected return '+research.fmt(f['selected']['return_percent'])+'%; reference '+research.fmt(f['baseline']['return_percent'])+'%; stress '+research.fmt(f['double_cost']['return_percent'])+'%.')
        lines+=['','Mean-R block-bootstrap uncertainty: '+json.dumps(r['bootstrap']),'']
    lines+=['## Research context','',
        '[Bailey et al.: Probability of backtest overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf). [Bank of Canada: FX fixings and intraday returns](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/). These motivate disciplined testing, not a promise that this strategy or a session filter works.','']
    report='\n'.join(lines);(a.OUT/'REPORT.md').write_text(report,encoding='utf-8');(study.ROOT/'platform'/'MANAGEMENT_REPORT.md').write_text(report,encoding='utf-8')
    m15=[b for b in baselines if b['timeframe']=='M15'];m15lines=['# M15 swing-stop backtest: alignment comparison','',
       '2010 through available November 2026 history; crypto begins 2017. 126/252 SMA OPEN, midpoint entry, swing-origin stop plus inferred tick, −200 target, $10,000 per market and 1% risk. Native M15 or genuine M1 aggregation, never H1 upsampling. Research costs/data are not FBS validation. Aligned version requires latest closed lower and H1 SMA agreement before placement and fill.','',
       '| Market | Alignment | Return % | DD % | Trades | Win % |','|---|---|---:|---:|---:|---:|']
    for b in m15:
        m=b['metrics'];m15lines.append(f"| {b['instrument']} | {b['alignment']} | {m['return_percent']:.2f} | {m['max_drawdown_percent']:.2f} | {m['completed_trades']} | {100*m['win_rate']:.2f} |")
    (study.ROOT/'platform'/'M15_BACKTEST.md').write_text('\n'.join(m15lines),encoding='utf-8')
    (study.ROOT/'platform'/'MT5_PACKAGE.txt').write_text(base64.b64encode((study.ROOT/'mt5'/'SME_MT5_Package.zip').read_bytes()).decode(),encoding='ascii')
    study.write_json(a.OUT/'summary.json',dict(results=rows,behaviour=groups,missing=missing))
    print('Compiled',len(rows),'markets;',len(movements),'movement rows;',sum(r['passes_screen'] for r in rows),'screen passes',flush=True)

if __name__=='__main__':main()
