# SME Trading Operations

Private hosted research and operations workspace. Start with [PRODUCT_SPECIFICATION.md](PRODUCT_SPECIFICATION.md) for the full release scope, acceptance criteria, data model, risk rules and production execution roadmap.

## Build and test

Requires Node 24 (tests use built-in node:sqlite). No dependency installation.

The public source contains `research.json.gz`, a compressed historical-data snapshot read by the build with Node's built-in zlib. Local research tools regenerate this snapshot; no broker credentials or runtime journal records are included. The current release includes confirmed-alignment M15/H1/H4 comparisons, chronological trade-management profiles, and the cleanly compiled MT5 package. Profiles are research evidence, not automatically applied EA settings.

```sh
npm run build
npm run validate
npm test
```

Worker entrypoint: `dist/server/index.js`. Sites deploys the exact pushed source with `.openai/hosting.json` and applies `drizzle/` schema migrations to its DB binding. Keep build output and service tokens out of Git. Owner-private Sites authentication is mandatory; do not expose this Worker directly to the public Internet unchanged.

Delivered: research tables and export, persistent manual journal, account-currency sizing calculator, append-only telemetry and stale-heartbeat monitoring. Terminal source lives in `../mt5/`. Cloud execution is disabled and no trade command endpoint exists. The current EA is a prototype: shared strategy core, restart-safe order reconciliation and account-wide risk reservations remain next-release work. MT5 compilation and demo execution are not verified.

The monitor needs an owner-provisioned Site service token and an allowed WebRequest origin. The credential belongs only in local terminal inputs, never in GitHub, frontend JavaScript, log output or journal notes. Deployment access is independent from the public source repository.

Research is recorded H1 data through 17 November 2026, using crossover-candle stops. The new swing-stop revision and M5+ support have not inherited those results. No fake account balances or live trades are seeded. Local API tests use an in-memory SQLite database; no test trades are sent to a broker.
