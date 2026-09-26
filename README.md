# QuotePlot Agent

QuotePlot Agent is a market-intelligence demo with an Angular browser app, a FastAPI backend, and Solidity token contracts. Lucy combines deterministic data collection and analysis with Gemini narration. The app includes wallet and token-management screens for Sepolia; using them requires a separately deployed factory and a wallet on Sepolia.

The Angular frontend is publicly reachable at [quote-plot-agent.vercel.app](https://quote-plot-agent.vercel.app/). The project owner reports that the backend has deployed successfully, but its public origin was not available during the September 26, 2026 readiness check. The live frontend bundle had no configured backend origin or custom Sepolia RPC, so API, Lucy, and wallet flows have not yet passed an end-to-end check. Live Sepolia token management also requires a deployed factory, a Sepolia ENS record, a browser-accessible RPC endpoint, and a Sepolia wallet. No hackathon submission is claimed.

## Architecture and investigation flow

```text
Angular app
  ├─ market, token and wallet views ── HTTP/WebSocket ──> FastAPI
  └─ wallet/provider ── JSON-RPC ──> Sepolia SeedTokenFactory and ERC-20s

Lucy token investigation (FastAPI)
  ├─ market history + investor-behavior context ──> local database
  ├─ ML market prediction ────────────────────────> local model
  ├─ recent news ─────────────────────────────────> Bright Data SERP API
  ├─ social and macro context ────────────────────> Bright Data MCP
  ├─ on-chain lookup ─────────────────────────────> TokenMap → Ethereum JSON-RPC
  └─ source evidence + context ───────────────────> Gemini narration, with deterministic fallback
```

For a token question, the backend identifies a symbol and gathers price history and behavior, runs the local market model, and requests web context. The on-chain reader resolves the symbol through an active Ethereum `TokenMap` entry before calling the configured Ethereum JSON-RPC endpoint for the latest block and ERC-20 metadata. It never invents a contract address. Results are combined into evidence records with explicit available, unavailable, or insufficient status. Gemini can use its read-only on-chain and Bright Data tools to narrate findings; if Gemini is not available for that request, Lucy falls back to the collected deterministic insight. The Angular Lucy panel displays the returned reply and source evidence. The integration does not sign transactions or trade on a user's behalf.

The Angular app is the active frontend. The older root `templates/` and `static/` content remains in the repository but is not served by FastAPI. In local development, the Angular proxy forwards `/api` and `/ws/thoughts` to `localhost:8000`. In production, the build-generated `quoteplot-config.js` sends HTTP and WebSocket traffic to the origin supplied through `QUOTE_PLOT_BACKEND_ORIGIN` over HTTPS/WSS.

See [the architecture notes](docs/ARCHITECTURE.md) for component responsibilities, the token-investigation request sequence, and deployment boundaries. See the [demo script](docs/DEMO.md) for the live walkthrough and [submission checklist](docs/SUBMISSION.md) for release gates and copy-ready project details.

## Repository layout

```text
backend/                 FastAPI routes, Lucy, data providers, database and ML logic
backend/blockchain/      Read-only Ethereum JSON-RPC and TokenMap resolver
frontend/                Angular market, Lucy, wallet and token-management UI
contracts/               SeedToken, SeedTokenFactory, Hardhat tests and deploy script
templates/, static/      Legacy frontend files retained during migration
```

## Requirements

- Python 3.11 or newer
- Node.js and npm (frontend lockfile uses npm)
- MySQL-compatible database for the backend
- Gemini and Bright Data credentials for the full Lucy/live-web experience
- Ethereum JSON-RPC URL for on-chain evidence
- For a Sepolia deployment: an RPC URL, a Sepolia-funded deployer account, and a wallet/browser extension configured for Sepolia

No live deployment or hosted service is implied by this repository. The Sepolia deploy command below sends transactions only when explicitly run with credentials.

## Configuration

Copy the example and fill in credentials locally:

```bash
cp env.example .env
```

Backend environment variables:

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Required at backend import for Gemini Lucy narration and tool calling. If Gemini fails during a request, token investigations return their collected deterministic insight. |
| `BRIGHTDATA_API_KEY` | Bright Data SERP, Web Unlocker, and MCP access; `BRIGHTDATA_TOKEN` is also accepted for MCP. |
| `BRIGHTDATA_CUSTOMER_ID` | Bright Data account identifier for API access. |
| `BRIGHTDATA_SERP_ZONE` | Bright Data SERP API zone. |
| `BRIGHTDATA_UNLOCKER_ZONE` | Optional Web Unlocker zone; defaults to `web_unlocker`. |
| `BRIGHTDATA_BROWSER_ZONE` | Optional Scraping Browser zone; defaults to `scraping_browser`. |
| `PYTH_HERMES_API_KEY` | Optional Pyth Hermes credential when the provider requires authentication. |
| `ETH_RPC_URL` | Ethereum JSON-RPC endpoint used by Lucy's read-only on-chain evidence path. |
| `DB_URL` | Optional complete SQLAlchemy database URL. When unset, use `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_PORT`, and `DB_NAME` (defaults: root, empty password, localhost, 3306, quoteplot). |
| `FRONTEND_URL` | Exact production browser origin allowed by FastAPI CORS. Required for the cross-origin Vercel frontend; the local Angular proxy does not need it. |
| `PORT` | Optional backend port for direct module startup; defaults to 80. The documented local command explicitly uses 8000. |

Hardhat Sepolia deployment uses `SEPOLIA_RPC_URL` and `SEPOLIA_PRIVATE_KEY` in the shell environment. Keep credentials out of source control. The Angular app accepts `QUOTE_PLOT_BACKEND_ORIGIN` and `QUOTE_PLOT_SEPOLIA_RPC_URL` as Vercel build environment variables. Set the backend origin to the Coolify HTTPS origin and set backend `FRONTEND_URL` to the exact Vercel origin. The RPC URL is public in the browser bundle, so restrict its key to the production frontend origin and allow that origin in the provider's CORS settings. Never put a wallet private key in frontend configuration. If the custom RPC URL is unset, local development falls back to ethers' default Sepolia providers, which may be rate-limited or blocked by browser CORS policy. Connect a Sepolia-compatible wallet for signing and transactions.

## Install

Run these from the repository root:

```bash
python3 -m pip install -r requirements.txt
cd frontend && npm ci
cd ../contracts && npm ci
```

## Run locally

The backend needs a reachable configured database, initialized schema and token rows. Set `GEMINI_API_KEY` before starting it because the agent router initializes Gemini during import. Bright Data and Ethereum RPC features need their corresponding credentials; missing optional feeds are represented as unavailable evidence. Backend startup also launches a background Playwright Chromium check/install and starts scheduled data jobs, so use a host that supports those dependencies and can reach the database.

Terminal 1, from the repository root:

```bash
python3 -m uvicorn backend.main:app --reload --port 8000
```

Terminal 2:

```bash
cd frontend
npm start
```

Open [http://localhost:4200](http://localhost:4200). Angular forwards `/api` and `/ws/thoughts` to the backend at port 8000.

Initialize/update database schema and seed data from the repository root:

```bash
python3 -m backend.migrate_db
python3 -m backend.seed_data
```

The seeder pulls provider data and therefore needs working external access and credentials for providers that require authentication.

## Build and validation

Backend deterministic tests (run at the repository root):

```bash
python3 -m unittest \
  backend.test_token_identity \
  backend.blockchain.test_ethereum \
  backend.blockchain.test_token_intelligence \
  backend.routers.test_agent_investigation -v
```

Backend syntax check:

```bash
python3 -m compileall -q backend
```

Angular production build and unit tests:

```bash
cd frontend
npm run build
npm test -- --watch=false
```

Hardhat compile and local deterministic contract tests:

```bash
cd contracts
npx hardhat compile
npx hardhat test
```

The Hardhat tests use the local simulated chain and do not require Sepolia, credentials, or external accounts.

## Sepolia deployment

Export deployment credentials in the shell, then run from `contracts/`:

```bash
export SEPOLIA_RPC_URL="https://your-sepolia-rpc-endpoint"
export SEPOLIA_PRIVATE_KEY="0x..."
npx hardhat run scripts/deploy.ts --network sepolia
```

The script deploys `SeedTokenFactory`, creates one `Seed Token (SEED)` through it, and prints both addresses after mining. This repository does not configure a production deployment pipeline, commit deployment addresses, or verify a live Sepolia deployment. Before the Angular token-management views can find the factory, configure the Sepolia ENS name `seed-token-factory.eth` to resolve to the printed factory address. Use a Sepolia wallet (chain ID `11155111`) for token creation, minting and ownership actions.

## HTTP and WebSocket API

Market endpoints include `GET /api/market/tickers`, `GET /api/market/history/{symbol}`, `GET /api/market/insight/{symbol}`, and `GET /api/market/web3-list`.

Lucy endpoints include `POST /api/agent/reply`, `GET /api/agent/brightdata-status`, `GET /api/agent/token-stats/{symbol}`, and WebSocket `/ws/thoughts`. Token investigation replies may include an `evidence` array for market history, ML prediction, web research and Ethereum on-chain sources.

## CI and hosted deployment

`frontend/vercel.json` configures only the Angular static frontend build. The backend and contracts have no checked-in production deployment pipeline. Configure the backend host, database, CORS origin, secrets, and Playwright support separately; configure Vercel's `QUOTE_PLOT_BACKEND_ORIGIN` and `QUOTE_PLOT_SEPOLIA_RPC_URL` build variables for the frontend. The RPC URL is public in the browser bundle and must be restricted by provider origin. Validate each component with the commands above before publishing. Backend startup schedules recurring data jobs, so run a single backend process unless the scheduler is moved to a dedicated worker.
