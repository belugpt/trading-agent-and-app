# Updated swing-origin stop backtest

Research source data, not FBS broker data. Inferred ticks and fixed costs are not verified FBS contract specifications. Includes existing AUDJPY/WTI coverage gaps. H4 uses complete UTC-aligned groups of four H1 bars; incomplete groups excluded. UTC H4 candles may differ from FBS server-aligned candles. No M5 data was synthesized. Per-market $10,000 accounts, not a combined portfolio.

H4, 126/252 SMA OPEN, midpoint entry, −200 target, 1% risk. Original data window through November 2026; crypto starts 2017. No parameters optimized for this run.

| Market | Return % | DD % | Trades | Win % |
|---|---:|---:|---:|---:|
| EURUSD | -15.90 | 24.83 | 46 | 10.87 |
| GBPUSD | -21.67 | 25.14 | 53 | 9.43 |
| AUDUSD | -12.83 | 16.06 | 46 | 13.04 |
| NZDUSD | 11.69 | 10.38 | 52 | 21.15 |
| USDJPY | -6.76 | 12.23 | 41 | 14.63 |
| USDCHF | 5.62 | 18.41 | 46 | 19.57 |
| USDCAD | -11.47 | 17.90 | 35 | 11.43 |
| EURGBP | -10.44 | 18.06 | 56 | 14.29 |
| EURJPY | -2.03 | 12.01 | 42 | 16.67 |
| EURCHF | -4.12 | 14.05 | 43 | 16.28 |
| EURAUD | -7.07 | 15.28 | 43 | 13.95 |
| EURCAD | -15.56 | 19.39 | 40 | 10.00 |
| EURNZD | -32.90 | 33.12 | 51 | 3.92 |
| GBPJPY | -5.66 | 14.92 | 45 | 15.56 |
| GBPCHF | -23.32 | 27.91 | 55 | 9.09 |
| GBPAUD | -9.24 | 17.81 | 49 | 14.29 |
| GBPCAD | -16.94 | 16.99 | 58 | 12.07 |
| GBPNZD | -19.11 | 22.89 | 50 | 10.00 |
| AUDJPY | 0.26 | 8.62 | 40 | 17.50 |
| CADJPY | 24.76 | 7.76 | 47 | 25.53 |
| NZDJPY | -15.61 | 22.90 | 45 | 11.11 |
| CHFJPY | -14.89 | 16.34 | 44 | 11.36 |
| XAUUSD | -11.31 | 16.79 | 35 | 11.43 |
| XAGUSD | -0.86 | 15.38 | 35 | 17.14 |
| WTIUSD | 14.41 | 5.90 | 27 | 25.93 |
| BCOUSD | 16.94 | 7.59 | 25 | 28.00 |
| BTCUSD | -5.99 | 10.84 | 28 | 14.29 |
| ETHUSD | 15.43 | 8.51 | 30 | 26.67 |
| BNBUSD | -13.61 | 19.20 | 30 | 10.00 |
## H1 comparison and H4 coverage

MA periods remain 126/252 chart bars; H4 spans four times the elapsed time. No H4-specific optimization was performed. Incomplete H4 groups are omitted, not filled. Gap counts include market closures as well as unresolved source gaps. AUDJPY and WTI retain known source deficiencies; this is not FBS tick-based execution validation.

| Market | H1 return % | H4 return % | H4 bars | H1 bars omitted | H4 gaps |
|---|---:|---:|---:|---:|---:|
| EURUSD | 13.37 | -15.90 | 24896 | 4562 | 995 |
| GBPUSD | -34.59 | -21.67 | 24879 | 4598 | 1001 |
| AUDUSD | -26.48 | -12.83 | 24881 | 4592 | 1003 |
| NZDUSD | -41.63 | 11.69 | 24884 | 4576 | 999 |
| USDJPY | -32.80 | -6.76 | 24850 | 4693 | 1023 |
| USDCHF | 19.44 | 5.62 | 24886 | 4589 | 993 |
| USDCAD | -37.24 | -11.47 | 24887 | 4577 | 998 |
| EURGBP | -49.51 | -10.44 | 24888 | 4581 | 995 |
| EURJPY | -22.05 | -2.03 | 24826 | 4746 | 1048 |
| EURCHF | -34.31 | -4.12 | 24889 | 4575 | 996 |
| EURAUD | 6.62 | -7.07 | 24861 | 4667 | 1013 |
| EURCAD | -27.46 | -15.56 | 24864 | 4668 | 1023 |
| EURNZD | 4.45 | -32.90 | 24815 | 4772 | 1030 |
| GBPJPY | -20.76 | -5.66 | 24808 | 4777 | 1047 |
| GBPCHF | 10.66 | -23.32 | 24874 | 4586 | 1010 |
| GBPAUD | 0.49 | -9.24 | 24856 | 4650 | 1025 |
| GBPCAD | -3.25 | -16.94 | 24832 | 4687 | 1037 |
| GBPNZD | -27.33 | -19.11 | 24838 | 4644 | 1018 |
| AUDJPY | 38.23 | 0.26 | 23495 | 4465 | 968 |
| CADJPY | 65.06 | 24.76 | 24881 | 4605 | 999 |
| NZDJPY | -2.38 | -15.61 | 24874 | 4600 | 1003 |
| CHFJPY | -48.35 | -14.89 | 24776 | 4887 | 1063 |
| XAUUSD | 24.88 | -11.31 | 22244 | 10741 | 3234 |
| XAGUSD | -0.42 | -0.86 | 22347 | 10581 | 3232 |
| WTIUSD | -11.88 | 14.41 | 17504 | 9042 | 2502 |
| BCOUSD | -22.26 | 16.94 | 16503 | 21714 | 4134 |
| BTCUSD | 22.06 | -5.99 | 20219 | 88 | 28 |
| ETHUSD | 3.81 | 15.43 | 20219 | 88 | 28 |
| BNBUSD | -9.00 | -13.61 | 19735 | 88 | 27 |