# SME Original MT5 indicator

Version 1.20 update: M5 and higher timeframes are supported. Stop rule is now swing-origin stop, superseding crossover-stop descriptions below: below point 4 for buys, above it for sells, buffered by StopBufferTicks (default one broker tick). The origin freezes before the breakout candle. Point 1 marks only the crossover candle; point 9 marks the revised stop. Previous research results used the earlier crossover stop.

Copy `SME_Original.mq5` into MT5: File → Open Data Folder → MQL5 → Indicators. Open it in MetaEditor, compile with F7, then attach it to an H1 chart. Load sufficient historical candles (at least 254; substantially more for setup history).

Defaults: 126/252 SMA on OPEN, prior structure lookback 50, 0.1% retracement, deepest pre-breakout retracement origin, wick breakout, continuing impulse endpoint frozen on retracement, midpoint limit, crossover-candle stop, −200 target. No trailing stop or optimized entry filters. Settings expose MA periods, lookback and retracement percentage. Use distinct ObjectTag values for multiple instances.

Gray arrows mark historical crossovers. Colored arrows mark confirmed setup availability. Blue/red/green dashed lines indicate entry/stop/target; hover for prices. Lines remain historical annotations after cancellation/touch and extend a fixed number of bars, not the order lifetime. Alerts are optional, default off, and fire on new confirmed setups, not when the indicator is first attached.

Structure uses completed candles only; current open-price crossover cancellation is reported immediately. Signals rebuild when history changes, so different broker candles can change results. The midpoint touch is an OHLC visual indication, not a spread-aware execution simulation. The indicator neither places orders nor calculates backtest returns or validates actual stop/target fills. MT5 prices and server timestamps can differ from the research data.

Validation: source reviewed against the Python original state machine. MetaEditor compilation and terminal chart inspection have not been performed in this environment; compile and check in MT5 before relying on alerts. Historical lines intentionally remain visible after a setup ceases to be pending.
