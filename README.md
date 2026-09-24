# QuotePlot Agent

QuotePlot Agent is a Web3 market-intelligence application. Angular provides the complete browser interface for market data, Lucy, wallets, and token management. FastAPI provides JSON APIs and the thought-stream WebSocket, and Hardhat manages the Sepolia smart contracts.

## Architecture

```text
frontend/   Angular market, Lucy, wallet, and token interface
backend/    FastAPI APIs, Lucy AI, market ingestion, database, WebSocket
contracts/  Solidity contracts, Hardhat tests, deployment scripts
templates/  Previous Jinja frontend retained as migration reference
static/     Previous frontend scripts and styles retained as migration reference
```

Runtime communication:

```text
Angular -> /api/market/* and /api/agent/* -> FastAPI
Angular -> /ws/thoughts -> FastAPI WebSocket
Angular -> wallet/RPC -> Sepolia contracts
```

Angular is the only active frontend. It consolidates the market chart, ticker search, Lucy chat, thought stream, wallet connection, token factory, and contract events. The old Jinja templates and root `static/` assets remain in the repository for reference while the Angular interface is validated; FastAPI no longer serves them.

## Features

- Searchable market ticker, price history chart, and token insight panels
- Lucy AI chat with persistent browser sessions, Bright Data status, reliability stats, and thought stream
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
  blockchain/
    ethereum.py           # Read-only Ethereum JSON-RPC adapter
    token_intelligence.py # TokenMap symbol → Ethereum ERC-20 metadata
  lucy/                   # Legacy text-processing helpers used by the brain
frontend/
  src/app/                # Angular wallet and token-management components
  public/assets/          # Angular-served wallet icons
  proxy.conf.json         # Local /api and /ws proxy to FastAPI
contracts/
  contracts/              # SeedToken and SeedTokenFactory
  scripts/                # Deployment and setup scripts
  test/                   # Hardhat tests
static/                   # Dashboard JavaScript, CSS, chart, and image assets
templates/                # Jinja dashboard and HTMX partials
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
ETH_RPC_URL=https://your-ethereum-rpc-provider/...
DB_URL=mysql+pymysql://...
FRONTEND_URL=http://localhost:4200
```

`PYTH_HERMES_API_KEY` is needed when Hermes returns HTTP 401. The backend batches Pyth requests and retries rate-limited HTTP 429 responses, but valid provider credentials are still required.

`ETH_RPC_URL` is required only when using the read-only Ethereum adapter. Keep the real endpoint in `.env`; `.env` files are ignored by Git. The adapter uses the existing `httpx` and `python-dotenv` dependencies.

## Read-Only Ethereum Data

The backend has a narrow, internal Ethereum read path:

```text
TokenMap symbol/address/chain
        ↓
backend.blockchain.token_intelligence
        ↓
backend.blockchain.ethereum
        ↓
ETH_RPC_URL → Ethereum JSON-RPC
```

`get_token_on_chain_intelligence(db, symbol)` resolves an active TokenMap row, verifies that it is an Ethereum mapping, and returns the mapped identity with the latest block and ERC-20 `name`, `symbol`, and `decimals`. The adapter supports `eth_blockNumber`, `eth_getBalance`, and `eth_call`. This is an internal Python capability; it is not exposed as an HTTP endpoint or Lucy tool.

Native ETH has no ERC-20 contract address, so the metadata lookup reports that case instead of inventing an address. The token seeder prefers CoinGecko's canonical `ethereum` identity and clears a stale contract address when refreshing native ETH. Wrapped Ether (WETH) is a separate ERC-20 token and should be represented by its own TokenMap entry.

To run the deterministic blockchain and token mapping tests from the repository root:

```bash
python3 -m unittest \
  backend.test_token_identity \
  backend.blockchain.test_ethereum \
  backend.blockchain.test_token_intelligence -v
```

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

Open [http://localhost:4200](http://localhost:4200) for the complete Angular application. Angular proxies `/api` and `/ws` requests to FastAPI on port 8000.

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

The Hardhat suite may require its existing ESM test imports to be updated before it passes.

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

Ethereum blockchain reads are not part of the HTTP API or Lucy's available tools yet.
