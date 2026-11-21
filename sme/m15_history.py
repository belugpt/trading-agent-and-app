"""Genuine minute archives -> UTC M15; never upsample hourly candles."""
import argparse,csv,hashlib,io,json,math,zipfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
from . import optimize as opt,study2010 as study
from .download import CACHE,cached
from .model import Bar
from .data import save_csv,quality
DATA=study.ROOT/'data'/'m15'

def minute_archive(path):
    groups={};bad=set();duplicates=0;counts={}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith('.csv'):continue
            with archive.open(name) as raw:
                for row in csv.reader(io.TextIOWrapper(raw,encoding='utf-8-sig'),delimiter=';'):
                    t=row[0];minute=int(t[11:13]);key=t[:11]+f'{minute//15*15:02}'
                    o,h,l,c=map(float,row[1:5]);v=float(row[5]) if len(row)>5 else 0
                    if not all(math.isfinite(x) for x in (o,h,l,c,v)) or not 0<l<=min(o,c)<=max(o,c)<=h or v<0:raise ValueError('Invalid M1 OHLC')
                    bit=1<<(minute%15)
                    if key not in groups:groups[key]=[o,h,l,c,v,t,t,0]
                    x=groups[key]
                    if x[7]&bit:bad.add(key);duplicates+=1;continue
                    x[7]|=bit
                    x[1]=max(x[1],h);x[2]=min(x[2],l)
                    if t<x[5]:x[0]=o;x[5]=t
                    if t>x[6]:x[3]=c;x[6]=t
                    # First row already contributes its volume.
                    if x[7]!=bit:x[4]+=v
    bars=[];partial=0
    for key,x in sorted(groups.items()):
        if key in bad:continue
        stamp=datetime(int(key[:4]),int(key[4:6]),int(key[6:8]),int(key[9:11]),int(key[11:13]),tzinfo=timezone.utc)+timedelta(hours=5)
        if x[7].bit_count()<15:partial+=1
        bars.append(Bar(stamp,*x[:5]))
    return bars,dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),duplicate_minutes=duplicates,excluded_buckets=len(bad),partial_buckets=partial,bars=len(bars))

def local_asset(symbol):
    DATA.mkdir(exist_ok=True)
    target=DATA/f'{symbol}.csv'
    if target.exists() and target.with_suffix('.manifest.json').exists():print(symbol,'M15 cached',flush=True);return
    files=[]
    for year in range(2010,2027):
        annual=CACHE/'histdata'/f'{symbol}-{year}.zip'
        files+= [annual] if annual.exists() else sorted((CACHE/'histdata').glob(f'{symbol}-{year}-*.zip'))
    merged={};conflicts=set();meta=[]
    for path in files:
        bars,info=minute_archive(path);meta.append(info)
        for b in bars:
            if not study.START<=b.time or b.time+timedelta(minutes=15)>study.END:continue
            if b.time in merged and merged[b.time]!=b:conflicts.add(b.time)
            else:merged[b.time]=b
        print(symbol,path.name,len(bars),flush=True)
    bars=[b for t,b in sorted(merged.items()) if t not in conflicts]
    if not bars:raise ValueError(symbol+' has no cached M1 source')
    save_csv(target,bars,symbol,'M15');study.write_json(target.with_suffix('.manifest.json'),dict(instrument=symbol,source='HistData cached real M1 -> UTC M15',source_timezone='fixed EST UTC-5; converted UTC',price_basis='bid',quality=quality(bars,'M15'),files=meta,conflicting_buckets=len(conflicts),note='Partial buckets retained and counted; no fabricated missing minutes. Existing AUDJPY/WTI archive gaps remain. Not FBS broker data.'))
    print(symbol,'M15 DONE',len(bars),flush=True)

def crypto_asset(symbol):
    DATA.mkdir(exist_ok=True);target=DATA/f'{symbol}.csv'
    if target.exists() and target.with_suffix('.manifest.json').exists():print(symbol,'M15 cached',flush=True);return
    pair=symbol.replace('USD','USDT');start=(2017,11) if symbol=='BNBUSD' else (2017,8)
    tasks=[(y,m,None) for y in range(2017,2027) for m in range(1,13) if start<=(y,m)<(2026,11)]+[(2026,11,d) for d in range(1,17)]
    bars={};files=[];errors=[];bad_days=set()
    for y,m,d in tasks:
        period=f'{y}-{m:02}'+(f'-{d:02}' if d else '');name=f'{pair}-15m-{period}.zip'
        url=f'https://data.binance.vision/data/spot/{"daily" if d else "monthly"}/klines/{pair}/15m/{name}'
        try:
            payload=cached(url,CACHE/'binance-m15'/name,checksum=True)
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                for row in csv.reader(io.StringIO(archive.read(archive.namelist()[0]).decode())):
                    n=int(row[0]);stamp=datetime.fromtimestamp(n/(1e6 if n>10**14 else 1000),timezone.utc)
                    if stamp.timestamp()%900:
                        bad_days.add(stamp.date().isoformat());continue
                    if stamp+timedelta(minutes=15)<=study.END:bars[stamp]=Bar(stamp,*(float(row[i]) for i in (1,2,3,4,5)))
            files.append(dict(url=url,sha256=hashlib.sha256(payload).hexdigest()))
        except Exception as e:errors.append(dict(period=period,error=str(e)))
        print(symbol,'M15',period,'files',len(files),'errors',len(errors),flush=True)
    repairs=[]
    for day in sorted(bad_days):
        bars={t:b for t,b in bars.items() if t.date().isoformat()!=day}
        name=f'{pair}-aggTrades-{day}.zip';url=f'https://data.binance.vision/data/spot/daily/aggTrades/{pair}/{name}'
        try:
            payload=cached(url,CACHE/'binance'/name,checksum=True);groups={}
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                with archive.open(archive.namelist()[0]) as raw:
                    for row in csv.reader(io.TextIOWrapper(raw,encoding='utf-8-sig')):
                        if not row or not row[0].isdigit():continue
                        n=int(row[5]);seconds=n/(1e6 if n>10**14 else 1000);t=datetime.fromtimestamp(seconds,timezone.utc)
                        if t.date().isoformat()!=day:raise ValueError('Aggregate trade day mismatch')
                        price,volume=float(row[1]),float(row[2]);key=int(seconds)//900*900
                        if key not in groups:groups[key]=[price,price,price,price,volume]
                        else:
                            g=groups[key];g[1]=max(g[1],price);g[2]=min(g[2],price);g[3]=price;g[4]+=volume
            for n,g in groups.items():
                t=datetime.fromtimestamp(n,timezone.utc);bars[t]=Bar(t,*g)
            repairs.append(dict(day=day,url=url,sha256=hashlib.sha256(payload).hexdigest(),bars=len(groups)))
        except Exception as e:errors.append(dict(day=day,error=str(e)))
    values=[b for _,b in sorted(bars.items())];save_csv(target,values,symbol,'M15');study.write_json(target.with_suffix('.manifest.json'),dict(instrument=symbol,source='Binance checksum-verified native 15m archives',quality=quality(values,'M15'),files=files,errors=errors,repairs=repairs,note='USDT spot proxy, not FBS CFD; misaligned days rebuilt from verified aggregate trades, never rounded.'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--symbols',nargs='+',default=opt.UNIVERSE);args=p.parse_args()
    for symbol in args.symbols:
        if symbol in study.CRYPTO:crypto_asset(symbol)
        else:local_asset(symbol)
if __name__=='__main__':main()
