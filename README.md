# QuotePlot Agent

Lucy is an AI agent that combines market intelligence, web intelligence and on-chain data to investigate crypto assets through natural language.

QuotePlot Agent is an Indonesia Web3 Hackathon project. It presents Lucy's investigations and source evidence in an Angular application, alongside a separate wallet workspace for testnet token management.

## Problem

Crypto research is fragmented across market indicators, news and social context, machine-learning signals, and blockchain explorers. People must combine these sources manually and decide which claims have evidence behind them.

## Solution

Ask Lucy about a crypto asset or market move in natural language. The backend gathers available information, identifies missing or insufficient sources, and returns an investigation with its evidence. Gemini can use read-only research tools and narrate the result; deterministic collection and analysis supply the evidence and a fallback response.

The app also has a separate token-management workspace for inspecting token inventory and factory creation events, and managing tokens on a configured test network. Lucy's investigation flow is read-only: it does not sign transactions or trade.

## Architecture

```text
Angular browser app
  ├─ Market and Lucy views ─ HTTPS / WebSocket ─> FastAPI backend
  └─ Wallet and token views ─ wallet / JSON-RPC ─> configured testnet contracts

Lucy investigation (backend)
  ├─ Market history and investor behavior ─> configured database
  ├─ ML market prediction ──────────────────> local model
  ├─ News and web context ─────────────────> Bright Data services
  ├─ Token resolution and chain evidence ──> Ethereum TokenMap → JSON-RPC
  └─ Evidence and context ─────────────────> Gemini narration / deterministic fallback
```

The Angular application is the active frontend. The legacy root `templates/` and `static/` folders are not served by FastAPI. In local development, Angular proxies `/api` and `/ws/thoughts` to `localhost:8000`. In production, the generated `quoteplot-config.js` supplies the backend origin for HTTPS and secure WebSocket requests. Set backend `FRONTEND_URL` to the exact frontend origin for CORS.

## AI Agent

Lucy combines deterministic investigation with Gemini's agentic tool use:

1. The backend identifies the token symbol and gathers market history and investor-behavior data from its configured database.
2. A local ML model contributes a prediction when its inputs and model are available.
3. Bright Data can provide news and web or social context when credentials and services are configured.
4. The on-chain resolver looks up the symbol in an active Ethereum `TokenMap` entry. It does not let the model invent a contract address.
5. The backend aggregates source results into evidence records with available, unavailable, or insufficient status. Gemini can narrate the findings and invoke read-only tools. If Gemini is unavailable during a request, Lucy can return the collected deterministic insight.

The Angular Lucy panel displays the response and evidence. Key endpoints include `POST /api/agent/reply`, `GET /api/agent/brightdata-status`, and WebSocket `/ws/thoughts`. Missing optional feeds are reported as unavailable rather than treated as negative market signals.

## Blockchain Integration

The investigation path uses Ethereum JSON-RPC to read the latest block and ERC-20 metadata for a contract resolved through `TokenMap`. This path is read-only and does not require a connected wallet.

Token management is a separate EVM integration that can target Ethereum Sepolia or BSC Testnet. The Hardhat project contains `SeedToken` and `SeedTokenFactory`. BSC Testnet uses chain ID `97` and a configured factory address. Sepolia uses chain ID `11155111` and can resolve the factory through `seed-token-factory.eth`. The browser wallet workspace requires:

- `SeedTokenFactory` deployed on the selected network.
- For Sepolia, `seed-token-factory.eth` resolving to the factory, or a configured factory address. For BSC Testnet, configure the factory address directly.
- A browser-accessible read RPC endpoint with the frontend origin allowed by the provider. The connected wallet supplies transaction signing; read calls use the configured frontend RPC.
- A wallet connected to the selected network for on-chain write actions.

The wallet chain must match `QUOTE_PLOT_NETWORK` (`11155111` for Sepolia or `97` for BSC Testnet). If they differ, the factory view is unavailable and the token inventory is empty until the wallet switches networks. Creation-event history is loaded only after clicking **Search events**. The token inventory checks for new creation events every 15 seconds, scans at most 10,000 blocks per request, and backs off to 120 seconds after RPC errors.

The frontend does not contain a deployer private key. Deployment and live contract addresses must be verified separately; no factory address is asserted here. Hardhat tests use a simulated local chain and do not prove a live testnet deployment.

## Market Intelligence

Market analysis combines stored market history and investor-behavior data, a local ML prediction, and optional news/web context from Bright Data. Lucy returns source evidence alongside its explanation so users can see which inputs were available. Freshness and completeness depend on backend data jobs and external providers; this is not a guaranteed real-time feed.

## Tech Stack

- **Frontend:** Angular, Angular Material, TypeScript, ethers.js, WalletConnect.
- **Backend:** Python, FastAPI, SQLAlchemy, Gemini, local ML components, Bright Data integrations, Ethereum JSON-RPC.
- **Contracts:** Solidity, Hardhat, `SeedToken`, and `SeedTokenFactory`.
- **Hosting:** Angular frontend on Vercel and backend on Coolify, as provided by the project owner. Hosting is configured outside this repository; the project has no checked-in automated production deployment pipeline for the backend or contracts.

## Setup

### Requirements

- Python 3.11 or newer.
- Node.js and npm.
- A reachable MySQL-compatible database for the backend.
- A Gemini API key to initialize Lucy's agent router.
- Optional Bright Data and Ethereum RPC credentials for those evidence sources.
- For testnet deployment: a BSC Testnet or Sepolia RPC endpoint and funded testnet deployer; for wallet management, a wallet on the selected network.

### Environment variables

Copy the example file and fill in the backend values locally:

```bash
cp env.example .env
```

Backend variables:

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Required when the backend initializes Lucy's Gemini tools and narration. |
| `BRIGHTDATA_API_KEY` | Bright Data SERP, Web Unlocker, and MCP access. `BRIGHTDATA_TOKEN` is also accepted for MCP. |
| `BRIGHTDATA_CUSTOMER_ID` | Bright Data account identifier for API access. |
| `BRIGHTDATA_SERP_ZONE` | Bright Data SERP API zone. |
| `BRIGHTDATA_UNLOCKER_ZONE` | Optional Web Unlocker zone; defaults to `web_unlocker`. |
| `BRIGHTDATA_BROWSER_ZONE` | Optional Scraping Browser zone; defaults to `scraping_browser`. |
| `PYTH_HERMES_API_KEY` | Optional Pyth Hermes credential, when required by the provider. |
| `ETH_RPC_URL` | JSON-RPC URL for Lucy's read-only on-chain evidence path. |
| `DB_URL` | Optional full SQLAlchemy URL. Otherwise set `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_PORT`, and `DB_NAME` (defaults: root, empty password, localhost, 3306, `quoteplot`). |
| `FRONTEND_URL` | Exact browser origin allowed by backend CORS, e.g. `https://quote-plot-agent.vercel.app`. |
| `PORT` | Optional backend port; defaults to 80. The local command below uses port 8000. |

Frontend build variables for Vercel:

| Variable | Purpose |
| --- | --- |
| `QUOTE_PLOT_BACKEND_ORIGIN` | Backend origin only, e.g. `https://quoteplot.carlssonstudio.com` (no `/api` suffix). |
| `QUOTE_PLOT_NETWORK` | Exact value `sepolia` (default) or `bscTestnet`; controls the wallet/contract UI, not Lucy's Ethereum evidence source. |
| `QUOTE_PLOT_SEPOLIA_RPC_URL` | Optional browser-accessible Sepolia HTTPS RPC endpoint. |
| `QUOTE_PLOT_BSC_TESTNET_RPC_URL` | Optional browser-accessible BSC Testnet HTTPS RPC; defaults to `https://bsc-testnet-dataseed.bnbchain.org`. |
| `QUOTE_PLOT_FACTORY_ADDRESS` | Deployed factory address; required for BSC Testnet, optional for Sepolia when ENS is configured. |

`npm run build` runs a prebuild script that writes these values into `frontend/public/quoteplot-config.js`. Vercel must build the `frontend` directory so the prebuild script can read its environment variables. Use plain URL strings, not Markdown links. Set the variables for the deployment environment and redeploy after changing them; they are embedded at build time. RPC URLs are public in the browser bundle; restrict provider keys to the frontend origin. Keep deployer private keys out of Vercel and browser configuration. Never commit credentials.

### Install and run locally

From the repository root:

```bash
python3 -m pip install -r requirements.txt
cd frontend && npm ci
cd ../contracts && npm ci
```

Start the backend from the repository root. It needs a configured database, initialized schema, and token rows:

```bash
python3 -m uvicorn backend.main:app --reload --port 8000
```

In another terminal, start Angular:

```bash
cd frontend
npm start
```

Open [http://localhost:4200](http://localhost:4200). Initialize/update the database schema and seed data from the repository root as needed:

```bash
python3 -m backend.migrate_db
python3 -m backend.seed_data
```

The seeder fetches provider data and may require external access and provider credentials. Backend startup also checks/installs Playwright Chromium and starts scheduled data jobs; use a host that supports those dependencies and run one backend process unless scheduled jobs are moved to a dedicated worker.

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

Hardhat tests run on a local simulated chain; they do not require testnet credentials or verify a live deployment.

### Deploy to BSC Testnet

The deployment script sends transactions. Use a testnet-funded deployer account and check the selected network and deployer address before running it.

```bash
cd contracts
export BSC_TESTNET_RPC_URL="https://bsc-testnet-dataseed.bnbchain.org"
export BSC_TESTNET_PRIVATE_KEY="0x..." # keep local; never commit
npx hardhat run scripts/deploy.ts --network bscTestnet
```

BSC Testnet uses chain ID `97` and native test currency `tBNB`. Save the printed factory address for the submission form and Vercel `QUOTE_PLOT_FACTORY_ADDRESS`. Configure Vercel with `QUOTE_PLOT_NETWORK=bscTestnet`, `QUOTE_PLOT_FACTORY_ADDRESS`, and a browser-accessible BSC Testnet RPC endpoint, then redeploy. Connect the wallet to BSC Testnet as well; a wallet left on Sepolia will show the switch-network prompt and the BSC factory inventory will remain empty. The app uses the configured RPC for reads and the wallet for writes. Live inventory updates poll incrementally with rate-limit backoff; use **Search events** to load historical creation events. This path does not use Sepolia ENS. See [BNB Chain wallet configuration](https://docs.bnbchain.org/bnb-smart-chain/developers/wallet-configuration/) for current network details.

## Demo

### Preflight

- Configure backend `GEMINI_API_KEY`, database, `ETH_RPC_URL`, and `FRONTEND_URL`. Configure Bright Data credentials if live web context will be shown.
- Configure Vercel `QUOTE_PLOT_BACKEND_ORIGIN`, `QUOTE_PLOT_NETWORK`, the corresponding RPC variable, and (for BSC Testnet) `QUOTE_PLOT_FACTORY_ADDRESS`, then rebuild. Confirm the API responds at `/docs`, `/api/market/tickers`, and `/api/agent/brightdata-status`, and that `/ws/thoughts` connects.
- Confirm the database contains current market rows and an active Ethereum `TokenMap` entry for the symbol you will demo.
- For BSC Testnet wallet UI, verify the factory on BscScan, configure its address and the read RPC, and connect a wallet on chain ID `97`. For Sepolia, verify the factory/ENS resolution and connect a wallet on chain ID `11155111`. The wallet chain must match the configured frontend network. Skip either segment if its checks are incomplete.
- Clear stale filters. Creation-event searches are manual and use a recent block window; choose a valid range and click **Search events**.
- Keep API keys, private keys, and account details out of the recording. Do not present unavailable evidence as a negative signal or show unverified deployment addresses.

### Suggested 3–4 minute walkthrough

1. **Problem and product:** Show the market panel and explain that Lucy brings market, model, web, and chain evidence into one investigation.
2. **Lucy investigation:** Ask Lucy to investigate a symbol confirmed in the deployed database. Show the response and evidence rows; identify which sources are available, unavailable, or insufficient.
3. **Blockchain evidence:** Explain that the backend resolves the symbol through an active `TokenMap` entry and reads the mapped contract via Ethereum JSON-RPC; Lucy does not invent addresses or sign transactions.
4. **BSC Testnet workspace, only if verified:** Show the wallet, inventory, and matching factory event. Keep it read-only unless deliberately demonstrating a test transaction.
5. **Close:** Explain that deterministic backend collection and fallback support Gemini's narration, while the user can inspect the evidence and missing sources.

For a pitch deck, cover the fragmented research problem, Lucy's product flow, the evidence aggregation architecture, the mapped Ethereum read path, limitations/safety boundaries, and a demo using only verified live values. Check the [official hackathon page](https://luma.com/pcc699dv) and [submission portal](https://indonesiaweb3hack.xyz) for current deadline and submission requirements. External submissions and video uploads are completed by the project team; this repository does not submit them automatically.

The project currently serves its frontend at [quote-plot-agent.vercel.app](https://quote-plot-agent.vercel.app/) and backend at [quoteplot.carlssonstudio.com](https://quoteplot.carlssonstudio.com/), as supplied by the project owner. These URLs do not by themselves verify every integration, data feed, testnet deployment, or wallet flow.
