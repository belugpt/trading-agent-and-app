import csv
import math
from datetime import datetime, timedelta, timezone
from .model import Bar

TIMEFRAMES = {'M15': 900, 'H1': 3600, 'H4': 14400}


class ValidatedSeries(tuple):
    """Immutable bars with a reusable quality report for parameter comparisons."""
    def __new__(cls,bars,timeframe='H1'):
        obj=super().__new__(cls,bars)
        obj.timeframe=timeframe
        obj.quality=quality(obj,timeframe)
        if not obj.quality['valid']:
            raise ValueError('; '.join(obj.quality['errors'][:8]))
        return obj


def load_csv(path):
    bars = []
    instruments, timeframes = set(), set()
    with open(path, newline='', encoding='utf-8-sig') as handle:
        for line, row in enumerate(csv.DictReader(handle), 2):
            try:
                stamp = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                if stamp.tzinfo is not None:
                    stamp = stamp.astimezone(timezone.utc)
                bars.append(Bar(stamp, *(float(row[k]) for k in ('open','high','low','close')), float(row.get('volume') or 0)))
                if row.get('instrument'):
                    instruments.add(row['instrument'])
                if row.get('timeframe'):
                    timeframes.add(row['timeframe'])
            except (ValueError, KeyError) as exc:
                raise ValueError(f'CSV row {line}: {exc}') from exc
    if len(instruments) > 1 or len(timeframes) > 1:
        raise ValueError('Import one instrument and timeframe per CSV')
    return bars


def quality(bars, timeframe='H1', continuous=False):
    errors, gaps, seen = [], [], set()
    step = TIMEFRAMES[timeframe]
    previous = None
    for i, b in enumerate(bars):
        if b.time.tzinfo is None or b.time.utcoffset() is None:
            errors.append(f'Row {i}: timestamp must have explicit timezone')
            continue
        if b.time in seen:
            errors.append(f'Row {i}: duplicate timestamp')
        seen.add(b.time)
        values = (b.open,b.high,b.low,b.close,b.volume)
        if not all(math.isfinite(x) for x in values) or not (0 < b.low <= min(b.open,b.close) <= max(b.open,b.close) <= b.high) or b.volume < 0:
            errors.append(f'Row {i}: invalid OHLC or volume')
        if b.time.timestamp() % step:
            errors.append(f'Row {i}: candle not aligned to UTC timeframe')
        if previous is not None:
            seconds = (b.time-previous).total_seconds()
            if seconds <= 0:
                errors.append(f'Row {i}: incorrect chronological ordering')
            elif seconds > step:
                # Report all gaps; weekend/holiday closures are not asserted missing data.
                gaps.append(dict(after=previous.isoformat(), before=b.time.isoformat(),
                                 absent_intervals=int(seconds//step)-1,
                                 classification='unexplained_or_market_closure' if not continuous else 'missing_intervals'))
        previous = b.time
    if not bars:
        errors.append('Empty dataset')
    return dict(valid=not errors, bars=len(bars), errors=errors, gaps=gaps,
                gap_count=len(gaps), absent_intervals=sum(g['absent_intervals'] for g in gaps),
                start=bars[0].time.isoformat() if bars else None,
                end=bars[-1].time.isoformat() if bars else None,
                timezone='UTC normalized; explicit offsets required',
                note='All gaps reported. Market sessions and holidays require provider calendar verification.')


def save_csv(path, bars, instrument, timeframe='H1'):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['timestamp','open','high','low','close','volume','instrument','timeframe'])
        for b in bars:
            writer.writerow([b.time.isoformat(),b.open,b.high,b.low,b.close,b.volume,instrument,timeframe])
