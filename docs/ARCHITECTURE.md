# QuotePlot Agent architecture

## Runtime components

| Component | Location | Responsibility |
| --- | --- | --- |
| Angular browser app | `frontend/` | Market display, Lucy chat/evidence, Sepolia wallet connection, and SeedTokenFactory UI. |
| FastAPI service | `backend/main.py`, `backend/routers/` | Market and Lucy HTTP APIs plus `/ws/thoughts`. Startup also schedules data-sync jobs. |
| Database | SQLAlchemy models in `backend/models.py` | Market history, token identity/chain mappings, behavior context, and prediction records. |
| Lucy investigation | `backend/routers/agent.py` | Combines recent local prices and behavior, ML prediction, optional Bright Data context, and optional Ethereum evidence; Gemini narrates when configured. |
| Ethereum read adapter | `backend/blockchain/` | Reads JSON-RPC block and ERC-20 metadata. It resolves symbols through an active `TokenMap` entry and does not guess addresses or sign transactions. |
| Contracts | `contracts/` | `SeedToken` and `SeedTokenFactory`, with local Hardhat tests and a manually invoked deployment script. |

The root `templates/` and `static/` folders are legacy assets. They are not served by the current FastAPI application.

## Lucy token investigation

```text
Browser → POST /api/agent/reply
  → classify request and identify the token symbol
  → load recent prices and behavior context from the database
  → in parallel: run local market prediction, request optional web feeds,
    and resolve the token through TokenMap before an Ethereum JSON-RPC read
  → mark each source available, unavailable, or insufficient
  → Gemini narration when available; deterministic collected insight on failure
  → reply text + symbol/prediction + evidence array → Angular Lucy panel
```

`GET /api/agent/brightdata-status` reports the web provider badge; `GET /api/agent/token-stats/{symbol}` returns stored prediction statistics. The thought stream at `/ws/thoughts` is a separate WebSocket used for background thought/status messages. Optional services may be unavailable without turning the missing source into a negative market signal.

## Sepolia wallet path

The Angular provider connects read-only to the configured Sepolia RPC by default and uses the connected EIP-1193 wallet for signing actions. The token UI resolves the ENS name `seed-token-factory.eth`; it does not read a factory address from the deployment script automatically. A usable deployment therefore requires:

1. Deploy `SeedTokenFactory` on Sepolia and retain the printed factory and example token addresses.
2. Configure `seed-token-factory.eth` on Sepolia to resolve to that factory.
3. Configure `QUOTE_PLOT_SEPOLIA_RPC_URL` at frontend build time and allow the deployed frontend origin in the RPC provider's CORS/key restrictions.
4. Connect a wallet on chain ID `11155111` and use test ETH for transaction fees.

The contracts' automated tests run against a local simulated chain. They do not verify deployment, ENS, RPC CORS, or wallet behavior on Sepolia.

## Deployment boundaries

- `frontend/vercel.json` builds and serves the Angular static app only.
- Configure `QUOTE_PLOT_BACKEND_ORIGIN` for the browser HTTP and WebSocket base and set the exact frontend origin as backend `FRONTEND_URL` for CORS. Locally, Angular's proxy forwards `/api` and `/ws/thoughts` to port 8000.
- The backend requires `GEMINI_API_KEY` at import/startup and a working database. Bright Data and `ETH_RPC_URL` enable additional evidence feeds. The JSON-RPC URL in the browser bundle is public; use a restricted key.
- Backend startup runs recurring APScheduler jobs in-process and checks/installs Playwright Chromium in a background thread. Run one backend process unless scheduling is moved out of the web process; make sure the runtime supports Playwright and its browser dependencies.
- No backend hosting manifest, live deployment addresses, ENS record, or hosted environment values are checked into this repository.
