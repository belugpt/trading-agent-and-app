# SME Trading Operations

Private hosted operations workspace, MT5 indicator/EA prototypes and historical strategy research.

Start with [the detailed product specification](platform/PRODUCT_SPECIFICATION.md), [app build instructions](platform/README.md), and [terminal installation](mt5/AGENT_SETUP.md).

The cloud provides journaling, risk estimates, telemetry and research. It does not execute trades. MT5 execution defaults off; compilation and demo validation remain required. Historical research used crossover stops; current swing-origin stops and M5+ operation require separate validation.

Source is public; deployment remains owner-private. Never commit broker passwords, service tokens, live account records or market-data archives.
