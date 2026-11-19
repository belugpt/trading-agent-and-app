# SME Trading Operations — Product specification sheet

Version: 0.1.0 | Date: 19 November 2026 | Owner: Charles Nwachebelu / belugpt

## Product outcome

Give the owner one private workspace to inspect strategy evidence, calculate risk, journal decisions and monitor MT5. Keep broker execution in the terminal. Every displayed number must have a source, strategy version and period; never label sample or historical data as live.

## Release boundaries and status

| Area | Release 0.1 delivery | Remaining acceptance work |
|---|---|---|
| Hosted workspace | Owner-private Worker app, responsive navigation, actual research summaries | Browser visual QA and user acceptance |
| Journal | Durable D1 append-only manual entries, bounded input validation, CSV export | Pagination beyond latest 300 records, retention/archive jobs |
| Risk calculator | Account-equity budget, tick-value sizing, volume rounding, cost reserve and portfolio-cap estimate | Automatic broker contract synchronization and atomic live reservations |
| Research | 29 markets, optimization and eight exit policies, filters and CSV | New swing-stop and M5+ backtests |
| Telemetry | Append-only deduplicated bridge endpoint, heartbeats, stale-state detection, event feed | Real terminal integration verification and alert delivery verification |
| MT5 monitor | Source sending heartbeat and deal events to private Site | Compile and exercise WebRequest credentials in a terminal |
| Trading EA | Existing source for alert-only / optional limit execution, swing stop, sizing | MetaEditor compile, Strategy Tester, demo execution, restart reconciliation |
| Setup forwarding | Endpoint accepts setup events | Trading EA must emit structured setup events; monitor alone does not |
| Shared strategy library | Architecture and migration contract defined | Indicator/EA shared pure core remains a next-release task |
| Cloud execution | Intentionally absent | Requires separate specification and explicit rollout decision |

Delivery does not certify trading profitability. The current terminal code remains a prototype, not a production-certified trading system. Infrastructure availability and strategy edge are separate requirements.

## Users and access

The single owner is the trader, researcher and operator. Browser access uses the Sites-provided authenticated identity. Owner-private platform permissions also protect service access. The bridge accepts append-only machine events after Sites dispatch authentication. No service token is embedded in source, client JavaScript, reports or GitHub. The database is shared inside this owner-only boundary, not multi-tenant.

Do not widen the Site audience without adding per-user row authorization, independent device authentication, token rotation and revocation. The current bridge must not be deployed unchanged on a public Worker endpoint.

## Information architecture

1. Overview: terminal reporting status, latest equity report, setup count within returned records, strategy schematic and release readiness.
2. Setups & events: received timestamps, event type, terminal alias, symbol and message, with type filter.
3. Position sizing: editable broker contract inputs and explicit block reasons.
4. Trade journal: manual entry form, version field, notes, realized P&L and CSV export.
5. Research lab: historical optimization / exit tables, symbol and asset-class filter, CSV export and period caveats.
6. MT5 connection: installation flow, service access boundary, endpoint and schema.
7. Product specification: release scope, limitations and downloadable detailed specification.

## Strategy contract — current revision

Strategy version: swing-stop-1.20. Chart periods M5 and higher; MA periods refer to chart bars. Fast/slow are 126/252 simple moving averages of OPEN by default. Equality retains the last strict side. Open-price crossovers invalidate opposite pending limits before new completed-candle structure is processed.

Structure lookback is 50 prior candles. After crossover, require a new directional extreme beyond prior structure, followed by a 0.1%-of-extreme close retracement. A new-extreme candle cannot also confirm that retracement. Track the deepest retracement low (buy) or highest retracement high (sell) before a later wick breaks structure. Freeze that origin before using breakout-candle extrema; their intrabar order is unknown.

Track continuation beyond the first breakout. Freeze the endpoint only after a later qualifying close retracement. Place the limit at the origin/endpoint midpoint. No retrospective fill on the confirmation candle. Reject if the midpoint was already passed before order creation.

BUY stop = swing-origin low minus StopBufferTicks × broker tick size. SELL stop = swing-origin high plus that buffer. Default buffer is one tick and must be positive. Freeze the stop reference at breakout; later retracements do not move it. Target is endpoint plus two directional full swing ranges (−200). No trailing stop in the current default. Tick normalization must preserve the intended stop side.

Historical baseline and exit-study metrics used crossover-candle stops. They do not validate this revised stop or chart periods beyond H1. Historical forex/metals generally begin 2010; Binance crypto begins 2017. Cutoff is 17 November 2026. WTI and AUDJPY have documented source gaps. None of the main chronological optimization policies passed its complete screen.

## Functional requirements and acceptance criteria

| ID | Requirement | Acceptance criterion |
|---|---|---|
| AUTH-01 | Reject anonymous browser data access | /api/state and journal requests without platform identity return 401 |
| AUTH-02 | Reject cross-origin browser mutation | Foreign Origin returns 403 before database mutation |
| DATA-01 | Persist manual journals | Reload returns the saved entry and timestamp |
| DATA-02 | Validate input server-side | Missing symbol/notes, nonfinite values and oversized bodies fail with 4xx |
| DATA-03 | Deduplicate machine events | Same eventId produces one database row and duplicate=true on retry |
| DATA-04 | Preserve provenance | Journal source=manual, bridge event kind and received time stored separately |
| RISK-01 | Calculate budget | budget = equity × riskPercent / 100 |
| RISK-02 | Model stop loss | perLotLoss = abs(entry−stop)/tickSize × tickValue × (1+reserve/100) |
| RISK-03 | Round volume down | No minimum-lot rounding up; over-budget minimum yields zero lots |
| RISK-04 | Preview portfolio cap | Block if requested risk plus declared committed risk exceeds cap |
| RISK-05 | Preserve distinction | Calculator cannot submit orders or reserve account risk |
| MON-01 | Display disconnected honestly | No heartbeat means no equity figure and disconnected state |
| MON-02 | Detect staleness | Last received heartbeat older than 180 seconds shows stale |
| MON-03 | Never imply reconciliation | Equity is labeled terminal-reported, not broker-verified |
| RES-01 | Separate research/live data | Research appears only in research views and labeled historical metrics |
| RES-02 | Preserve version caveat | Swing-stop mismatch is visible on overview and research screens |
| EXP-01 | Export escaped CSV | Quotes/newlines correctly quoted; formula-leading strings protected |
| UI-01 | Responsive and accessible | Navigation, forms and tables usable on narrow screens; labels and visible keyboard focus |
| EXEC-01 | Keep cloud read/record-only | No cloud order-submission or execution-toggle endpoint |
| EXEC-02 | Default EA alerts-only | ExecuteTrades=false after fresh installation |

## Data model

Release 0.1 table `records`: `id TEXT PRIMARY KEY`, `kind TEXT`, `payload TEXT(JSON)`, `created_at TEXT(UTC ISO8601)`. Index on kind/created_at. API returns newest 300 records; overview counts refer to this bounded window. Journal records contain symbol, direction, notes, realized outcome, strategyVersion, actor and source. Machine records contain account alias, terminal ID, optional symbol/message, version and optional event time. Heartbeats add balance, equity and mode (demo/live/unknown). Received time, not untrusted device time, determines staleness.

No broker passwords, access tokens or raw account login IDs are required in records. Operators should choose aliases. Current journal records are immutable through the app; corrections are appended as new notes. Future schema additions require append-only migrations; do not modify applied migration SQL.

## API specification

| Method and route | Access | Behavior |
|---|---|---|
| GET / | Private Site | HTML workspace |
| GET /health | Private Site boundary | Version, execution-disabled state and DB binding availability (not full DB connectivity test) |
| GET /api/state | Browser identity | Latest records and bundled historical research |
| POST /api/journal | Browser identity + same-origin | Validate and append manual record |
| POST /api/size | Browser identity + same-origin | Pure risk estimate; no database mutation |
| POST /api/bridge | Owner-private service access | Validate event envelope; INSERT OR IGNORE by eventId |
| GET /specification | Private Site | Detailed Markdown specification |

JSON body maximum: 32,768 characters, with early Content-Length rejection when supplied. Supported bridge kinds: heartbeat, setup, deal, error. Envelope requires eventId, account and terminal. Unknown kinds fail. Heartbeat equity/balance must be finite and nonnegative. Request errors return JSON and do not expose stack traces. No cross-origin API access is enabled.

## Terminal bridge and delivery semantics

`SME_Monitor.mq5` runs on a separate MT5 chart because one chart supports one EA. Use HTTPS SiteOrigin and owner-provided service token in the OAI-Sites-Authorization header. Allow the origin in MT5 WebRequest settings. It sends heartbeats periodically and appends matching symbol trade events. Setup events require integration with the actual trading EA, explicitly not inferred from the monitor's presence.

The initial monitor reports HTTP errors and does not guarantee durable delivery through outages. Server idempotency protects repeated IDs, but the next release must add an on-disk outbox, backoff, dead-letter tracking and replay. Dashboard failure does not remove broker-held stops/targets. Terminal offline means no new signals, client-side cancellations or trailing updates.

## Production execution design — next release

Move causal setup transitions into one `SMEStrategy.mqh` library consumed by indicator and EA; preserve a replay fixture contract with Python. Unique setup ID includes account alias, symbol, timeframe, crossover timestamp and strategy hash. Persist acknowledged setup/order IDs atomically before accepting new work.

Use a single account supervisor for all symbols/timeframes. Compute currency-group and account-wide committed risk from positions AND pending orders; reserve risk atomically before submission, then release only after broker reconciliation. Block excessive spread, stale prices, margin violations, daily loss threshold and maximum drawdown. Distinguish stop-entry budget from guaranteed-loss claims.

State machine: detected → qualified → risk-reserved → submit-requested → accepted-pending → partially-filled/filled → closed, with rejected/cancel-requested/cancelled/expired/unknown states. Persist broker ticket, deal IDs, requested/filled volume, price, costs and version. Unknown request outcomes require reconciliation before any retry. OrderCheck success is not a fill guarantee. Process OnTradeTransaction and account snapshots, including out-of-order transactions.

At startup, reconcile the broker ledger, local durable ledger and pending risk reservations before enabling new entries. Separate operator actions: pause new entries, cancel owned pending orders, and flatten owned positions. Pausing must not remove protective stops or silently cancel unrelated orders. Any future cloud command needs authenticated authorization, expiry, idempotency and terminal acknowledgement; none is implemented in release 0.1.

## Infrastructure and deployment

Cloud: Sites owner-private HTTPS Worker, D1 storage with schema migrations, dependency-free HTML/JS interface. Source repository: belugpt/trading-agent-and-app, user-created public repository. Hosting source is a separate Sites-managed Git repository; the release records both commit references. GitHub contains no secrets or broker records. Market archives and generated per-trade research runs are excluded.

Terminal: user's MT5 installation initially; dedicated Windows VPS only after demo verification. The app does not provision a VPS or connect a broker automatically. One active executor per account/strategy; failover requires a lease to avoid duplicate trading. Monitor uptime, terminal age, HTTP failures, disk capacity and broker connectivity. Journal exports are manual in this release; scheduled encrypted backups and tested restore procedures are next-release operational requirements.

Build: `node scripts/build.mjs`, then `node scripts/validate-artifact.mjs`, then `node --test tests/*.test.mjs`. No npm install is required. Build embeds reviewed HTML, specification and historical summaries into `dist/server/index.js`, plus hosting manifest and D1 migration metadata. Publish exact pushed source through Sites workflow. D1 migrations apply before Worker publication. Rollback must account for already-applied schemas.

## Test and rollout plan

1. Unit tests: lot rounding, invalid stops, risk-cap rejection, minimum lots, invalid/oversized input.
2. HTTP tests: anonymous access, cross-origin mutation, durable journal persistence, event deduplication, unsupported event kind, absent DB, unknown routes.
3. Content/build tests: valid ESM Worker, all views present, chart explicitly schematic, no fake live balance, research source count 29.
4. Deployment: owner-private audience confirmed; migration and HTTP data paths verified with owner service access when available. Browser visual review is separately recorded, never implied by HTTP tests.
5. MT5: compile cleanly, test real tick behavior, verify labels and stops, test minimum lots and broker limits, request rejection, terminal restart, lost network and duplicate prevention. These terminal gates remain pending until a real terminal run.
6. Demo forward operation: reconcile every signal, request, fill, cancellation and stop; compare costs and behavior with research. Live rollout requires a separate informed decision and small constrained exposure.

## Success measures

Data integrity: no fabricated live figures; no duplicate event row under repeated ID; no journal mutation acknowledged without durable storage. Risk estimates round down and reject impossible minimums. Operators can identify current strategy version, research mismatch and terminal freshness. Production execution success is measured by correct order lifecycle and reconciled risk, not win rate alone.

## Known limitations

No hosted trading commands, broker authentication, automated VPS provisioning, portfolio risk reservations, shared MQL strategy core, persistent EA order ledger, unattended cloud alerts, durable terminal outbox, or automatic backups yet. The EA's per-chart exposure checks do not constitute account-wide risk control. No claim is made that MetaEditor compilation or demo trading has passed. Browser and device runtime verification must be reported separately from source and API checks.
