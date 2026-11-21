import csv,hashlib,io,json,zipfile
from datetime import datetime,timezone
from sme.m15_history import DATA
from sme.download import cached,CACHE
from sme.data import load_csv,save_csv,quality
from sme.model import Bar
from sme import study2010 as study

for symbol in ['BTCUSD','ETHUSD','BNBUSD']:
    path=DATA/f'{symbol}.manifest.json'
    if not path.exists():continue
    meta=json.loads(path.read_text());errors=meta.get('errors',[])
    for error in list(errors):
        period=error.get('period')
        if not period:continue
        pair=symbol.replace('USD','USDT');name=f'{pair}-15m-{period}.zip'
        url=f'https://data.binance.vision/data/spot/{"daily" if len(period)>7 else "monthly"}/klines/{pair}/15m/{name}'
        payload=cached(url,CACHE/'binance-m15'/name,checksum=True);rows=[]
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for row in csv.reader(io.StringIO(archive.read(archive.namelist()[0]).decode())):
                n=int(row[0]);stamp=datetime.fromtimestamp(n/(1e6 if n>10**14 else 1000),timezone.utc)
                if stamp.timestamp()%900:raise ValueError('Misaligned repair archive')
                rows.append(Bar(stamp,*(float(row[k]) for k in (1,2,3,4,5))))
        merged={b.time:b for b in load_csv(DATA/f'{symbol}.csv')}
        for b in rows:
            if b.time in merged and merged[b.time]!=b:raise ValueError('Conflicting repair price')
            if b.time<study.END:merged[b.time]=b
        values=[b for _,b in sorted(merged.items())];q=quality(values,'M15')
        if not q['valid']:raise ValueError(q['errors'])
        save_csv(DATA/f'{symbol}.csv',values,symbol,'M15');errors.remove(error)
        meta['files'].append(dict(url=url,sha256=hashlib.sha256(payload).hexdigest(),repaired_transient_download=True));meta['quality']=q
        study.write_json(path,meta);print(symbol,period,'REPAIRED',len(rows),flush=True)
