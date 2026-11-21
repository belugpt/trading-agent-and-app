# Multi-timeframe strategy and trade-management research

{
  "version": "confirmed-alignment-1",
  "timeframes": [
    "M15",
    "H1",
    "H4"
  ],
  "exits": [
    "original",
    "minus100",
    "twoR",
    "runner2R",
    "atr3",
    "partial1R_runner2R"
  ],
  "filters": [
    "higher",
    "higher_trend",
    "higher_liquid",
    "higher_low_cost",
    "higher_minimum_stop"
  ],
  "mandatory": "Swing-origin stop; SMA126/252 OPEN; midpoint limit; latest CLOSED higher SMA and closed lower SMA must agree before order creation and before fill.",
  "higher": {
    "M15": "H1",
    "H1": "H4",
    "H4": "UTC D1"
  },
  "training": "Six prior calendar years, minimum four actual years, 24h embargo; next two years frozen test; final 2026 partial",
  "shortlist": 2,
  "min_training_trades": 25,
  "objective": "Actual training CAGR / max(1%, MTM drawdown); positive return, mean R, PF>=1.05, two profitable years, no winner over 50% gross gains.",
  "partial": "Half at +1 initial R after fill bar, remaining runner with 2R trail; conservative stop-first before partial credit.",
  "caveat": "Retrospective research: prior history has already been inspected. Native M15 or real M1 aggregation only; not FBS costs/ticks or server candles. No averaging down or discretionary extra entries. At most one entry per setup; concurrent distinct setups remain possible under original engine leverage rules."
}

## Findings

29 markets; 0 pass the prespecified retrospective screen. No settings have been automatically applied to live execution.

H1 comparator and selected policies reset flat at identical forward boundaries. Rules are selected using earlier closed trades only with a 24-hour embargo. Minimum 25 training trades, positive training return/mean R, PF >=1.05, two profitable years and capped winner concentration are required. Top two proxy candidates are replayed with actual sizing. If none passes, the next window stays in cash. Timeframe, exit and filter are frozen before testing. Double-cost stress keeps parameters fixed, but cost-sensitive eligibility can change. All candidates require closed lower/higher SMA agreement at formation and again before fill.

| Market | Latest tested timeframe | Exit | Filter | Windows | Cash | H1 reference % | Selected % | H1 DD % | Selected DD % | Trades | Double cost % | Screen |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| EURUSD | M15 | atr3 | higher_liquid | 6 | 2 | 8.26 | 4.50 | 16.38 | 11.19 | 70 | -2.67 | False |
| GBPUSD | H1 | minus100 | higher | 6 | 4 | -4.95 | -12.25 | 14.54 | 14.54 | 13 | -12.25 | False |
| AUDUSD | H1 | original | cash | 6 | 5 | -14.80 | -8.84 | 23.03 | 14.80 | 15 | -8.89 | False |
| NZDUSD | M15 | partial1R_runner2R | higher_low_cost | 6 | 2 | -11.21 | -13.78 | 14.04 | 20.33 | 54 | -18.62 | False |
| USDJPY | M15 | atr3 | higher | 6 | 2 | -20.93 | -1.06 | 27.00 | 8.25 | 45 | 0.42 | False |
| USDCHF | H1 | twoR | higher | 6 | 0 | 9.59 | 0.71 | 12.42 | 20.64 | 87 | -4.64 | False |
| USDCAD | M15 | twoR | higher_trend | 6 | 3 | -26.69 | -8.15 | 27.86 | 17.06 | 58 | -9.97 | False |
| EURGBP | H1 | original | cash | 6 | 3 | -21.80 | -19.84 | 24.37 | 29.01 | 89 | -30.64 | False |
| EURJPY | M15 | atr3 | higher_low_cost | 6 | 0 | -14.14 | -18.48 | 23.88 | 30.09 | 116 | -16.61 | False |
| EURCHF | H1 | original | cash | 6 | 3 | -24.86 | -23.49 | 25.12 | 24.45 | 56 | -26.44 | False |
| EURAUD | M15 | atr3 | higher_low_cost | 6 | 2 | -1.11 | -10.55 | 10.93 | 17.22 | 34 | -10.59 | False |
| EURCAD | M15 | twoR | higher_minimum_stop | 6 | 1 | -4.68 | -8.87 | 15.04 | 17.56 | 92 | -7.57 | False |
| EURNZD | M15 | runner2R | higher_low_cost | 6 | 2 | -7.45 | -17.95 | 17.52 | 30.26 | 90 | -17.44 | False |
| GBPJPY | H1 | original | cash | 6 | 3 | -1.21 | -5.07 | 12.40 | 15.91 | 46 | -7.93 | False |
| GBPCHF | H1 | original | cash | 6 | 2 | -26.08 | -28.13 | 27.51 | 30.67 | 78 | -29.12 | False |
| GBPAUD | H1 | original | cash | 6 | 2 | 10.45 | -25.89 | 16.68 | 28.47 | 77 | -37.15 | False |
| GBPCAD | H1 | original | higher | 6 | 2 | 33.63 | 8.53 | 10.55 | 10.55 | 32 | 6.91 | False |
| GBPNZD | M15 | original | higher_low_cost | 6 | 0 | 0.90 | -26.46 | 14.25 | 33.17 | 125 | -27.14 | False |
| AUDJPY | H1 | original | higher_minimum_stop | 4 | 1 | 26.95 | 3.71 | 11.07 | 9.56 | 25 | 3.11 | False |
| CADJPY | H1 | minus100 | higher_minimum_stop | 6 | 0 | 24.59 | 4.55 | 10.15 | 16.75 | 125 | -9.81 | False |
| NZDJPY | H1 | original | cash | 6 | 3 | -9.90 | -14.44 | 16.11 | 16.11 | 38 | -15.12 | False |
| CHFJPY | M15 | original | higher_low_cost | 6 | 4 | -28.70 | -10.73 | 28.70 | 19.43 | 34 | -7.25 | False |
| XAUUSD | H1 | minus100 | higher | 6 | 3 | 31.62 | 9.12 | 9.13 | 5.49 | 22 | 8.52 | False |
| XAGUSD | H1 | original | cash | 6 | 5 | -14.76 | 4.37 | 19.91 | 4.31 | 7 | 3.27 | False |
| WTIUSD | none | none | cash | 0 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 0.00 | False |
| BCOUSD | H1 | original | cash | 6 | 2 | -7.92 | -9.78 | 20.63 | 11.77 | 46 | -9.20 | False |
| BTCUSD | H1 | atr3 | higher_trend | 3 | 0 | -0.50 | 3.21 | 10.17 | 9.80 | 28 | 0.12 | False |
| ETHUSD | H1 | original | higher | 3 | 0 | 2.03 | -6.94 | 7.83 | 13.06 | 28 | -9.34 | False |
| BNBUSD | M15 | original | higher_liquid | 3 | 0 | -12.24 | 0.33 | 18.59 | 13.41 | 35 | -4.00 | False |

## What happened after entry

These are descriptive outcomes of the aligned original −200 baseline, not future-known predictors. MFE/MAE use only fully observed bars strictly between fill and exit; ambiguous fill/exit-bar extrema are excluded. Therefore reach frequencies are conservative lower bounds, not exact target probabilities. Trades spanning major data gaps or numerical near-zero risk are excluded. R divides movement by initial price risk. Post-stop rebound examines the next 20 bars after exit; it is counterfactual description, not proof that a wider stop or re-entry is profitable. Means alone are inadequate: report medians, quartiles and sample counts by timeframe, formation session and trend environment.

| Group | N | Win % | Mean R | Median MFE R | P75 MFE R | Median MAE R | Confirmed +1R % | Stopped after +1R % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M15 / all | 7901 | 15.67 | -0.13 | 0.84 | 2.62 | 0.81 | 46.10 | 30.50 |
| M15 / session / London | 2013 | 15.30 | -0.15 | 0.75 | 2.47 | 0.79 | 43.77 | 28.56 |
| M15 / session / NewYork | 1936 | 15.86 | -0.11 | 0.93 | 2.71 | 0.82 | 48.24 | 32.44 |
| M15 / session / Other | 765 | 16.73 | -0.07 | 0.94 | 2.89 | 0.85 | 48.37 | 31.63 |
| M15 / session / Overlap | 1582 | 15.17 | -0.15 | 0.84 | 2.48 | 0.81 | 46.21 | 31.16 |
| M15 / session / Tokyo | 1605 | 15.89 | -0.13 | 0.78 | 2.63 | 0.81 | 45.23 | 29.41 |
| M15 / trend / aligned | 5754 | 15.62 | -0.13 | 0.86 | 2.59 | 0.81 | 46.28 | 30.73 |
| M15 / trend / weak | 2147 | 15.79 | -0.13 | 0.82 | 2.71 | 0.81 | 45.60 | 29.90 |
| H1 / all | 2105 | 15.82 | -0.10 | 0.87 | 2.70 | 0.77 | 46.56 | 30.88 |
| H1 / session / London | 407 | 16.46 | -0.06 | 0.80 | 2.66 | 0.74 | 45.45 | 29.48 |
| H1 / session / NewYork | 639 | 14.87 | -0.16 | 0.90 | 2.68 | 0.81 | 46.79 | 31.92 |
| H1 / session / Other | 284 | 16.55 | -0.05 | 1.00 | 2.95 | 0.79 | 49.65 | 33.10 |
| H1 / session / Overlap | 305 | 14.43 | -0.18 | 0.70 | 2.47 | 0.73 | 43.28 | 29.18 |
| H1 / session / Tokyo | 470 | 17.02 | -0.02 | 0.89 | 2.76 | 0.74 | 47.45 | 30.43 |
| H1 / trend / aligned | 1565 | 15.72 | -0.10 | 0.85 | 2.62 | 0.75 | 45.62 | 30.10 |
| H1 / trend / weak | 540 | 16.11 | -0.08 | 0.94 | 2.85 | 0.80 | 49.26 | 33.15 |
| H4 / all | 555 | 16.58 | -0.04 | 0.92 | 3.02 | 0.75 | 47.21 | 30.63 |
| H4 / session / London | 110 | 12.73 | -0.27 | 0.82 | 2.49 | 0.79 | 40.91 | 28.18 |
| H4 / session / NewYork | 135 | 15.56 | -0.09 | 1.00 | 3.38 | 0.80 | 50.37 | 34.81 |
| H4 / session / Other | 105 | 22.86 | 0.34 | 1.43 | 3.78 | 0.81 | 60.95 | 38.10 |
| H4 / session / Overlap | 46 | 8.70 | -0.54 | 0.53 | 2.27 | 0.61 | 39.13 | 30.43 |
| H4 / session / Tokyo | 159 | 18.24 | 0.05 | 0.66 | 2.71 | 0.65 | 42.14 | 23.90 |
| H4 / trend / aligned | 391 | 16.62 | -0.04 | 0.91 | 2.73 | 0.74 | 46.80 | 30.18 |
| H4 / trend / weak | 164 | 16.46 | -0.04 | 0.94 | 3.48 | 0.77 | 48.17 | 31.71 |

H4 forms far fewer setups. Many six-year H4 training windows fail the minimum-25-trade gate; not selecting H4 is insufficient evidence that it is intrinsically inferior. Do not lower sample requirements simply to manufacture a winning profile.

Taking half off at +1R illustrates the trade-off: if the rest returns to the original −1R stop, gross trade profit is approximately zero before costs; if a fixed 5R target would have won, the half-at-1R/half-at-5R payout falls to 3R. The tested partial runner removes the final fixed target and uses a 2R trail. Its actual forward evidence, not the higher apparent win rate, determines whether it qualifies.

## Data, clocks and execution

M15 comes from genuine HistData M1 aggregation or checksum-verified Binance 15m archives. HistData fixed EST is converted to UTC without invented missing minutes; partial buckets are counted. Legacy misaligned crypto days are rebuilt from aggregate trades. Existing AUDJPY and WTI gaps remain. Source manifests retain hashes and failures. Crypto is a USDT spot proxy with synthetic short/margin assumptions, not an FBS CFD. H4 groups require four H1 bars. Higher confirmation series use nonempty UTC H1/H4/calendar-day groups and become available only at the group close. Daily partial/weekend bars and UTC boundaries can differ from FBS-REAL server candles.

Formation sessions are research windows: London 08–16 local, New York 08–16 local, overlap, Tokyo 09–17 local, or Other. Post-2007 UK/US daylight-saving rules are applied explicitly; no missing timezone package is silently replaced with fixed UTC offsets. These are broad financial-session proxies, including on crypto weekends, not exchange trading calendars. Trend environment uses only known directional fast-MA change over 24 bars and MA separation divided by ATR14; aligned means both >=0.5. Low-cost filter requires estimated costs <=10% of stop distance; minimum-stop filter requires initial stop distance >=ATR14. No news-calendar filter is claimed.

Risk is 1% per entry with original account-currency conversion and leverage approximations. Multiple independent setups may overlap; there is no added averaging down or discretionary pyramiding, but this research is not an account-wide risk-reservation implementation. Partial exits take half at +1R only after the fill candle; stop-first ambiguity precedes partial credit. Runners activate a trail after a fully closed post-entry candle reaches +1R, use only completed bars, and ratchet for the next bar. ATR3 uses a simple mean of 14 true ranges. Limit/stop execution is OHLC-conservative; funding, financing, swaps and commodity roll costs are omitted. FBS contract values and server data still require terminal verification.

Exact forward MTM drawdown is computed from all equity marks; display curves are sampled. Forward returns chain independently restarted test accounts; full-history results are a separate comparison. Unequal valid windows prohibit a fair universal cross-asset yield ranking. Retrospective multiple testing remains even with chronological splits; a passing basic screen is not proof of future edge.

## Per-market frozen decisions

### EURUSD

2016: {"timeframe": "H1", "exit": "atr3", "gate": "higher", "proxy": {"score": 0.16803309789497753, "trades": 28, "mean_r": 0.231487589910431, "r_profit_factor": 1.4114195566224643, "proxy_return_percent": 6.25459593274893, "proxy_drawdown_percent": 6.0479780280034205}}; selected return 0.81%; reference 1.34%; stress -3.18%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -7.22%; stress 0.00%.
2020: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -0.28%; stress 0.00%.
2022: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_trend", "proxy": {"score": 0.1847068468596956, "trades": 67, "mean_r": 0.182329068432942, "r_profit_factor": 1.2961931122829018, "proxy_return_percent": 11.314096219593385, "proxy_drawdown_percent": 9.758602305704866}}; selected return 9.42%; reference 15.05%; stress 7.38%.
2024: {"timeframe": "M15", "exit": "runner2R", "gate": "higher", "proxy": {"score": 0.8147319372144294, "trades": 88, "mean_r": 0.39254600492263775, "r_profit_factor": 1.6885332675946685, "proxy_return_percent": 37.59557982680466, "proxy_drawdown_percent": 6.705459510950707}}; selected return -2.95%; reference -3.30%; stress -4.01%.
2026: {"timeframe": "M15", "exit": "atr3", "gate": "higher_liquid", "proxy": {"score": 0.8294040674107721, "trades": 71, "mean_r": 0.3402594468235436, "r_profit_factor": 1.696036606681433, "proxy_return_percent": 25.864062340462503, "proxy_drawdown_percent": 4.712193258928754}}; selected return -2.38%; reference 3.78%; stress -2.48%.

Mean-R block-bootstrap uncertainty: {"sample_size": 70, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.27910854313266953, 0.4988141617121322], "profit_factor_95ci": [0.588135435763764, 1.822747863760294], "max_drawdown_r_95range": [6.853056866268435, 25.745234805376537], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### GBPUSD

2016: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -1.35%; stress 0.00%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -2.24%; stress 0.00%.
2020: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 2.51%; stress 0.00%.
2022: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 9.57%; stress 0.00%.
2024: {"timeframe": "H1", "exit": "original", "gate": "higher", "proxy": {"score": 0.2680562570318604, "trades": 25, "mean_r": 0.4155417755834213, "r_profit_factor": 1.5346875543652825, "proxy_return_percent": 10.044274533708752, "proxy_drawdown_percent": 5.9987456621597435}}; selected return -9.56%; reference -9.56%; stress -9.56%.
2026: {"timeframe": "H1", "exit": "minus100", "gate": "higher", "proxy": {"score": 0.3969297827308188, "trades": 27, "mean_r": 0.45712712729123656, "r_profit_factor": 1.7090535614996554, "proxy_return_percent": 12.545520447394164, "proxy_drawdown_percent": 5.011771657443664}}; selected return -2.97%; reference -2.97%; stress -2.97%.

Mean-R block-bootstrap uncertainty: {"sample_size": 13, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-1.032583609822672, -1.0217319550978965], "profit_factor_95ci": [0.0, 0.0], "max_drawdown_r_95range": [13.282515416272656, 13.423586927694735], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### AUDUSD

2016: {"timeframe": "H1", "exit": "original", "gate": "higher", "proxy": {"score": 0.017683399808608925, "trades": 27, "mean_r": 0.08065857402676463, "r_profit_factor": 1.0960867231156706, "proxy_return_percent": 1.4735020130033805, "proxy_drawdown_percent": 13.80330281950105}}; selected return -8.84%; reference -8.84%; stress -8.89%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -9.56%; stress 0.00%.
2020: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 5.53%; stress 0.00%.
2022: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 7.45%; stress 0.00%.
2024: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -5.13%; stress 0.00%.
2026: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -3.94%; stress 0.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 15, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-1.0308348663559581, 0.17095353567196928], "profit_factor_95ci": [0.0, 1.2069916083497292], "max_drawdown_r_95range": [5.172893342869015, 15.462522995339372], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### NZDUSD

2016: {"timeframe": "M15", "exit": "original", "gate": "higher", "proxy": {"score": 0.024081527804387597, "trades": 113, "mean_r": 0.062382276568461376, "r_profit_factor": 1.0728775637093633, "proxy_return_percent": 4.127836752731828, "proxy_drawdown_percent": 28.089171099159614}}; selected return -8.72%; reference -7.94%; stress -13.56%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 2.22%; stress 0.00%.
2020: {"timeframe": "H1", "exit": "minus100", "gate": "higher_trend", "proxy": {"score": 0.10710737685985264, "trades": 25, "mean_r": 0.2479601063884134, "r_profit_factor": 1.3542895766411975, "proxy_return_percent": 5.933530753900906, "proxy_drawdown_percent": 9.012670817044787}}; selected return -5.85%; reference -7.73%; stress -5.85%.
2022: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 7.51%; stress 0.00%.
2024: {"timeframe": "M15", "exit": "partial1R_runner2R", "gate": "higher_low_cost", "proxy": {"score": 0.25635281120781367, "trades": 44, "mean_r": 0.1388878194463596, "r_profit_factor": 1.3687090256516823, "proxy_return_percent": 6.01507880911103, "proxy_drawdown_percent": 3.8161207997233326}}; selected return -2.26%; reference -4.18%; stress 0.00%.
2026: {"timeframe": "M15", "exit": "partial1R_runner2R", "gate": "higher_low_cost", "proxy": {"score": 0.26565519583339237, "trades": 44, "mean_r": 0.14211198268666422, "r_profit_factor": 1.402053462179742, "proxy_return_percent": 6.214210200399917, "proxy_drawdown_percent": 3.8013950636673455}}; selected return 2.65%; reference -0.74%; stress 0.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 54, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.8060372533268088, 0.31712384595054915], "profit_factor_95ci": [0.13699121232308548, 1.475071272696743], "max_drawdown_r_95range": [9.835795647125758, 45.698390700570094], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### USDJPY

2016: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 2.56%; stress 0.00%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -3.31%; stress 0.00%.
2020: {"timeframe": "H1", "exit": "partial1R_runner2R", "gate": "higher", "proxy": {"score": 0.8422045763324438, "trades": 25, "mean_r": 0.3762793066084922, "r_profit_factor": 2.134923458452076, "proxy_return_percent": 9.54944130561759, "proxy_drawdown_percent": 1.8186894341649773}}; selected return 3.41%; reference -0.82%; stress 2.92%.
2022: {"timeframe": "H1", "exit": "atr3", "gate": "higher_low_cost", "proxy": {"score": 0.7631235092302054, "trades": 27, "mean_r": 0.4802511902894977, "r_profit_factor": 2.148873764793192, "proxy_return_percent": 13.384520487226625, "proxy_drawdown_percent": 2.7723524054572124}}; selected return 0.50%; reference -6.79%; stress 0.92%.
2024: {"timeframe": "H1", "exit": "atr3", "gate": "higher_low_cost", "proxy": {"score": 0.6929766061390279, "trades": 27, "mean_r": 0.47760239599101534, "r_profit_factor": 2.080730833267305, "proxy_return_percent": 13.263576635564478, "proxy_drawdown_percent": 3.026776455112512}}; selected return -5.42%; reference -4.27%; stress -3.37%.
2026: {"timeframe": "M15", "exit": "atr3", "gate": "higher", "proxy": {"score": 0.23893470085680868, "trades": 101, "mean_r": 0.13281467575066266, "r_profit_factor": 1.2463523241691516, "proxy_return_percent": 12.752093390168561, "proxy_drawdown_percent": 8.456273486593101}}; selected return 0.66%; reference -9.90%; stress 0.06%.

Mean-R block-bootstrap uncertainty: {"sample_size": 45, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.359181512271575, 0.2896217177103013], "profit_factor_95ci": [0.4629581747930259, 1.609935731479832], "max_drawdown_r_95range": [4.059161472858476, 19.034387459267364], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### USDCHF

2016: {"timeframe": "M15", "exit": "original", "gate": "higher_trend", "proxy": {"score": 0.6794873623956117, "trades": 71, "mean_r": 0.5552361208333383, "r_profit_factor": 1.713271570938294, "proxy_return_percent": 44.53452687146615, "proxy_drawdown_percent": 9.318051844810338}}; selected return -10.29%; reference 8.26%; stress -10.65%.
2018: {"timeframe": "M15", "exit": "twoR", "gate": "higher_liquid", "proxy": {"score": 0.051223103569962444, "trades": 72, "mean_r": 0.04658298724360218, "r_profit_factor": 1.0702134808454706, "proxy_return_percent": 2.642341890741151, "proxy_drawdown_percent": 8.504337906667503}}; selected return -9.43%; reference -7.72%; stress -9.85%.
2020: {"timeframe": "H1", "exit": "minus100", "gate": "higher", "proxy": {"score": 0.4999985921435425, "trades": 26, "mean_r": 0.5043314967683915, "r_profit_factor": 1.7990096541926295, "proxy_return_percent": 13.428677071756368, "proxy_drawdown_percent": 4.244560401558395}}; selected return 0.73%; reference 4.60%; stress 0.58%.
2022: {"timeframe": "H1", "exit": "minus100", "gate": "higher", "proxy": {"score": 0.27137651303463006, "trades": 26, "mean_r": 0.3529524022244978, "r_profit_factor": 1.524911045442718, "proxy_return_percent": 9.08856691718638, "proxy_drawdown_percent": 5.381426721704575}}; selected return 7.68%; reference 3.59%; stress 4.47%.
2024: {"timeframe": "M15", "exit": "original", "gate": "higher_liquid", "proxy": {"score": 0.030824224677114428, "trades": 68, "mean_r": 0.0887240441320566, "r_profit_factor": 1.103941154474596, "proxy_return_percent": 4.283580320562863, "proxy_drawdown_percent": 22.758444745741457}}; selected return 10.20%; reference 0.55%; stress 8.92%.
2026: {"timeframe": "H1", "exit": "twoR", "gate": "higher", "proxy": {"score": 1.2014257893100218, "trades": 26, "mean_r": 0.5889370499140462, "r_profit_factor": 2.2270067354757477, "proxy_return_percent": 16.1540713260659, "proxy_drawdown_percent": 2.1034959514638074}}; selected return 3.69%; reference 0.68%; stress 3.43%.

Mean-R block-bootstrap uncertainty: {"sample_size": 87, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.46840222197454007, 0.5806988620500096], "profit_factor_95ci": [0.47930163570236983, 1.8385617971417865], "max_drawdown_r_95range": [9.68047779826191, 49.057343511161726], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### USDCAD

2016: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -0.42%; stress 0.00%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -13.99%; stress 0.00%.
2020: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -2.18%; stress 0.00%.
2022: {"timeframe": "M15", "exit": "twoR", "gate": "higher", "proxy": {"score": 0.18465076855346413, "trades": 92, "mean_r": 0.10211138791073696, "r_profit_factor": 1.1582892554776092, "proxy_return_percent": 8.780971962955153, "proxy_drawdown_percent": 7.650418814414916}}; selected return -13.20%; reference -6.80%; stress -13.89%.
2024: {"timeframe": "M15", "exit": "atr3", "gate": "higher_trend", "proxy": {"score": 0.17131591520533618, "trades": 71, "mean_r": 0.12989643794079592, "r_profit_factor": 1.245833906457709, "proxy_return_percent": 8.915095303116317, "proxy_drawdown_percent": 8.367493211057099}}; selected return 3.51%; reference -4.23%; stress 2.57%.
2026: {"timeframe": "M15", "exit": "twoR", "gate": "higher_trend", "proxy": {"score": 0.23657966814240333, "trades": 68, "mean_r": 0.1909300914890943, "r_profit_factor": 1.3096210846984084, "proxy_return_percent": 13.009584333649382, "proxy_drawdown_percent": 8.70442859151016}}; selected return 2.23%; reference -1.98%; stress 1.93%.

Mean-R block-bootstrap uncertainty: {"sample_size": 58, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.5319831297710255, 0.18736836604015447], "profit_factor_95ci": [0.3751586918206737, 1.339237434140078], "max_drawdown_r_95range": [6.309292078529628, 33.54223229190935], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### EURGBP

2016: {"timeframe": "M15", "exit": "atr3", "gate": "higher_minimum_stop", "proxy": {"score": 0.06309927382667634, "trades": 90, "mean_r": 0.06964865645801638, "r_profit_factor": 1.1192977862530706, "proxy_return_percent": 5.329262957690228, "proxy_drawdown_percent": 13.773638383730303}}; selected return 3.80%; reference -10.47%; stress -2.31%.
2018: {"timeframe": "M15", "exit": "atr3", "gate": "higher_minimum_stop", "proxy": {"score": 0.2519219632720102, "trades": 80, "mean_r": 0.15676484192185952, "r_profit_factor": 1.3034425877969937, "proxy_return_percent": 12.29566392954251, "proxy_drawdown_percent": 7.746643369179562}}; selected return -9.44%; reference 1.55%; stress -12.59%.
2020: {"timeframe": "M15", "exit": "original", "gate": "higher_trend", "proxy": {"score": 0.29762608430728915, "trades": 64, "mean_r": 0.35896056086330086, "r_profit_factor": 1.447807619287091, "proxy_return_percent": 23.27197599966202, "proxy_drawdown_percent": 11.922876382047399}}; selected return -14.72%; reference -5.07%; stress -18.78%.
2022: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -6.83%; stress 0.00%.
2024: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 0.23%; stress 0.00%.
2026: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -2.97%; stress 0.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 89, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.5552343716852094, 0.08406033971196587], "profit_factor_95ci": [0.3123406289793138, 1.1604179544317053], "max_drawdown_r_95range": [11.401313277285123, 51.092729544420315], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### EURJPY

2016: {"timeframe": "M15", "exit": "original", "gate": "higher_minimum_stop", "proxy": {"score": 0.27731107465998384, "trades": 89, "mean_r": 0.24408078869657973, "r_profit_factor": 1.3004298160444625, "proxy_return_percent": 21.038883629033812, "proxy_drawdown_percent": 11.660333325635497}}; selected return 10.90%; reference -2.71%; stress 9.53%.
2018: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_minimum_stop", "proxy": {"score": 0.8900200684498544, "trades": 79, "mean_r": 0.3577153411677102, "r_profit_factor": 1.6526871806250711, "proxy_return_percent": 30.511959760469875, "proxy_drawdown_percent": 5.098995330513134}}; selected return -9.29%; reference 0.53%; stress -10.59%.
2020: {"timeframe": "M15", "exit": "original", "gate": "higher_trend", "proxy": {"score": 0.5352859177076137, "trades": 57, "mean_r": 0.6375451427139163, "r_profit_factor": 1.8513947050324593, "proxy_return_percent": 40.81349512703167, "proxy_drawdown_percent": 10.966618164520192}}; selected return -11.22%; reference -5.84%; stress -11.58%.
2022: {"timeframe": "H1", "exit": "minus100", "gate": "higher", "proxy": {"score": 0.04954655915980425, "trades": 29, "mean_r": 0.07718378185687559, "r_profit_factor": 1.1038551433152903, "proxy_return_percent": 1.795973789089178, "proxy_drawdown_percent": 5.996648403904603}}; selected return 1.55%; reference -4.25%; stress 1.26%.
2024: {"timeframe": "M15", "exit": "twoR", "gate": "higher_low_cost", "proxy": {"score": 0.20509617922889942, "trades": 31, "mean_r": 0.13566097903184202, "r_profit_factor": 1.2148565905294542, "proxy_return_percent": 3.9473433261303814, "proxy_drawdown_percent": 3.1561972158246077}}; selected return -10.14%; reference -6.20%; stress -3.93%.
2026: {"timeframe": "M15", "exit": "atr3", "gate": "higher_low_cost", "proxy": {"score": 0.05673101075700402, "trades": 47, "mean_r": 0.08460032707008215, "r_profit_factor": 1.1610956085214055, "proxy_return_percent": 3.556665158440442, "proxy_drawdown_percent": 10.297351333276294}}; selected return 0.03%; reference 3.81%; stress -1.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 116, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.44809648907250493, 0.14457551770401297], "profit_factor_95ci": [0.45342408291169467, 1.215222260933111], "max_drawdown_r_95range": [14.15759723020885, 57.504268481437094], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### EURCHF

2016: {"timeframe": "M15", "exit": "minus100", "gate": "higher_liquid", "proxy": {"score": 1.000325969340435, "trades": 55, "mean_r": 0.48816378152153267, "r_profit_factor": 1.7624623147820178, "proxy_return_percent": 29.389512018594033, "proxy_drawdown_percent": 4.386394449913212}}; selected return -8.11%; reference -8.64%; stress -10.83%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -8.49%; stress 0.00%.
2020: {"timeframe": "M15", "exit": "twoR", "gate": "higher", "proxy": {"score": 0.07703510667339837, "trades": 70, "mean_r": 0.07099915834230873, "r_profit_factor": 1.1077418904324743, "proxy_return_percent": 4.321431264167286, "proxy_drawdown_percent": 9.185452216874413}}; selected return -9.60%; reference 1.17%; stress -10.34%.
2022: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -4.38%; stress 0.00%.
2024: {"timeframe": "H1", "exit": "atr3", "gate": "higher", "proxy": {"score": 0.10932803788370628, "trades": 31, "mean_r": 0.16128733553539804, "r_profit_factor": 1.2947825324971787, "proxy_return_percent": 4.69540475813075, "proxy_drawdown_percent": 7.021825235072921}}; selected return -7.89%; reference -4.25%; stress -7.99%.
2026: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -2.97%; stress 0.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 56, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.739058152230588, -0.22918552186513444], "profit_factor_95ci": [0.21999654825596196, 0.7087606160819807], "max_drawdown_r_95range": [16.144041813414844, 42.56602969952767], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### EURAUD

2016: {"timeframe": "M15", "exit": "original", "gate": "higher_low_cost", "proxy": {"score": 0.05410517943982668, "trades": 69, "mean_r": 0.10384016976411575, "r_profit_factor": 1.124883986903568, "proxy_return_percent": 5.461555319505895, "proxy_drawdown_percent": 16.453334477680535}}; selected return -3.67%; reference 3.55%; stress -2.96%.
2018: {"timeframe": "H1", "exit": "original", "gate": "higher_low_cost", "proxy": {"score": 0.20000964705445912, "trades": 25, "mean_r": 0.40797996136479336, "r_profit_factor": 1.523539541349506, "proxy_return_percent": 9.842858301543632, "proxy_drawdown_percent": 7.884528614214137}}; selected return -4.90%; reference -6.78%; stress -2.00%.
2020: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 13.49%; stress 0.00%.
2022: {"timeframe": "H1", "exit": "atr3", "gate": "higher", "proxy": {"score": 0.3386316168675333, "trades": 25, "mean_r": 0.35745550780455454, "r_profit_factor": 1.7295301749076295, "proxy_return_percent": 8.873258355368163, "proxy_drawdown_percent": 4.2139888904169425}}; selected return -5.91%; reference -7.62%; stress -5.98%.
2024: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -0.29%; stress 0.00%.
2026: {"timeframe": "M15", "exit": "atr3", "gate": "higher_low_cost", "proxy": {"score": 0.07720442998038457, "trades": 54, "mean_r": 0.10803618216908092, "r_profit_factor": 1.2103421699723338, "proxy_return_percent": 5.507440976606204, "proxy_drawdown_percent": 11.625309638224223}}; selected return 3.78%; reference -2.00%; stress 0.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 34, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.8491365516798959, 0.2930821291949971], "profit_factor_95ci": [0.10559543025391123, 1.4874055378555586], "max_drawdown_r_95range": [6.385662883013793, 29.9845207176686], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### EURCAD

2016: {"timeframe": "M15", "exit": "original", "gate": "higher_low_cost", "proxy": {"score": 0.16992838980083433, "trades": 50, "mean_r": 0.2899079101338235, "r_profit_factor": 1.3626581870130445, "proxy_return_percent": 13.864169866547304, "proxy_drawdown_percent": 12.873170792816158}}; selected return -13.14%; reference 1.01%; stress -4.91%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -2.39%; stress 0.00%.
2020: {"timeframe": "M15", "exit": "twoR", "gate": "higher_trend", "proxy": {"score": 0.32701690517183246, "trades": 72, "mean_r": 0.2136854475085301, "r_profit_factor": 1.353108315667089, "proxy_return_percent": 15.703247220987482, "proxy_drawdown_percent": 7.52488415964253}}; selected return -3.85%; reference -3.15%; stress -4.49%.
2022: {"timeframe": "M15", "exit": "twoR", "gate": "higher_trend", "proxy": {"score": 0.25953852820821305, "trades": 64, "mean_r": 0.13064530354812612, "r_profit_factor": 1.2054493067334837, "proxy_return_percent": 7.974240025058021, "proxy_drawdown_percent": 4.958487979396475}}; selected return 7.02%; reference -4.26%; stress 3.16%.
2024: {"timeframe": "M15", "exit": "twoR", "gate": "higher_trend", "proxy": {"score": 0.42057324794437223, "trades": 65, "mean_r": 0.2016505556470072, "r_profit_factor": 1.3288058906649334, "proxy_return_percent": 13.183207594770208, "proxy_drawdown_percent": 4.958487979396509}}; selected return 0.60%; reference -3.31%; stress -2.24%.
2026: {"timeframe": "M15", "exit": "twoR", "gate": "higher_minimum_stop", "proxy": {"score": 0.23229843014239726, "trades": 94, "mean_r": 0.16955298496802698, "r_profit_factor": 1.2722532884035518, "proxy_return_percent": 16.078058154857278, "proxy_drawdown_percent": 10.830932633058099}}; selected return 1.36%; reference 7.84%; stress 0.90%.

Mean-R block-bootstrap uncertainty: {"sample_size": 92, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.3244880924257793, 0.16251777570405157], "profit_factor_95ci": [0.5909472108399887, 1.2593741868851185], "max_drawdown_r_95range": [7.627682063254742, 36.721676582564584], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### EURNZD

2016: {"timeframe": "M15", "exit": "original", "gate": "higher_minimum_stop", "proxy": {"score": 0.20195642431859245, "trades": 115, "mean_r": 0.20510925166298363, "r_profit_factor": 1.2491622205995618, "proxy_return_percent": 22.468799695056752, "proxy_drawdown_percent": 17.012619173182607}}; selected return 4.70%; reference -3.32%; stress -1.94%.
2018: {"timeframe": "M15", "exit": "original", "gate": "higher_minimum_stop", "proxy": {"score": 0.3751925022426026, "trades": 106, "mean_r": 0.3104916843557648, "r_profit_factor": 1.3848487097630766, "proxy_return_percent": 34.48944091687376, "proxy_drawdown_percent": 13.493267283209375}}; selected return -9.02%; reference -1.29%; stress -9.57%.
2020: {"timeframe": "M15", "exit": "twoR", "gate": "higher_liquid", "proxy": {"score": 0.21361542131235392, "trades": 66, "mean_r": 0.13420093725660265, "r_profit_factor": 1.2094168385114377, "proxy_return_percent": 8.473022942248122, "proxy_drawdown_percent": 6.388821728716632}}; selected return -5.31%; reference -11.34%; stress -5.95%.
2022: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 5.43%; stress 0.00%.
2024: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 4.80%; stress 0.00%.
2026: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_low_cost", "proxy": {"score": 0.1586477265590651, "trades": 68, "mean_r": 0.21424240443374618, "r_profit_factor": 1.340483872970407, "proxy_return_percent": 12.141989101332573, "proxy_drawdown_percent": 12.154495997591042}}; selected return -9.04%; reference -1.00%; stress -1.01%.

Mean-R block-bootstrap uncertainty: {"sample_size": 90, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.6137608691921159, 0.2705434282207579], "profit_factor_95ci": [0.33792703249614225, 1.3472053490749523], "max_drawdown_r_95range": [12.989851645116183, 59.225274718997596], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### GBPJPY

2016: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -1.21%; stress 0.00%.
2018: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_low_cost", "proxy": {"score": 0.6328579711835793, "trades": 77, "mean_r": 0.40698601610013263, "r_profit_factor": 1.6404064032408188, "proxy_return_percent": 32.536489662740784, "proxy_drawdown_percent": 7.595302273396742}}; selected return -0.49%; reference 9.87%; stress -5.28%.
2020: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_low_cost", "proxy": {"score": 0.5019998833278286, "trades": 70, "mean_r": 0.3956013888097247, "r_profit_factor": 1.5762920751357736, "proxy_return_percent": 27.595565877766393, "proxy_drawdown_percent": 8.257375011214307}}; selected return -3.54%; reference -3.32%; stress -1.51%.
2022: {"timeframe": "H1", "exit": "atr3", "gate": "higher_minimum_stop", "proxy": {"score": 0.492464234340171, "trades": 29, "mean_r": 0.4231329129691367, "r_profit_factor": 1.921192397093943, "proxy_return_percent": 12.578743222404864, "proxy_drawdown_percent": 4.049712554721019}}; selected return -1.10%; reference -3.34%; stress -1.30%.
2024: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -0.63%; stress 0.00%.
2026: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -1.99%; stress 0.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 46, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.5783149154632856, 0.4774782350056924], "profit_factor_95ci": [0.31427720350428556, 1.7077428277134319], "max_drawdown_r_95range": [6.72521523970148, 29.327946220822767], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### GBPCHF

2016: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_low_cost", "proxy": {"score": 0.0751774246519441, "trades": 54, "mean_r": 0.12002583345868839, "r_profit_factor": 1.1890413413529908, "proxy_return_percent": 5.513674422567427, "proxy_drawdown_percent": 11.951977585600327}}; selected return -2.68%; reference -6.76%; stress -1.97%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 1.59%; stress 0.00%.
2020: {"timeframe": "M15", "exit": "original", "gate": "higher_trend", "proxy": {"score": 0.32085004456766825, "trades": 70, "mean_r": 0.4103446325339082, "r_profit_factor": 1.5202633069491154, "proxy_return_percent": 30.249384447069062, "proxy_drawdown_percent": 14.0349850398652}}; selected return -14.27%; reference -3.38%; stress -14.51%.
2022: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_trend", "proxy": {"score": 0.09723580175457142, "trades": 79, "mean_r": 0.11943233574362562, "r_profit_factor": 1.1774453182271702, "proxy_return_percent": 7.830792345139037, "proxy_drawdown_percent": 13.004253605087934}}; selected return -4.17%; reference -7.77%; stress -6.67%.
2024: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_trend", "proxy": {"score": 0.14228076209400867, "trades": 77, "mean_r": 0.1898825313481883, "r_profit_factor": 1.2893699213951448, "proxy_return_percent": 13.52778197503357, "proxy_drawdown_percent": 15.020582039226515}}; selected return -10.10%; reference -7.05%; stress -9.39%.
2026: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -5.79%; stress 0.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 78, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.6986336821669323, -0.17692283552052818], "profit_factor_95ci": [0.1947295976549458, 0.7335619296697299], "max_drawdown_r_95range": [18.41252608534229, 56.00671242233713], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### GBPAUD

2016: {"timeframe": "M15", "exit": "original", "gate": "higher", "proxy": {"score": 0.028897640117085406, "trades": 113, "mean_r": 0.06182863255927033, "r_profit_factor": 1.0724847162625606, "proxy_return_percent": 4.087830078138177, "proxy_drawdown_percent": 23.184673558005198}}; selected return -13.67%; reference 8.55%; stress -26.79%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 12.45%; stress 0.00%.
2020: {"timeframe": "H1", "exit": "minus100", "gate": "higher_minimum_stop", "proxy": {"score": 0.8206659978564442, "trades": 26, "mean_r": 0.8149997201136352, "r_profit_factor": 2.4580844569331814, "proxy_return_percent": 22.86590848077248, "proxy_drawdown_percent": 4.2546313945717396}}; selected return -6.48%; reference -5.74%; stress -6.59%.
2022: {"timeframe": "H1", "exit": "original", "gate": "higher_minimum_stop", "proxy": {"score": 0.2788822213504878, "trades": 30, "mean_r": 0.5759996666855338, "r_profit_factor": 1.7676622286985653, "proxy_return_percent": 17.592867822511305, "proxy_drawdown_percent": 9.816964353120294}}; selected return -5.18%; reference -5.18%; stress -5.28%.
2024: {"timeframe": "H1", "exit": "minus100", "gate": "higher_low_cost", "proxy": {"score": 0.27127147632252674, "trades": 30, "mean_r": 0.4433490215472754, "r_profit_factor": 1.6848062380235096, "proxy_return_percent": 13.568036959365948, "proxy_drawdown_percent": 7.900480386321773}}; selected return -3.20%; reference -2.38%; stress -2.98%.
2026: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 3.72%; stress 0.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 77, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.7249371952959764, -0.008058769680282237], "profit_factor_95ci": [0.25291026432845287, 0.9902678739661752], "max_drawdown_r_95range": [14.786209763639247, 57.662681511763346], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### GBPCAD

2016: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 8.10%; stress 0.00%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 13.90%; stress 0.00%.
2020: {"timeframe": "H1", "exit": "original", "gate": "higher_minimum_stop", "proxy": {"score": 0.45584304569626355, "trades": 33, "mean_r": 0.6067906504564049, "r_profit_factor": 1.812279970825696, "proxy_return_percent": 20.71121561393392, "proxy_drawdown_percent": 6.991242266963571}}; selected return 3.43%; reference 3.43%; stress 3.00%.
2022: {"timeframe": "H1", "exit": "original", "gate": "higher", "proxy": {"score": 0.8293508713080354, "trades": 33, "mean_r": 0.7845250519365481, "r_profit_factor": 2.095408973117866, "proxy_return_percent": 27.864004568270182, "proxy_drawdown_percent": 5.042119895612673}}; selected return 4.49%; reference 4.49%; stress 4.19%.
2024: {"timeframe": "H1", "exit": "original", "gate": "higher", "proxy": {"score": 1.0423854098957528, "trades": 27, "mean_r": 0.9650538528040241, "r_profit_factor": 2.405088636669377, "proxy_return_percent": 28.26170981875571, "proxy_drawdown_percent": 4.063395375585344}}; selected return -0.15%; reference -0.15%; stress -0.68%.
2026: {"timeframe": "H1", "exit": "original", "gate": "higher", "proxy": {"score": 0.27177506615753033, "trades": 28, "mean_r": 0.4521428232991651, "r_profit_factor": 1.577368095576884, "proxy_return_percent": 12.43105078228799, "proxy_drawdown_percent": 7.25609342948188}}; selected return 0.57%; reference 0.57%; stress 0.30%.

Mean-R block-bootstrap uncertainty: {"sample_size": 32, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.29931094894650734, 1.0489688531318548], "profit_factor_95ci": [0.6731024567250956, 2.5971153186551765], "max_drawdown_r_95range": [4.260208662067272, 19.932007636687885], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### GBPNZD

2016: {"timeframe": "M15", "exit": "minus100", "gate": "higher_low_cost", "proxy": {"score": 0.4103035223707385, "trades": 87, "mean_r": 0.30533722091247273, "r_profit_factor": 1.4456775994869604, "proxy_return_percent": 28.403066541850386, "proxy_drawdown_percent": 10.369790445738115}}; selected return -9.06%; reference -3.27%; stress 0.58%.
2018: {"timeframe": "H1", "exit": "twoR", "gate": "higher", "proxy": {"score": 0.029182715907218874, "trades": 28, "mean_r": 0.04980859649665322, "r_profit_factor": 1.0758195108323854, "proxy_return_percent": 1.112861454790326, "proxy_drawdown_percent": 6.32643894071726}}; selected return -2.48%; reference 3.05%; stress -5.49%.
2020: {"timeframe": "M15", "exit": "atr3", "gate": "higher_trend", "proxy": {"score": 0.16255660669668673, "trades": 82, "mean_r": 0.1580596400751374, "r_profit_factor": 1.2820466603754483, "proxy_return_percent": 12.657994998897815, "proxy_drawdown_percent": 12.34217364654332}}; selected return -7.98%; reference -1.31%; stress -8.65%.
2022: {"timeframe": "M15", "exit": "minus100", "gate": "higher_liquid", "proxy": {"score": 0.186464436488964, "trades": 82, "mean_r": 0.18269330388888066, "r_profit_factor": 1.2535173840380058, "proxy_return_percent": 14.563658645528022, "proxy_drawdown_percent": 12.291226016312729}}; selected return -12.01%; reference -5.23%; stress -12.47%.
2024: {"timeframe": "M15", "exit": "original", "gate": "higher_liquid", "proxy": {"score": 0.2740424906539465, "trades": 81, "mean_r": 0.3406635980940721, "r_profit_factor": 1.4173947852821147, "proxy_return_percent": 28.38721907617392, "proxy_drawdown_percent": 15.518093237186292}}; selected return -1.46%; reference 0.55%; stress -2.17%.
2026: {"timeframe": "M15", "exit": "original", "gate": "higher_low_cost", "proxy": {"score": 0.020372422393895973, "trades": 59, "mean_r": 0.052076899103091955, "r_profit_factor": 1.059991946123077, "proxy_return_percent": 1.4979253386454783, "proxy_drawdown_percent": 12.178726293685926}}; selected return 3.94%; reference 7.63%; stress -2.02%.

Mean-R block-bootstrap uncertainty: {"sample_size": 125, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.4895567152540453, 0.050626864563097417], "profit_factor_95ci": [0.429261392484816, 1.0698016457832173], "max_drawdown_r_95range": [15.724773178240051, 67.61891243739811], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### AUDJPY

2016: excluded — Incomplete/gapped H1 comparator or less than four years training
2018: excluded — Incomplete/gapped H1 comparator or less than four years training
2020: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 24.89%; stress 0.00%.
2022: {"timeframe": "H1", "exit": "original", "gate": "higher", "proxy": {"score": 0.08665990158442555, "trades": 32, "mean_r": 0.26078822280894776, "r_profit_factor": 1.3204224539015446, "proxy_return_percent": 7.669484918252745, "proxy_drawdown_percent": 14.29976039378521}}; selected return 4.48%; reference 4.48%; stress 4.20%.
2024: {"timeframe": "H1", "exit": "original", "gate": "higher_minimum_stop", "proxy": {"score": 0.3444164006056862, "trades": 28, "mean_r": 0.6825975406311156, "r_profit_factor": 1.9302816849043605, "proxy_return_percent": 19.787361068247698, "proxy_drawdown_percent": 8.869685645379999}}; selected return 6.48%; reference 4.37%; stress 6.15%.
2026: {"timeframe": "H1", "exit": "original", "gate": "higher_minimum_stop", "proxy": {"score": 1.4286369316117489, "trades": 30, "mean_r": 1.169563659360045, "r_profit_factor": 2.793589777497298, "proxy_return_percent": 40.0336686845405, "proxy_drawdown_percent": 4.040446848413836}}; selected return -6.78%; reference -6.78%; stress -6.78%.

Mean-R block-bootstrap uncertainty: {"sample_size": 25, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.7903212495894321, 0.9022507629212639], "profit_factor_95ci": [0.2004673986397643, 2.2912224601442177], "max_drawdown_r_95range": [4.120947243810309, 20.203558228057865], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### CADJPY

2016: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_trend", "proxy": {"score": 0.5295649331095066, "trades": 79, "mean_r": 0.3555589918491666, "r_profit_factor": 1.5905372169595333, "proxy_return_percent": 29.93587787633718, "proxy_drawdown_percent": 8.424199780106944}}; selected return 5.20%; reference 0.28%; stress 2.09%.
2018: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_trend", "proxy": {"score": 0.9960890984006338, "trades": 69, "mean_r": 0.5510159835417833, "r_profit_factor": 1.9683503503218966, "proxy_return_percent": 43.506010075974984, "proxy_drawdown_percent": 6.229375115970315}}; selected return -5.02%; reference -1.14%; stress -6.39%.
2020: {"timeframe": "M15", "exit": "original", "gate": "higher_trend", "proxy": {"score": 0.49653317131934016, "trades": 64, "mean_r": 0.4428063064369953, "r_profit_factor": 1.5596288791126807, "proxy_return_percent": 29.928346283927908, "proxy_drawdown_percent": 8.98258538059762}}; selected return 6.25%; reference 6.27%; stress -4.94%.
2022: {"timeframe": "M15", "exit": "original", "gate": "higher_trend", "proxy": {"score": 0.543992651158231, "trades": 76, "mean_r": 0.37194085956311324, "r_profit_factor": 1.4667499400183215, "proxy_return_percent": 29.468265950641047, "proxy_drawdown_percent": 8.08542357361568}}; selected return -1.19%; reference -6.80%; stress -2.16%.
2024: {"timeframe": "M15", "exit": "partial1R_runner2R", "gate": "higher_low_cost", "proxy": {"score": 0.4620309407415824, "trades": 29, "mean_r": 0.31075290198320055, "r_profit_factor": 1.7335856706859882, "proxy_return_percent": 9.081314569151688, "proxy_drawdown_percent": 3.158378489831193}}; selected return -3.91%; reference 17.86%; stress -1.98%.
2026: {"timeframe": "H1", "exit": "minus100", "gate": "higher_minimum_stop", "proxy": {"score": 0.2912031255675078, "trades": 29, "mean_r": 0.4900865315179306, "r_profit_factor": 1.7690775873473503, "proxy_return_percent": 14.614633531108034, "proxy_drawdown_percent": 7.896415553952584}}; selected return 3.73%; reference 7.67%; stress 3.52%.

Mean-R block-bootstrap uncertainty: {"sample_size": 125, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.23197523834670766, 0.338650719563786], "profit_factor_95ci": [0.7042851518784667, 1.4947919205033355], "max_drawdown_r_95range": [8.681748106832472, 36.74209331210431], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### NZDJPY

2016: {"timeframe": "H1", "exit": "original", "gate": "higher", "proxy": {"score": 0.5397335558843886, "trades": 27, "mean_r": 0.7499852821430485, "r_profit_factor": 2.0351335489360447, "proxy_return_percent": 21.153729439166092, "proxy_drawdown_percent": 6.021227193656308}}; selected return 0.77%; reference 0.77%; stress 0.69%.
2018: {"timeframe": "H1", "exit": "original", "gate": "higher", "proxy": {"score": 0.6829440505063462, "trades": 26, "mean_r": 0.822499417217109, "r_profit_factor": 2.1581162474809457, "proxy_return_percent": 22.542304512960285, "proxy_drawdown_percent": 5.046023962665891}}; selected return -6.37%; reference -6.37%; stress -6.67%.
2020: {"timeframe": "M15", "exit": "twoR", "gate": "higher_liquid", "proxy": {"score": 0.27890961922777774, "trades": 54, "mean_r": 0.23433163818630465, "r_profit_factor": 1.3875813217083548, "proxy_return_percent": 12.794954160630034, "proxy_drawdown_percent": 7.267442816822944}}; selected return -9.32%; reference 10.85%; stress -9.68%.
2022: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -6.18%; stress 0.00%.
2024: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -7.02%; stress 0.00%.
2026: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -1.26%; stress 0.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 38, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.8025843775498638, -0.010059555026903491], "profit_factor_95ci": [0.16292566773231162, 0.9870226992846517], "max_drawdown_r_95range": [8.429538386708781, 32.44414412216586], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### CHFJPY

2016: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -7.71%; stress 0.00%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -8.65%; stress 0.00%.
2020: {"timeframe": "M15", "exit": "original", "gate": "higher_trend", "proxy": {"score": 0.14865447121988437, "trades": 59, "mean_r": 0.2624284400480916, "r_profit_factor": 1.3194352620041094, "proxy_return_percent": 14.684409094404117, "proxy_drawdown_percent": 15.538301356976248}}; selected return -4.91%; reference -6.79%; stress -5.35%.
2022: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -4.91%; stress 0.00%.
2024: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 1.36%; stress 0.00%.
2026: {"timeframe": "M15", "exit": "original", "gate": "higher_low_cost", "proxy": {"score": 0.09526196246244117, "trades": 41, "mean_r": 0.2768152791128773, "r_profit_factor": 1.3419292451952896, "proxy_return_percent": 10.637221071133185, "proxy_drawdown_percent": 17.835507132722917}}; selected return -6.12%; reference -5.85%; stress -2.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 34, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.8718634956568805, 0.19947721774152774], "profit_factor_95ci": [0.14225518587801195, 1.2419433952695462], "max_drawdown_r_95range": [7.6024900328307075, 30.260770808621913], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### XAUUSD

2016: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 3.41%; stress 0.00%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -1.63%; stress 0.00%.
2020: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 8.32%; stress 0.00%.
2022: {"timeframe": "H1", "exit": "runner2R", "gate": "higher", "proxy": {"score": 0.6838193113333831, "trades": 30, "mean_r": 0.7187648718625, "r_profit_factor": 2.4574379852056394, "proxy_return_percent": 22.449413410630157, "proxy_drawdown_percent": 5.020447057186416}}; selected return 4.05%; reference 7.70%; stress 3.92%.
2024: {"timeframe": "H1", "exit": "minus100", "gate": "higher", "proxy": {"score": 0.3856506850825674, "trades": 27, "mean_r": 0.4585438743642442, "r_profit_factor": 1.7114585747365185, "proxy_return_percent": 12.587559536815407, "proxy_drawdown_percent": 5.174811983104622}}; selected return 3.47%; reference 5.32%; stress 3.10%.
2026: {"timeframe": "H1", "exit": "minus100", "gate": "higher", "proxy": {"score": 0.42097814848602927, "trades": 26, "mean_r": 0.5172935055600691, "r_profit_factor": 1.8231614334090065, "proxy_return_percent": 13.80378270279472, "proxy_drawdown_percent": 5.174811983104632}}; selected return 1.36%; reference 5.30%; stress 1.29%.

Mean-R block-bootstrap uncertainty: {"sample_size": 22, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.09867416836081436, 0.9043541614436996], "profit_factor_95ci": [0.8740470424444132, 3.044552076475595], "max_drawdown_r_95range": [3.0433504365091224, 7.98786616732699], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### XAGUSD

2016: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -0.36%; stress 0.00%.
2018: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -5.27%; stress 0.00%.
2020: {"timeframe": "H1", "exit": "atr3", "gate": "higher", "proxy": {"score": 0.17362136007241666, "trades": 25, "mean_r": 0.39678790025632843, "r_profit_factor": 1.612688774505823, "proxy_return_percent": 9.448224783129099, "proxy_drawdown_percent": 8.732034839830384}}; selected return 4.37%; reference 4.67%; stress 3.27%.
2022: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -3.25%; stress 0.00%.
2024: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -7.17%; stress 0.00%.
2026: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -3.94%; stress 0.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 7, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.6934582136506815, 1.9925455515957287], "profit_factor_95ci": [0.2100112076616898, 7.8726765115973185], "max_drawdown_r_95range": [1.02245700813717, 6.144653623738971], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### WTIUSD

2016: excluded — Incomplete/gapped H1 comparator or less than four years training
2018: excluded — Incomplete/gapped H1 comparator or less than four years training
2020: excluded — Incomplete/gapped H1 comparator or less than four years training
2022: excluded — Incomplete/gapped H1 comparator or less than four years training
2024: excluded — Incomplete/gapped H1 comparator or less than four years training
2026: excluded — Incomplete/gapped H1 comparator or less than four years training

Mean-R block-bootstrap uncertainty: {"sample_size": 0, "note": "Insufficient sample for bootstrap"}

### BCOUSD

2016: {"timeframe": "M15", "exit": "atr3", "gate": "higher_trend", "proxy": {"score": 0.18205432044057746, "trades": 51, "mean_r": 0.15525562454223465, "r_profit_factor": 1.252006205589135, "proxy_return_percent": 7.371720812458471, "proxy_drawdown_percent": 6.55023441495608}}; selected return -8.36%; reference -5.85%; stress -8.51%.
2018: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_low_cost", "proxy": {"score": 0.5546014048717574, "trades": 32, "mean_r": 0.44036425163168014, "r_profit_factor": 1.7788632045308832, "proxy_return_percent": 14.114597615480108, "proxy_drawdown_percent": 4.011783342998909}}; selected return 2.18%; reference 1.48%; stress 3.36%.
2020: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference -7.73%; stress 0.00%.
2022: {"timeframe": "M15", "exit": "runner2R", "gate": "higher_low_cost", "proxy": {"score": 0.10005322568591479, "trades": 26, "mean_r": 0.14817730425934872, "r_profit_factor": 1.2335504678309923, "proxy_return_percent": 3.4342817820921523, "proxy_drawdown_percent": 5.640574149266698}}; selected return 0.45%; reference -9.47%; stress -3.01%.
2024: {"timeframe": "M15", "exit": "minus100", "gate": "higher_low_cost", "proxy": {"score": 0.13832151311668583, "trades": 30, "mean_r": 0.18671028137434065, "r_profit_factor": 1.2627655017959105, "proxy_return_percent": 5.229848065189091, "proxy_drawdown_percent": 6.168475076589708}}; selected return -4.08%; reference 11.06%; stress -1.00%.
2026: {"timeframe": "H1", "exit": "original", "gate": "cash"}; selected return 0.00%; reference 3.89%; stress 0.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 46, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.5645532475492523, 0.11022926817637167], "profit_factor_95ci": [0.28715009790862944, 1.208921271618444], "max_drawdown_r_95range": [5.886537086485411, 26.449311204120555], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### BTCUSD

2016: excluded — Incomplete/gapped H1 comparator or less than four years training
2018: excluded — Incomplete/gapped H1 comparator or less than four years training
2020: excluded — Incomplete/gapped H1 comparator or less than four years training
2022: {"timeframe": "H1", "exit": "original", "gate": "higher", "proxy": {"score": 0.21904553883042363, "trades": 26, "mean_r": 0.48833335741724876, "r_profit_factor": 1.5816191707231075, "proxy_return_percent": 12.462489021282174, "proxy_drawdown_percent": 9.024502419406733}}; selected return 3.52%; reference 3.52%; stress 1.88%.
2024: {"timeframe": "H1", "exit": "original", "gate": "higher_minimum_stop", "proxy": {"score": 0.3181808639577837, "trades": 37, "mean_r": 0.4956988985339711, "r_profit_factor": 1.592957494818024, "proxy_return_percent": 18.513686910743488, "proxy_drawdown_percent": 9.024502419406733}}; selected return 0.71%; reference 0.06%; stress -0.73%.
2026: {"timeframe": "H1", "exit": "atr3", "gate": "higher_trend", "proxy": {"score": 0.47286557480336777, "trades": 27, "mean_r": 0.39805978354832244, "r_profit_factor": 1.6696033967484556, "proxy_return_percent": 10.729645391164034, "proxy_drawdown_percent": 3.623017120806682}}; selected return -1.00%; reference -3.94%; stress -1.00%.

Mean-R block-bootstrap uncertainty: {"sample_size": 28, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.4945007254986547, 0.7986988857801627], "profit_factor_95ci": [0.5110920659662539, 2.0316513719930356], "max_drawdown_r_95range": [5.620819055200145, 19.164353689599597], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### ETHUSD

2016: excluded — Incomplete/gapped H1 comparator or less than four years training
2018: excluded — Incomplete/gapped H1 comparator or less than four years training
2020: excluded — Incomplete/gapped H1 comparator or less than four years training
2022: {"timeframe": "M15", "exit": "twoR", "gate": "higher_liquid", "proxy": {"score": 0.10526121659300314, "trades": 59, "mean_r": 0.11495369785169715, "r_profit_factor": 1.1694197089963534, "proxy_return_percent": 6.304444611171278, "proxy_drawdown_percent": 9.729675354499845}}; selected return -1.43%; reference 5.99%; stress -3.52%.
2024: {"timeframe": "H1", "exit": "original", "gate": "higher_trend", "proxy": {"score": 0.24689370913030223, "trades": 26, "mean_r": 0.516898274740279, "r_profit_factor": 1.6420252932555386, "proxy_return_percent": 13.321119290232497, "proxy_drawdown_percent": 8.53050659705038}}; selected return -5.85%; reference -4.00%; stress -5.86%.
2026: {"timeframe": "H1", "exit": "original", "gate": "higher", "proxy": {"score": 0.09185860372392769, "trades": 33, "mean_r": 0.1688645685118896, "r_profit_factor": 1.1954393260520944, "proxy_return_percent": 4.718465388715365, "proxy_drawdown_percent": 8.397485414468719}}; selected return 0.28%; reference 0.28%; stress -0.19%.

Mean-R block-bootstrap uncertainty: {"sample_size": 28, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.8721291758202709, 0.22392572834758934], "profit_factor_95ci": [0.1793082042390141, 1.347391741004089], "max_drawdown_r_95range": [4.4087903322745685, 25.64052240787623], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

### BNBUSD

2016: excluded — Incomplete/gapped H1 comparator or less than four years training
2018: excluded — Incomplete/gapped H1 comparator or less than four years training
2020: excluded — Incomplete/gapped H1 comparator or less than four years training
2022: {"timeframe": "H1", "exit": "twoR", "gate": "higher", "proxy": {"score": 0.6535718297469112, "trades": 28, "mean_r": 0.511378259109681, "r_profit_factor": 1.9904471986690326, "proxy_return_percent": 14.986613121937008, "proxy_drawdown_percent": 3.602850150415904}}; selected return -7.70%; reference -10.13%; stress -8.13%.
2024: {"timeframe": "H1", "exit": "minus100", "gate": "higher_trend", "proxy": {"score": 0.2913159256284815, "trades": 26, "mean_r": 0.2944103884419298, "r_profit_factor": 1.4128183373125305, "proxy_return_percent": 7.442284726664172, "proxy_drawdown_percent": 4.1315258261653725}}; selected return 0.20%; reference 3.51%; stress -0.45%.
2026: {"timeframe": "M15", "exit": "original", "gate": "higher_liquid", "proxy": {"score": 0.07687474876061025, "trades": 92, "mean_r": 0.16021809300342543, "r_profit_factor": 1.164518572370355, "proxy_return_percent": 12.461427366967094, "proxy_drawdown_percent": 25.71216923160009}}; selected return 8.48%; reference -5.65%; stress 4.96%.

Mean-R block-bootstrap uncertainty: {"sample_size": 35, "repetitions": 500, "block_size": 5, "seed": 1729, "mean_r_95ci": [-0.5705949231225463, 0.9288911046237133], "profit_factor_95ci": [0.4597989973007592, 2.3014991360823394], "max_drawdown_r_95range": [4.5841154478966715, 23.09499872407738], "note": "Circular five-trade blocks; overlaps and market regime dependence remain. Profit factor is R-weighted, not dollar-weighted. Drawdown in additive R, not account percent."}

## Research context

[Bailey et al.: Probability of backtest overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf). [Bank of Canada: FX fixings and intraday returns](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/). These motivate disciplined testing, not a promise that this strategy or a session filter works.
