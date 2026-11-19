# SME Trading Operations

Private hosted operations app, MT5 indicator/EA prototypes and Python research engine.

Read [the detailed product specification](platform/PRODUCT_SPECIFICATION.md), [app setup](platform/README.md), and [MT5 installation](mt5/AGENT_SETUP.md).

Build: `cd platform`, then `npm run build`, `npm run validate`, `npm test` (Node 24). Research tests: `python -m unittest discover -s tests`.

Cloud execution is disabled. Terminal compilation and demo validation remain pending. Current swing-stop and M5+ operation do not inherit historical crossover-stop H1 results. Source is public; hosting remains owner-private. Do not commit credentials or broker records.
