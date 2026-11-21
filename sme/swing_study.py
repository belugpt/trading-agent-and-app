"""Updated swing-origin stop study; original studies remain unchanged."""
import json
import argparse
from pathlib import Path
from . import optimize as opt,research,study2010 as study
from .engine import Engine
from .data import load_csv,ValidatedSeries

class SwingEngine(Engine):
    def advance(self,s,i):
        before=s['state'];super().advance(s,i)
        if before=='WAITING_FOR_STRUCTURE_BREAKOUT' and s['state']=='TRACKING_BREAKOUT_IMPULSE':
            s['stop']=s['origin']-s['direction']*self.c.pip_size/10

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--timeframe',choices=['H1','H4'],default='H1');tf=parser.parse_args().timeframe
    research.DATA=opt.DATA;rows=[];out=study.ROOT/'output'/('swing-study' if tf=='H1' else 'swing-study-h4');out.mkdir(exist_ok=True)
    for symbol in opt.UNIVERSE:
        source=load_csv(opt.DATA/f'{symbol}.csv')
        if tf=='H4':
            from .server import resample_h4
            values=resample_h4(source)
        else:values=source
        bars=ValidatedSeries(values,tf);c=opt.asset_base(symbol)
        r=SwingEngine(c,symbol,timeframe=tf,conversion=research.currency_converter(symbol,{})).run(bars)
        curve=r['equity'];stride=max(1,len(curve)//240)
        points=curve[::stride]+[curve[-1]]
        rows.append(dict(instrument=symbol,asset_class=opt.asset_class(symbol),metrics=r['metrics'],curve=points,start=bars[0].time.isoformat(),end=bars[-1].time.isoformat(),bars=len(bars),unaggregated_h1_bars=len(source)-len(bars)*4 if tf=='H4' else 0,gap_count=r['quality']['gap_count']))
        study.write_json(out/(symbol+'.json'),dict(metrics=r['metrics'],trades=r['trades'],curve=points))
        print(symbol,round(r['metrics']['return_percent'],2),flush=True)
    result=dict(results=rows,timeframe=tf,risk_percent=1,stop='Pre-breakout swing origin plus one inferred tick (pip_size/10)',warning='Research source data, not FBS broker data. Inferred ticks and fixed costs are not verified FBS contract specifications. Includes existing AUDJPY/WTI coverage gaps. H4 uses complete UTC-aligned groups of four H1 bars; incomplete groups excluded. UTC H4 candles may differ from FBS server-aligned candles. No M5 data was synthesized. Per-market $10,000 accounts, not a combined portfolio.')
    study.write_json(out/'summary.json',result)
    bundle=study.ROOT/'platform'/'research.json';data=json.loads(bundle.read_text());data['swing' if tf=='H1' else 'swingH4']=dashboard_bundle(result);bundle.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    lines=['# Updated swing-origin stop backtest','',result['warning'],'','H1, 126/252 SMA OPEN, midpoint entry, −200 target, 1% risk. Original data window through November 2026; crypto starts 2017. No parameters optimized for this run.','', '| Market | Return % | DD % | Trades | Win % |','|---|---:|---:|---:|---:|']
    for row in rows:
        m=row['metrics'];lines.append(f"| {row['instrument']} | {m['return_percent']:.2f} | {m['max_drawdown_percent']:.2f} | {m['completed_trades']} | {m['win_rate']*100:.2f} |")
    if tf=='H4':lines=[line.replace('H1, 126/252','H4, 126/252') for line in lines]
    (out/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
def dashboard_bundle(result):
    compact={**result,'results':[]}
    for row in result['results']:
        points=row['curve'][::2]
        if points[-1]!=row['curve'][-1]:points.append(row['curve'][-1])
        compact['results'].append({**row,'metrics':{k:v for k,v in row['metrics'].items() if not isinstance(v,(dict,list))},'curve':[dict(time=p['time'],equity=round(p['equity'],2)) for p in points]})
    return compact

if __name__=='__main__':main()
