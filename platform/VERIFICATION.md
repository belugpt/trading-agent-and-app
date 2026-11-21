# Release verification

- 14 application checks: SQLite-backed API behavior, request authorization, deduplication, sizing, schema health, client parsing, P&L controls and CSV formula handling.
- 82 Python strategy tests passed, including bullish/bearish swing-origin stop placement.
- Updated H1 swing-stop study covers 29 markets; its equity curves are historical research, not FBS account performance.
- Native Sites deployment succeeded as owner-private.
- Authenticated deployment checks cover /health, /, /specification and browser-identity rejection on /api/state. The health endpoint queries the migrated records table.
- No broker trades, synthetic setup events or account balances were seeded for deployment testing.
- Browser visual inspection, MetaEditor compilation, terminal WebRequest delivery and broker/demo order execution are not verified.
- CI workflow is configured in GitHub; local test results are not a claim that GitHub Actions has completed successfully.
