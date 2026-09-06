# QuotePlot Agent

QuotePlot Agent is a Web3 market-intelligence application. The Angular frontend provides the terminal UI and wallet experience, the FastAPI backend provides market and Lucy AI services, and the Hardhat project manages the Sepolia smart contracts.

## Architecture

```text
frontend/   Angular terminal UI, WalletConnect, ethers.js
backend/    FastAPI APIs, Lucy AI, market ingestion, database, WebSocket stream
contracts/  Solidity contracts, Hardhat tests, deployment scripts
```

Runtime communication:

```text
Angular -> /api/market/* -> FastAPI -> database and market providers
Angular -> /api/agent/*  -> FastAPI -> Lucy AI and Bright Data
Angular -> /ws/thoughts  -> FastAPI WebSocket
Angular -> wallet/RPC    -> Sepolia contracts
```

The active frontend is `frontend/`. The root `static/` and `templates/` directories are legacy HTMX/Jinja assets retained temporarily for migration reference; they are no longer mounted by FastAPI.

## Features

- Market ticker and token insight panels
- Lucy AI chat with persistent browser sessions
- Live Lucy thought stream over WebSocket
- Bright Data market, news, and sentiment enrichment
- WalletConnect and MetaMask support
- Sepolia token factory and ERC-20 token management
- Token creation, minting, ownership transfer, sorting, filtering, and event history
- Pyth and CoinGecko market-data ingestion

## Project Layout

```text
backend/
  main.py                 # FastAPI entry point
  routers/                # JSON API routers
  brain.py                # Market analysis and intent classification
  database.py             # SQLAlchemy configuration and persistence helpers
  tasks.py                # Scheduled oracle and monitoring jobs
  utils.py                # Market providers and data utilities
  lucy/                   # Legacy text-processing helpers used by the brain
frontend/
  src/app/                # Angular components and services
  proxy.conf.json         # Local /api and /ws proxy to FastAPI
contracts/
  contracts/              # SeedToken and SeedTokenFactory
  scripts/                # Deployment and setup scripts
  test/                   # Hardhat tests
static/                   # Legacy HTMX assets
templates/               # Legacy Jinja templates
```

## Requirements

- Python 3.10+
- Node.js and npm
- A MySQL-compatible database for production, or the configured local database
- A funded Sepolia wallet for contract deployment and transactions
- Optional Gemini, Bright Data, and Pyth Hermes credentials

## Configuration

From the repository root:

```bash
cp env.example .env
```

Set the values required by the backend. Important variables include:

```env
GEMINI_API_KEY=...
BRIGHTDATA_API_KEY=...
BRIGHTDATA_CUSTOMER_ID=...
PYTH_HERMES_API_KEY=...
DB_URL=mysql+pymysql://...
FRONTEND_URL=http://localhost:4200
```

`PYTH_HERMES_API_KEY` is needed when Hermes returns HTTP 401. The backend batches Pyth requests and retries rate-limited HTTP 429 responses, but valid provider credentials are still required.

## Install Dependencies

Backend:

```bash
cd /Users/carlsson/Documents/QuotePlot-Agent
python3 -m pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
```

Contracts:

```bash
cd contracts
npm install
```

## Run Locally

Start the backend from the repository root so package imports resolve correctly:

```bash
cd /Users/carlsson/Documents/QuotePlot-Agent
python3 -m uvicorn backend.main:app --reload --port 8000
```

Start Angular in a second terminal:

```bash
cd /Users/carlsson/Documents/QuotePlot-Agent/frontend
npm start
```

Open [http://localhost:4200](http://localhost:4200). Angular proxies `/api` and `/ws` to FastAPI on port 8000.

## Database Seeding

Run migrations and seed market tokens from the repository root:

```bash
python3 -m backend.migrate_db
python3 -m backend.seed_data
```

The seed process discovers token feeds, stores Pyth IDs in `token_map`, and seeds baseline investor-behavior data.

## Sepolia Contracts

The contracts project is configured for Sepolia. Compile and test it with:

```bash
cd contracts
npx hardhat compile
npx hardhat test
```

Deploy using the project’s configured Sepolia account and RPC settings:

```bash
npx hardhat run scripts/deploy.ts --network sepolia
```

After deployment, update the frontend’s contract address configuration used by `SeedTokenFactoryService`. The connected wallet must use Sepolia, chain ID `11155111`.

## Validation

Frontend build:

```bash
cd frontend
npm run build
```

Backend syntax check:

```bash
cd /Users/carlsson/Documents/QuotePlot-Agent
python3 -m compileall -q backend
```

The Angular build currently emits bundle-size and WalletConnect CommonJS warnings. The Hardhat suite may require its existing ESM test imports to be updated before it passes.

## API Surface

Market:

- `GET /api/market/tickers`
- `GET /api/market/history/{symbol}`
- `GET /api/market/insight/{symbol}`
- `GET /api/market/web3-list`

Lucy:

- `POST /api/agent/reply`
- `GET /api/agent/brightdata-status`
- `GET /api/agent/token-stats/{symbol}`
- `WebSocket /ws/thoughts`
