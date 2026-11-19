from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import math


@dataclass(frozen=True)
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def json(self):
        return dict(time=self.time.isoformat(), open=self.open, high=self.high,
                    low=self.low, close=self.close, volume=self.volume)


@dataclass
class Config:
    name: str = 'SME baseline 126 SMA / 252 SMA (open)'
    fast_type: str = 'SMA'
    slow_type: str = 'SMA'
    fast_period: int = 126
    slow_period: int = 252
    ma_source: str = 'open'
    lookback: int = 50
    retracement_mode: str = 'percent'
    retracement: float = 0.1
    origin_method: str = 'retracement_extreme'
    initial_balance: float = 10000.0
    sizing: str = 'risk_percent'
    risk_percent: float = 1.0
    fixed_units: float = 10000.0
    fixed_lots: float = 0.1
    contract_size: float = 100000.0
    pip_size: float = 0.0001
    spread: float = 0.0
    slippage: float = 0.0
    commission_per_million: float = 35.0
    penetration: float = 0.0
    stop_buffer: float = 0.0
    expiry_bars: int = 0
    ambiguity: str = 'stop_first'
    max_leverage: float = 30.0
    account_currency: str = 'USD'
    entry_fraction: float = 0.5
    extension: float = 2.0

    def validate(self):
        if self.fast_type not in ('SMA', 'EMA') or self.slow_type not in ('SMA', 'EMA'):
            raise ValueError('MA types must be SMA or EMA')
        if self.ma_source not in ('open','close'):
            raise ValueError('MA source must be open or close')
        if any(not isinstance(x, int) or x < 1 for x in (self.fast_period, self.slow_period, self.lookback)):
            raise ValueError('Periods and lookback must be positive integers')
        if self.fast_period >= self.slow_period:
            raise ValueError('Fast period must be shorter than slow period')
        if self.retracement_mode not in ('percent', 'price') or self.retracement <= 0:
            raise ValueError('Positive retracement threshold required: percent of extreme price, or price distance')
        if self.origin_method not in ('retracement_extreme', 'latest_confirmed_pivot'):
            raise ValueError('Unsupported origin method')
        if self.sizing not in ('risk_percent', 'fixed_units', 'fixed_lots') or self.ambiguity not in ('stop_first', 'skip_entry'):
            raise ValueError('Unsupported sizing or ambiguity policy')
        for key, value in asdict(self).items():
            if isinstance(value, (int, float)) and (not math.isfinite(value) or value < 0):
                raise ValueError(f'Invalid numeric setting: {key}')
        if self.initial_balance <= 0 or self.max_leverage <= 0 or not 0 < self.risk_percent <= 100:
            raise ValueError('Balance, leverage and risk must be positive; risk <= 100%')
        if min(self.fixed_units,self.fixed_lots,self.contract_size,self.pip_size) <= 0 or self.entry_fraction != 0.5 or self.extension != 2:
            raise ValueError('SME requires 0.5 entry and 200% extension; fixed units must be positive')
        if self.account_currency != 'USD':
            raise ValueError('This release explicitly supports USD accounts only')


def moving_average(values, period, kind):
    result = [None] * len(values)
    total = 0.0
    previous = None
    for i, value in enumerate(values):
        total += value
        if i >= period:
            total -= values[i-period]
        if i >= period-1:
            previous = total / period if kind == 'SMA' or previous is None else previous + 2/(period+1)*(value-previous)
            result[i] = previous
    return result


def fibonacci(origin, endpoint, direction):
    span = direction * (endpoint-origin)
    if span <= 0:
        raise ValueError('Swing must have positive directional range')
    return dict(origin=origin, endpoint=endpoint, range=span,
                entry=(origin+endpoint)/2, target=endpoint+direction*2*span,
                entry_label='0.5', target_label='-2.0')


def crossover(previous_fast, previous_slow, fast, slow):
    if None in (previous_fast, previous_slow, fast, slow):
        return 0
    if previous_fast < previous_slow and fast > slow:
        return 1
    if previous_fast > previous_slow and fast < slow:
        return -1
    return 0
