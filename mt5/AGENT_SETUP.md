# Multi-timeframe indicator and EA

## Version 1.30: mandatory confirmed alignment

Compilation update: workspace SMAStrat, SME_Agent and SME_Monitor were compiled in the installed MetaEditor with zero errors and zero warnings. The package includes their .ex5 binaries and COMPILATION.json hashes. This does not verify chart behavior, broker constraints or demo execution; nothing was installed into the terminal or activated. Binary copies go in their corresponding Indicators/Experts folders; SME_Alignment.mqh goes in Include if rebuilding source.

Install SME_Alignment.mqh in MQL5/Include, then recompile BOTH SMAStrat and SME_Agent. No pending limit is permitted unless the latest CLOSED trading-timeframe and higher-timeframe candles both have 126 SMA above 252 SMA for buys, or below for sells. H1 checks H4; H4 checks D1; M15/M5/M30 check H1. Higher chart periods map to daily/weekly/monthly. Missing history or equal SMAs blocks the order. This is MA ordering, not an additional slope test. The forming higher candle cannot confirm alignment. Existing owned pending limits are cancelled on loss of confirmed alignment while execution is enabled and the terminal is running. Broker fills may occur before a client-side cancellation reaches the server. Stops and targets on existing positions are not changed. This may filter conflicting setups; it cannot guarantee protection from spikes or losses. Historical dashboard reports predate this filter and do not validate it. MetaEditor compilation is verified as described above; terminal/broker execution remains unverified.

## Version 1.20: revised swing stop

The current stop rule supersedes crossover-stop references below. Buy stops are below point 4 (the deepest pre-breakout retracement low forming the origin of the swing that breaks the prior high). Sell stops are above that swing's origin high. The origin freezes on the first wick breakout; later continuation or retracement does not move it. StopBufferTicks defaults to one broker tick and must be at least one. The EA reads the revised stop buffer and calculates lots using its actual distance. Recompile BOTH indicator and EA. Existing pending orders/positions are not modified by this update; the new rule applies to new setups. Previous Python backtests used crossover stops and do not establish performance for this revision.

1. Put SMAStrat.mq5 in MQL5/Indicators and compile it first with F7.
2. Put SME_Agent.mq5 in MQL5/Experts and compile it with F7.
3. Attach the EA to the desired symbol and timeframe, M5 or higher. Each chart monitors its own symbol/timeframe. Load enough history for the slow SMA plus setup formation. Use a different MagicNumber for each independently managed chart on the same symbol.
4. ExecuteTrades=false gives setup notifications and calculated sizing without placing or cancelling orders. PushNotifications=false by default; enable it after configuring Tools → Options → Notifications and your MetaQuotes ID. PopupAlerts defaults on.
5. For execution, enable ExecuteTrades and MT5 Algo Trading. Test on a demo account first. The EA places midpoint limit orders with server-side crossover stops and −200 targets. It does not chase a passed midpoint with a market order. Existing positions on the symbol or this EA's pending orders block another entry.

Defaults remain SMA 126/252 OPEN, structure lookback 50 and 0.1% retracement. These periods mean chart bars: on M5 they represent a much shorter time horizon than H1. M5/higher-timeframe support is not evidence of backtested profitability on those timeframes. Original research was H1.

Sizing uses account equity × RiskPercent (default 1%), OrderCalcProfit in account currency, a configurable 10% cost reserve, and rounds volume down to broker steps. Below-minimum sizes are skipped rather than rounded up. The reserve is an estimate, not a guaranteed maximum loss; gaps, slippage and commissions can exceed it. Broker price ticks, minimum order distances and free margin are checked. Rejected requests are reported without automatic retries. Fill and closing-deal notifications include actual execution prices.

Opposite current-open SMA direction cancels this EA's opposite pending limits when execution is enabled. This is client-side cancellation: the terminal must be running, and an order may fill before a cancellation reaches the broker. Stops/targets are submitted with the pending order. No trailing stop is used. Attaching/restarting skips the currently forming candle's existing setup to avoid submitting stale signals; pending orders are GTC. Turning execution off also stops EA-managed cancellation.

The EA reads indicator buffers 2–5: direction, midpoint, stop and target at the first candle after confirmation. Buffers 0–1 contain the SMA values. It uses the same input periods/lookback/retracement as the indicator. Do not enable indicator alerts too unless duplicate alerts are desired.

Status: source implemented and reviewed; MetaEditor compilation is verified; Strategy Tester execution, broker constraints and demo end-to-end behavior remain unverified. No live order has been placed. Use MT5 Strategy Tester with real ticks for meaningful execution verification.
