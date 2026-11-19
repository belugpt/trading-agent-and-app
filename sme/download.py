"""Public source downloads with raw-file cache, hashes and explicit coverage manifests."""
import argparse
import concurrent.futures
import csv
import hashlib
import io
import json
import re
import time
import urllib.request
import urllib.error
import urllib.parse
import http.client
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .model import Bar
from .data import save_csv, quality

FOREX = ['EURUSD','GBPUSD','AUDUSD','NZDUSD','USDJPY','USDCHF','USDCAD',
         'EURGBP','EURJPY','EURCHF','EURAUD','EURCAD','EURNZD',
         'GBPJPY','GBPCHF','GBPAUD','GBPCAD','GBPNZD','AUDJPY','CADJPY','NZDJPY']
COMMODITIES = ['XAUUSD','XAGUSD','BRENTCMDUSD','LIGHTCMDUSD','GASCMDUSD','COPPERCMDUSD',
               'DIESELCMDUSD','XPTCMDUSD','XPDCMDUSD','COCOACMDUSD','COFFEECMDUSX',
               'COTTONCMDUSX','OJUICECMDUSX','SOYBEANCMDUSX','SUGARCMDUSD']
CRYPTO = ['BTCUSD','ETHUSD','BNBUSD']
ROOT=Path(__file__).resolve().parent.parent
CACHE=ROOT/'data'/'raw'
DATA=ROOT/'data'/'h1'


def request(url, *, data=None, referer=None, timeout=25):
    headers={'User-Agent':'SME-Research/1.0 (personal historical backtest)'}
    if referer:
        headers['Referer']=referer
    req=urllib.request.Request(url,data=data,headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError:
            # Do not retry rate limits, forbidden responses or unpublished archives.
            raise
        except (urllib.error.URLError,TimeoutError,http.client.IncompleteRead):
            if attempt==2:
                raise
            time.sleep(2**attempt)


def cached(url, target, checksum=False):
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        return target.read_bytes()
    last=None
    for attempt in range(3):
        try:
            payload=request(url)
            if checksum:
                expected=request(url+'.CHECKSUM').decode().split()[0]
                if hashlib.sha256(payload).hexdigest()!=expected:
                    raise ValueError('Provider checksum mismatch')
            target.write_bytes(payload)
            return payload
        except urllib.error.HTTPError as exc:
            if exc.code in (403,404,429):
                raise
            last=exc
        except (TimeoutError,urllib.error.URLError) as exc:
            last=exc
        time.sleep(1+attempt)
    raise last


def binance_month(symbol,year,month):
    pair=symbol.replace('USD','USDT')
    name=f'{pair}-1h-{year}-{month:02}.zip'
    url=f'https://data.binance.vision/data/spot/monthly/klines/{pair}/1h/{name}'
    payload=cached(url,CACHE/'binance'/name,checksum=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        rows=list(csv.reader(io.StringIO(archive.read(archive.namelist()[0]).decode())))
    bars=[]
    for row in rows:
        stamp=int(row[0])
        stamp/=1e6 if stamp>10**14 else 1000
        bars.append(Bar(datetime.fromtimestamp(stamp,timezone.utc),*(float(row[k]) for k in (1,2,3,4,5))))
    return bars,dict(url=url,sha256=hashlib.sha256(payload).hexdigest(),bars=len(bars),checksum_verified=True)


def download_crypto(end):
    DATA.mkdir(parents=True,exist_ok=True)
    manifests=[]
    for symbol in CRYPTO:
        tasks=[(symbol,y,m) for y in range(2020,end.year+1) for m in range(1,13)
               if datetime(y,m,1,tzinfo=timezone.utc)<end.replace(day=1,hour=0,minute=0,second=0,microsecond=0)]
        bars,files,errors=[],[],[]
        def fetch(args):
            try:
                return binance_month(*args)
            except Exception as exc:
                return [],dict(period=f'{args[1]}-{args[2]:02}',error=str(exc))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for chunk,meta in pool.map(fetch,tasks):
                bars.extend(chunk)
                (errors if 'error' in meta else files).append(meta)
                if len(files)%12==0:
                    print(symbol,'months',len(files),'errors',len(errors),flush=True)
        # REST supplies current month and any interval after the last complete archive.
        pair=symbol.replace('USD','USDT')
        start=datetime(end.year,end.month,1,tzinfo=timezone.utc)
        while start<end:
            url=f'https://api.binance.com/api/v3/klines?symbol={pair}&interval=1h&startTime={int(start.timestamp()*1000)}&endTime={int(end.timestamp()*1000)-1}&limit=1000'
            try:
                rows=json.loads(request(url))
                if not rows:
                    break
                raw=json.dumps(rows).encode()
                file=CACHE/'binance'/f'{pair}-REST-{start:%Y%m%d%H}.json'
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes(raw)
                files.append(dict(url=url,sha256=hashlib.sha256(raw).hexdigest(),bars=len(rows),checksum_verified=False))
                for row in rows:
                    stamp=datetime.fromtimestamp(int(row[0])/1000,timezone.utc)
                    if stamp+timedelta(hours=1)<=end:
                        bars.append(Bar(stamp,*(float(row[k]) for k in (1,2,3,4,5))))
                start=datetime.fromtimestamp(int(rows[-1][0])/1000,timezone.utc)+timedelta(hours=1)
            except Exception as exc:
                errors.append(dict(period='current_month',error=str(exc)))
                break
        by_time={b.time:b for b in bars if b.time+timedelta(hours=1)<=end}
        bars=[by_time[k] for k in sorted(by_time)]
        save_csv(DATA/f'{symbol}.csv',bars,symbol)
        manifest=dict(instrument=symbol,source='Binance spot USDT klines',quote_proxy='USDT treated as USD; depegs not adjusted',
                      price_basis='last_traded_price (not executable bid/ask)',
                      shorting='Synthetic symmetric short simulation; spot archive does not establish short availability',
                      fetched_at=datetime.now(timezone.utc).isoformat(),quality=quality(bars,continuous=True),files=files,errors=errors)
        (DATA/f'{symbol}.manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        manifests.append(manifest)
        print(symbol,'DONE',len(bars),'errors',len(errors),flush=True)
    return manifests


def inspect_histdata():
    for symbol,year in [('eurusd',2020),('eurusd',2026),('xauusd',2020)]:
        url=f'https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{symbol}/{year}'
        html=request(url).decode('utf-8',errors='replace')
        path=ROOT/'data'/f'histdata_{symbol}_{year}.html'
        path.parent.mkdir(exist_ok=True)
        path.write_text(html,encoding='utf-8')
        print(url,'bytes',len(html),flush=True)
        print('\n'.join(line[:1500] for line in html.splitlines() if any(k in line for k in ('name="tk"','name="date"','name="datemonth"','get.php','HISTDATA','name="fxpair"','name="timeframe"'))),flush=True)


def histdata_period(symbol,year,month=None):
    suffix=f'/{month}' if month else ''
    url=f'https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{symbol.lower()}/{year}{suffix}'
    name=f'{symbol}-{year}'+(f'-{month:02}' if month else '')+'.zip'
    target=CACHE/'histdata'/name
    if target.exists():
        payload=target.read_bytes()
    else:
        html=request(url).decode('utf-8',errors='replace')
        fields=dict(re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"',html))
        if not fields.get('tk'):
            raise ValueError('No downloadable archive/token published for period')
        fields={k:fields[k] for k in ('tk','date','datemonth','platform','timeframe','fxpair')}
        payload=request('https://www.histdata.com/get.php',data=urllib.parse.urlencode(fields).encode(),referer=url,timeout=90)
        if not payload.startswith(b'PK'):
            raise ValueError(f'Expected ZIP, received {payload[:100]!r}')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(payload)
    hours={}
    duplicates=out_of_order=bad_ohlc=missing_minutes=0
    seen=set()
    excluded_hours=set()
    previous=None
    minute_counts={}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        files=[n for n in archive.namelist() if n.lower().endswith('.csv')]
        for filename in files:
            with archive.open(filename) as raw:
                for row in csv.reader(io.TextIOWrapper(raw,encoding='utf-8-sig'),delimiter=';'):
                    # Source is fixed EST (UTC-5) without daylight saving adjustments.
                    t=row[0]
                    naive=datetime(int(t[:4]),int(t[4:6]),int(t[6:8]),int(t[9:11]),int(t[11:13]),int(t[13:15]))
                    stamp=naive.replace(tzinfo=timezone(timedelta(hours=-5))).astimezone(timezone.utc)
                    o,h,l,c=map(float,row[1:5])
                    if not 0<l<=min(o,c)<=max(o,c)<=h:
                        bad_ohlc+=1
                        continue
                    key=stamp.replace(minute=0,second=0)
                    if stamp in seen:
                        duplicates+=1
                        excluded_hours.add(key)
                    seen.add(stamp)
                    if previous is not None:
                        if stamp<previous:
                            out_of_order+=1
                        missing_minutes+=max(0,int((stamp-previous).total_seconds()/60)-1)
                    previous=stamp
                    if key in excluded_hours:
                        continue
                    minute_counts[key]=minute_counts.get(key,0)+1
                    if key not in hours:
                        hours[key]=[o,h,l,c,float(row[5]) if len(row)>5 else 0,stamp,stamp]
                    else:
                        x=hours[key]
                        x[1]=max(x[1],h)
                        x[2]=min(x[2],l)
                        if stamp<x[5]:
                            x[0],x[5]=o,stamp
                        if stamp>x[6]:
                            x[3],x[6]=c,stamp
                        x[4]+=float(row[5]) if len(row)>5 else 0
    if bad_ohlc:
        raise ValueError(f'Source M1 validation failed: bad OHLC={bad_ohlc}')
    bars=[Bar(t,*hours[t][:5]) for t in sorted(hours) if t not in excluded_hours]
    return bars,dict(url=url,sha256=hashlib.sha256(payload).hexdigest(),bars=len(bars),
                     partial_hours=sum(n<60 for n in minute_counts.values()),
                     absent_minute_intervals=missing_minutes,source_timezone='Fixed EST UTC-5, no DST',
                     original_out_of_order_rows=out_of_order,duplicate_minutes=duplicates,
                     excluded_ambiguous_hours=[t.isoformat() for t in sorted(excluded_hours)],
                     normalization='Sort hours; drop entire hours with any duplicate minute timestamp. Never choose between conflicting duplicate prices.')


def download_histdata(end,symbols=None,smoke=False):
    DATA.mkdir(parents=True,exist_ok=True)
    symbols=symbols or FOREX+['XAUUSD','XAGUSD','WTIUSD','BCOUSD']
    for symbol in symbols:
        tasks=[(symbol,y,None) for y in range(2020,end.year)]
        tasks += [(symbol,end.year,m) for m in range(1,end.month+1)]
        if smoke:
            tasks=tasks[:1]
        bars,files,errors=[],[],[]
        def fetch(args):
            try:
                return histdata_period(*args)
            except Exception as exc:
                return [],dict(year=args[1],month=args[2],error=str(exc))
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            for chunk,meta in pool.map(fetch,tasks):
                bars.extend(chunk)
                (errors if 'error' in meta else files).append(meta)
                print(symbol,'periods',len(files),'errors',len(errors),flush=True)
        by_time={b.time:b for b in bars if datetime(2020,1,1,tzinfo=timezone.utc)<=b.time and b.time+timedelta(hours=1)<=end}
        bars=[by_time[t] for t in sorted(by_time)]
        save_csv(DATA/f'{symbol}.csv',bars,symbol)
        manifest=dict(instrument=symbol,source='HistData Generic ASCII M1 aggregated to UTC H1',
                      price_basis='bid',fetched_at=datetime.now(timezone.utc).isoformat(),
                      quality=quality(bars),files=files,errors=errors,
                      note='Partial hours retained and counted; absence of M1 bars can be no ticks, market closures or missing data.')
        (DATA/f'{symbol}.manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        print(symbol,'DONE',len(bars),'errors',len(errors),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',choices=['crypto','inspect-histdata','histdata','smoke-histdata','duka-check'])
    parser.add_argument('--end',default='2026-11-17T00:00:00+00:00')
    parser.add_argument('--symbols',nargs='+')
    args=parser.parse_args()
    if args.source=='duka-check':
        url='https://datafeed.dukascopy.com/datafeed/GASCMDUSD/2020/00/BID_candles_hour_1.bi5'
        try:
            payload=request(url)
            path=CACHE/'dukascopy'/'GASCMDUSD-2020-01.bi5'
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(payload)
            print('Natural gas probe downloaded',len(payload),'bytes',flush=True)
        except urllib.error.HTTPError as exc:
            print('Dukascopy status',exc.code,'Retry-After:',exc.headers.get('Retry-After'),'body:',exc.read(350).decode(errors='replace'),flush=True)
    elif args.source=='crypto':
        download_crypto(datetime.fromisoformat(args.end))
    elif args.source=='inspect-histdata':
        inspect_histdata()
    else:
        download_histdata(datetime.fromisoformat(args.end),args.symbols,smoke=args.source=='smoke-histdata')

if __name__=='__main__':
    main()
