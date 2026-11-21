"""Verify source signatures, original comparators and independent frozen-policy replay."""
import argparse,bisect,json
from datetime import datetime
from pathlib import Path
from sme import adaptive_study as a,study2010 as study
from sme.adaptive_engine import simulate
from sme.data import load_csv,ValidatedSeries
from sme.server import resample_h4

def main():
    p=argparse.ArgumentParser();p.add_argument('--symbols',nargs='+',default=a.opt.UNIVERSE);args=p.parse_args()
    old={tf:{r['instrument']:r for r in json.loads((study.ROOT/'output'/folder/'summary.json').read_text())['results']} for tf,folder in [('H1','swing-study'),('H4','swing-study-h4')]}
    checks=[]
    for symbol in args.symbols:
        saved=json.loads((a.OUT/'assets'/symbol/'study.json').read_text());assert saved['signature']==a.signature(symbol),symbol+' stale'
        for b in saved['baselines']:
            if b['alignment']=='all' and b['timeframe'] in old:
                previous=old[b['timeframe']][symbol]['metrics']
                for k,v in b['metrics'].items():assert previous[k]==v,(symbol,b['timeframe'],k,previous[k],v)
        folds=[f for f in saved['folds'] if f['status']=='tested']
        for f in folds:
            assert f['selection_cutoff']<f['test_start'];assert f['policy']['gate']=='cash' or f['policy']['gate'].startswith('higher')
            for t in f['selected_trades']:
                assert t['entry_features']['higher_aligned'],symbol+' unconfirmed order'
                assert t['entry_features']['known_at']<=t['entry_time'],symbol+' future entry feature'
        if folds:
            f=folds[-1];policy=f['policy'];tf=policy['timeframe'];start=datetime.fromisoformat(f['test_start']);end=datetime.fromisoformat(f['test_end'])
            hourly=load_csv(a.opt.DATA/f'{symbol}.csv');bars=load_csv(a.M15/f'{symbol}.csv') if tf=='M15' else hourly if tf=='H1' else resample_h4(hourly)
            times=[b.time for b in bars];first=bisect.bisect_left(times,start);last=bisect.bisect_left(times,end);warm=max(0,first-1260)
            result=simulate(ValidatedSeries(bars[warm:last],tf),a.opt.asset_base(symbol),symbol,a.converter(symbol,tf),tf,exit_name=policy['exit'],gate=policy['gate'],activation=start,flatten=True,higher=a.higher_series(hourly,tf))
            assert a.slim(result)==f['selected'],symbol+' replay metrics differ'
            assert result['trades']==f['selected_trades'],symbol+' replay trades differ'
        meta=json.loads((a.M15/f'{symbol}.manifest.json').read_text());assert meta['quality']['valid']
        checks.append(dict(instrument=symbol,signature=True,original_H1_H4_comparators_equal=True,latest_frozen_policy_replay_equal=True,m15_quality_valid=True))
        print(symbol,'AUDITED',flush=True)
    study.write_json(a.OUT/'verification'/('-'.join(args.symbols[:1])+'.json'),dict(checks=checks))
if __name__=='__main__':main()
