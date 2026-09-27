# QuotePlot Agent

Lucy is an AI agent that combines market intelligence, web intelligence and on-chain data to investigate crypto assets through natural language.

QuotePlot Agent is an Indonesia Web3 Hackathon project. It brings those sources together in an evidence-led investigation, with an Angular dashboard for Lucy's analysis and a separate wallet workspace for Sepolia token management.

## Problem

Crypto research is fragmented. Market indicators, news and social context, machine-learning signals, and blockchain data are usually inspected in separate tools. A reader must combine them manually and distinguish observed data from unsupported claims.

## Solution

Ask Lucy a question about a token or market movement. The backend gathers available evidence from configured sources, labels each source as available, unavailable, or insufficient, and returns an investigation with the supporting evidence. Gemini can choose read-only research tools and narrate the results; deterministic backend collection and analysis provide the investigation data and fallback response.

The app also includes an independent wallet workspace to inspect seed-token inventory and factory creation events, and to create or manage tokens on Sepolia when the factory, ENS record, RPC, and wallet are configured. Lucy's investigation path is read-only: it does not sign transactions or trade.

## Architecture

```text
Angular browser app
  ├─ market and Lucy views ── HTTPS / WebSocket ──> FastAPI backend
  └─ wallet and token views ── wallet provider / JSON-RPC ──> Sepolia contracts

Lucy investigation (backend)
  ├─ market history and investor behavior ──> configured database
  ├─ ML market prediction ──────────────────> local model
  ├─ news and web context ─────────────────> Bright Data services
  ├─ token resolution and chain evidence ──> Ethereum TokenMap → JSON-RPC
  └─ evidence + context ───────────────────> Gemini narration / deterministic fallback
```

The Angular application is the active frontend. The legacy root `templates/` and `static/` directories are not served by FastAPI. In local development, Angular proxies `/api` and `/ws/thoughts` to `localhost:8000`. In production, the frontend's generated `quoteplot-config.js` supplies the backend origin for HTTPS and secure WebSocket requests. The backend must allow the exact frontend origin through `FRONTEND_URL`.

See [the architecture notes](docs/ARCHITECTURE.md) for component responsibilities, the request sequence, and deployment boundaries.

## AI Agent

Lucy combines deterministic investigation steps with Gemini's agentic tool use:

1. The backend identifies the token symbol and gathers market history and investor-behavior data from its configured database.
2. A local ML model contributes a prediction where its inputs and model are available.
3. Bright Data can provide news and web or social context when its credentials and services are configured.
4. The on-chain resolver looks up the symbol in the active Ethereum `TokenMap`; it does not let the model invent a contract address.
5. The backend combines the source results into evidence records and gives Lucy the context for a natural-language response. Gemini may invoke the read-only on-chain and web tools. If Gemini fails during a request, the deterministic investigation can still return its collected insight.

Evidence availability depends on database contents, credentials, provider access, and the configured chain endpoint. Missing feeds should be presented as unavailable rather than treated as confirmed findings. The Angular Lucy panel presents the response and its source evidence. Key endpoints include `POST /api/agent/reply`, `GET /api/agent/brightdata-status`, and WebSocket `/ws/thoughts`.

## Blockchain Integration

The investigation path uses an Ethereum JSON-RPC endpoint to read chain metadata and ERC-20 information for a contract resolved through `TokenMap`. It is read-only and does not require a user's wallet.

The token-management workspace is a separate Sepolia integration. The Hardhat project contains `SeedToken` and `SeedTokenFactory`; its local tests use a simulated chain. The browser wallet workspace requires:

- A deployed `SeedTokenFactory` on Sepolia.
- The Sepolia ENS name `seed-token-factory.eth` resolving to that factory address.
- A browser-accessible Sepolia RPC endpoint with the frontend origin allowed by the provider.
- A wallet connected to Sepolia (chain ID `11155111`) for actions that write to the chain.

The frontend does not contain a deployer private key. Do not expose private keys through Vercel variables or browser configuration. Deployment and live contract addresses must be verified separately; the repository does not publish or assert a factory address.

## Market Intelligence

Market intelligence is assembled from the application's stored market history and investor-behavior data, a local ML prediction, and optional news/web context from Bright Data. Lucy returns the source evidence alongside its explanation so users can see which inputs were available. Freshness and completeness depend on the backend database jobs and external providers; the app should not be treated as a guaranteed real-time market feed.

## Tech Stack

- **Frontend:** Angular, Angular Material, TypeScript, ethers.js, WalletConnect.
- **Backend:** Python, FastAPI, SQLAlchemy, Gemini, local ML components, Bright Data integrations, Ethereum JSON-RPC.
- **Contracts:** Solidity, Hardhat, `SeedToken`, and `SeedTokenFactory`.
- **Hosting:** Angular frontend on Vercel and backend on Coolify, as configured by the project owner. Hosting configuration is external to the repository; see the runtime environment variables below.

## Setup

### Requirements

- Python 3.11 or newer.
- Node.js and npm.
- A reachable MySQL-compatible database for the backend.
- A Gemini API key to initialize Lucy's agent router.
- Optional Bright Data and Ethereum RPC credentials for those evidence sources.
- For Sepolia contract deployment: a Sepolia RPC endpoint, a funded deployer account, and a Sepolia wallet.

### Environment variables

Copy the example file and fill in backend values locally:

```bash
cp env.example .env
```

Backend configuration:

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Required when the backend initializes Lucy's Gemini tools and narration. |
| `BRIGHTDATA_API_KEY` | Bright Data SERP, Web Unlocker, and MCP access. `BRIGHTDATA_TOKEN` is also accepted for MCP. |
| `BRIGHTDATA_CUSTOMER_ID` | Bright Data account identifier for API access. |
| `BRIGHTDATA_SERP_ZONE` | Bright Data SERP API zone. |
| `BRIGHTDATA_UNLOCKER_ZONE` | Optional Web Unlocker zone; defaults to `web_unlocker`. |
| `BRIGHTDATA_BROWSER_ZONE` | Optional Scraping Browser zone; defaults to `scraping_browser`. |
| `PYTH_HERMES_API_KEY` | Optional Pyth Hermes credential, when required by the provider. |
| `ETH_RPC_URL` | JSON-RPC URL used by Lucy's read-only on-chain evidence integration. |
| `DB_URL` | Optional full SQLAlchemy URL. Otherwise set `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_PORT`, and `DB_NAME` (defaults: root, empty password, localhost, 3306, `quoteplot`). |
| `FRONTEND_URL` | Exact browser origin allowed by backend CORS, for example `https://quote-plot-agent.vercel.app`. |
| `PORT` | Optional backend port; defaults to 80. The local command below explicitly uses 8000. |

Frontend build variables (Vercel):

| Variable | Purpose |
| --- | --- |
| `QUOTE_PLOT_BACKEND_ORIGIN` | Backend origin only, for example `https://quoteplot.carlssonstudio.com` (no `/api` suffix). |
| `QUOTE_PLOT_SEPOLIA_RPC_URL` | Browser-accessible Sepolia HTTPS RPC endpoint used by wallet/contract UI. It is public in the built JavaScript; restrict the provider key to the frontend origin. |

`npm run build` runs a prebuild script that writes these values into `frontend/public/quoteplot-config.js`. Use plain URL strings, not Markdown links. Set Vercel variables for the appropriate deployment environment and rebuild after changing them. Keep `SEPOLIA_PRIVATE_KEY` on the deployment operator's machine only; Hardhat uses it for contract deployment. Never commit credentials.

### Install and run locally

From the repository root:

```bash
python3 -m pip install -r requirements.txt
cd frontend && npm ci
cd ../contracts && npm ci
```

Start the backend from the repository root (it needs the configured database, schema, and token rows):

```bash
python3 -m uvicorn backend.main:app --reload --port 8000
```

In another terminal, start the Angular app:

```bash
cd frontend
npm start
```

Open [http://localhost:4200](http://localhost:4200). Initialize/update the database schema and seed data from the repository root as needed:

```bash
python3 -m backend.migrate_db
python3 -m backend.seed_data
```

The seeder fetches provider data and may require external access and provider credentials. Backend startup also checks/installs Playwright Chromium and starts scheduled data jobs; use a host that supports those dependencies and run a single backend process unless scheduled jobs are moved to a dedicated worker.

### Build and test

Backend tests and syntax check, from repository root:

```bash
python3 -m unittest \
  backend.test_token_identity \
  backend.blockchain.test_ethereum \
  backend.blockchain.test_token_intelligence \
  backend.routers.test_agent_investigation -v
python3 -m compileall -q backend
```

Frontend build and tests:

```bash
cd frontend
npm run build
npm test -- --watch=false
```

Hardhat compile and local contract tests:

```bash
cd contracts
npx hardhat compile
npx hardhat test
```

Hardhat tests run on a local simulated chain and do not require Sepolia credentials or a live deployment.

### Deployment expectations

The project currently serves its frontend at [quote-plot-agent.vercel.app](https://quote-plot-agent.vercel.app/) and its backend at [quoteplot.carlssonstudio.com](https://quoteplot.carlssonstudio.com/), as provided by the project owner. These URLs do not by themselves verify every integration or hosted data feed. Vercel builds the Angular static frontend; configure the backend host, database, CORS, secrets, and Playwright dependencies separately on Coolify. There is no checked-in automated production deployment pipeline for the backend or contracts.

To deploy the factory manually, from `contracts/`:

```bash
export SEPOLIA_RPC_URL="https://your-sepolia-rpc-endpoint"
export SEPOLIA_PRIVATE_KEY="0x..."
npx hardhat run scripts/deploy.ts --network sepolia
```

The script deploys `SeedTokenFactory`, creates a `Seed Token (SEED)`, and prints the addresses. Configure the Sepolia ENS record to resolve to the printed factory address before using the browser token-management workspace. Running the deploy command sends on-chain transactions.

## Demo

Open the [deployed frontend](https://quote-plot-agent.vercel.app/) and use Lucy to ask about a token or market move. A useful demo explains which market, web, ML, and on-chain evidence is available and points out any source reported unavailable. For the wallet workspace, connect a Sepolia wallet only after verifying that the factory is deployed and `seed-token-factory.eth` resolves correctly. The token investigation itself does not need a wallet.

See the [demo walkthrough](docs/DEMO.md) for a narrated sequence and preflight checks. The [submission checklist](docs/SUBMISSION.md) contains copy-ready project details and release checks. External hackathon submissions must be completed by the project team; this repository does not submit them automatically.
