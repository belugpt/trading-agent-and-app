"""Loopback-only research UI. Python standard library; no broker, telemetry or external CDN."""
import argparse
import json
import mimetypes
import urllib.parse
from dataclasses import asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .model import Config
from .data import load_csv, quality, save_csv
from .engine import Engine
from .research import ROOT,DATA,OUT,baseline,currency_converter,dump,export_csv

WEB=ROOT/'web'


def resample_h4(bars):
    from .model import Bar
    groups={}
    for b in bars:
        key=b.time.replace(hour=b.time.hour//4*4)
        groups.setdefault(key,[]).append(b)
    return [Bar(t,bs[0].open,max(b.high for b in bs),min(b.low for b in bs),bs[-1].close,sum(b.volume for b in bs))
            for t,bs in groups.items() if len(bs)==4]


class Handler(BaseHTTPRequestHandler):
    def send(self,value,status=200,mime='application/json'):
        data=json.dumps(value,allow_nan=False).encode() if mime=='application/json' else value
        self.send_response(status)
        self.send_header('Content-Type',mime+'; charset=utf-8' if mime.startswith(('text/','application/json')) else mime)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            parsed=urllib.parse.urlparse(self.path)
            query=urllib.parse.parse_qs(parsed.query)
            if parsed.path=='/api/catalog':
                files=[p.stem for p in sorted(DATA.glob('*.csv')) if p.stat().st_size>100]
                summary=json.loads((OUT/'summary.json').read_text(encoding='utf-8')) if (OUT/'summary.json').exists() else dict(results=[],failures=[])
                return self.send(dict(instruments=files,summary=summary,defaults=asdict(Config())))
            if parsed.path in ('/api/result','/api/bars'):
                symbol=query.get('symbol',[''])[0]
                if symbol not in [p.stem for p in DATA.glob('*.csv')]:
                    return self.send({'error':'Unknown instrument'},404)
                if parsed.path=='/api/bars':
                    return self.send([b.json() for b in load_csv(DATA/f'{symbol}.csv')])
                path=OUT/'runs'/symbol/'result.json'
                if not path.exists():
                    return self.send({'error':'Run the instrument first'},404)
                return self.send(path.read_bytes(),mime='text/json')
            if parsed.path.startswith('/export/'):
                relative=urllib.parse.unquote(parsed.path[len('/export/'):])
                path=(OUT/relative).resolve()
                if not path.is_relative_to(OUT.resolve()) or not path.is_file():
                    return self.send({'error':'Export not found'},404)
                return self.send(path.read_bytes(),mime=mimetypes.guess_type(path)[0] or 'application/octet-stream')
            if parsed.path in ('/','/app.js','/style.css'):
                path=WEB/('index.html' if parsed.path=='/' else parsed.path[1:])
                return self.send(path.read_bytes(),mime=mimetypes.guess_type(path)[0] or 'text/plain')
            self.send({'error':'Not found'},404)
        except Exception as exc:
            self.send({'error':str(exc)},400)

    def do_POST(self):
        try:
            # Prevent websites from issuing requests to the local research server.
            origin=self.headers.get('Origin')
            if origin and urllib.parse.urlparse(origin).netloc!=self.headers.get('Host'):
                return self.send({'error':'Cross-origin request refused'},403)
            length=int(self.headers.get('Content-Length','0'))
            if length>30_000_000:
                return self.send({'error':'Request too large'},413)
            body=json.loads(self.rfile.read(length))
            symbol=body.get('instrument','').upper()
            if not symbol.isalnum() or not 3<=len(symbol)<=20:
                raise ValueError('Instrument must be a short alphanumeric identifier')
            if self.path=='/api/import':
                path=DATA/f'{symbol}.csv'
                if path.exists():
                    raise ValueError('Use a new instrument identifier; existing source histories cannot be overwritten through import')
                text=body['csv']
                import tempfile
                with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
                    incoming=Path(temporary)/'import.csv'
                    incoming.write_text(text,encoding='utf-8')
                    bars=load_csv(incoming)
                    q=quality(bars,body.get('timeframe','H1'))
                    if not q['valid']:
                        return self.send(q,400)
                    DATA.mkdir(parents=True,exist_ok=True)
                    save_csv(path,bars,symbol,body.get('timeframe','H1'))
                    dump(DATA/f'{symbol}.manifest.json',dict(source='User CSV',instrument=symbol,timeframe=body.get('timeframe','H1'),quality=q))
                return self.send(q)
            if self.path!='/api/backtest':
                return self.send({'error':'Not found'},404)
            config=Config(**body['config'])
            bars=load_csv(DATA/f'{symbol}.csv')
            timeframe=body.get('timeframe','H1')
            manifest_path=DATA/f'{symbol}.manifest.json'
            manifest=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
            source_timeframe=manifest.get('timeframe','H1')
            if timeframe=='H4' and source_timeframe=='H1':
                bars=resample_h4(bars)
            elif timeframe!=source_timeframe:
                raise ValueError(f'Source is {source_timeframe}; finer candles cannot be inferred')
            result=Engine(config,symbol,timeframe,currency_converter(symbol,{})).run(bars)
            result['provenance']=manifest
            folder=OUT/'runs'/symbol
            # Keep baseline exports intact: UI experiments use separate names.
            dump(folder/'experiment.json',result)
            export_csv(folder/'experiment-trades.csv',result['trades'])
            return self.send(dict(result=result,bars=[b.json() for b in bars]))
        except Exception as exc:
            self.send({'error':str(exc)},400)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--port',type=int,default=8765)
    args=p.parse_args()
    print(f'SME research dashboard: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()

if __name__=='__main__':
    main()
