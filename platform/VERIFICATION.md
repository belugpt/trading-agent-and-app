# Release verification

Expanded release: 95 Python tests pass, including genuine M1-to-M15 aggregation and closed-higher-timeframe gating. Three MT5 programs compile with zero errors/warnings; compiled binaries and source hashes are packaged. Terminal/broker execution is not verified. Dashboard adds M15, aligned comparisons and chronological management profiles; client DOM-adapter runtime checks supplement syntax/API checks and are not browser visual QA.

The alert release has 18 passing API/client checks, including crossover deduplication and the dedicated alert feed. All 29 studies pass source-signature checks, original H1/H4 comparator equality and independent latest-frozen-window trade/metric replay. Deployment checks cover reports and ZIP download as well as database health and browser-identity rejection. No test broker orders or synthetic balances are posted.

- 14 application checks: SQLite-backed API behavior, request authorization, deduplication, sizing, schema health, client parsing, P&L controls and CSV formula handling.
- 82 Python strategy tests passed, including bullish/bearish swing-origin stop placement.
- Updated H1 swing-stop study covers 29 markets; its equity curves are historical research, not FBS account performance.
- Native Sites deployment succeeded as owner-private.
- Authenticated deployment checks cover /health, /, /specification and browser-identity rejection on /api/state. The health endpoint queries the migrated records table.
- No broker trades, synthetic setup events or account balances were seeded for deployment testing.
- Three programs compile in MetaEditor with zero errors and warnings. Browser visual inspection, actual popup/push delivery, terminal WebRequest delivery and broker/demo order execution are not verified.
- CI workflow is configured in GitHub; local test results are not a claim that GitHub Actions has completed successfully.
