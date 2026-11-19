"""Rebuild genuinely UTC-aligned H1 candles from archived aggregate trades."""
import csv
import hashlib
import io
import math
import zipfile
from datetime import datetime,timezone
from .model import Bar
from .download import cached,CACHE


def aggregate_trade_rows(rows,day):
    hours={};count=0;previous=None
    for row in rows:
        if not row or not row[0].isdigit():
            if count==0:
                continue
            raise ValueError('Unexpected non-trade row')
        price,quantity=float(row[1]),float(row[2])
        stamp=int(row[5])
        if stamp>10**14:
            stamp//=1000
        if previous is not None and stamp<previous:
            raise ValueError('Aggregate-trade timestamps out of order')
        previous=stamp
        if not all(math.isfinite(v) and v>0 for v in (price,quantity)):
            raise ValueError('Invalid aggregate-trade price or quantity')
        if datetime.fromtimestamp(stamp/1000,timezone.utc).date().isoformat()!=day:
            raise ValueError('Trade timestamp outside its source UTC day')
        key=stamp//3600000*3600
        if key not in hours:
            hours[key]=[price,price,price,price,quantity]
        else:
            h=hours[key]
            h[1]=max(h[1],price);h[2]=min(h[2],price);h[3]=price;h[4]+=quantity
        count+=1
    if not count:
        raise ValueError('Empty aggregate-trade source')
    return [Bar(datetime.fromtimestamp(t,timezone.utc),*hours[t]) for t in sorted(hours)],count


def day_from_trades(symbol,day):
    pair=symbol.replace('USD','USDT')
    name=f'{pair}-aggTrades-{day}.zip'
    url=f'https://data.binance.vision/data/spot/daily/aggTrades/{pair}/{name}'
    payload=cached(url,CACHE/'binance'/name,checksum=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_name=next(n for n in archive.namelist() if n.lower().endswith('.csv'))
        with archive.open(csv_name) as raw:
            bars,count=aggregate_trade_rows(csv.reader(io.TextIOWrapper(raw,encoding='utf-8-sig')),day)
    return bars,dict(url=url,sha256=hashlib.sha256(payload).hexdigest(),checksum_verified=True,
                     source='Binance aggregate trades regrouped into UTC H1',day=day,trades=count,bars=len(bars))


def repair_misaligned(symbol,bars,fetch_day=day_from_trades):
    bad=[b for b in bars if b.time.timestamp()%3600]
    if not bad:
        return bars,[]
    days=sorted({b.time.date().isoformat() for b in bad})
    rebuilt=[];provenance=[]
    for day in days:
        chunk,meta=fetch_day(symbol,day)
        rebuilt.extend(chunk)
        provenance.append({**meta,'replaced_misaligned_candles':sum(b.time.date().isoformat()==day for b in bad),
                           'policy':'Replace entire affected UTC day with OHLC from actual archived trades; never floor old candle timestamps.'})
    keep=[b for b in bars if b.time.date().isoformat() not in days]
    return sorted(keep+rebuilt,key=lambda b:b.time),provenance
