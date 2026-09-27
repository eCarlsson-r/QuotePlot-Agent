# QuotePlot Agent contracts

This Hardhat 3 project contains the `SeedToken` ERC-20 and `SeedTokenFactory` used by the Angular token-management UI.

## Local validation

Tests run on Hardhat's local simulated chain. They do not contact a public testnet or use external private keys.

```bash
npm ci
npx hardhat compile
npx hardhat test
```

The tests cover token metadata, ownership, mint permissions, factory token creation, and the EVM runtime bytecode size limit.

## BSC Testnet deployment

Use a testnet-funded deployer key and keep it on the deployment machine only:

```bash
export BSC_TESTNET_RPC_URL="https://bsc-testnet-dataseed.bnbchain.org"
export BSC_TESTNET_PRIVATE_KEY="0x..."
npx hardhat run scripts/deploy.ts --network bscTestnet
```

BSC Testnet uses chain ID `97` and native test currency `tBNB`. The script deploys `SeedTokenFactory`, creates a `Seed Token (SEED)`, and prints the factory/token addresses and BscScan testnet link. The factory address is required as Vercel `QUOTE_PLOT_FACTORY_ADDRESS`; set `QUOTE_PLOT_NETWORK=bscTestnet` for the frontend build. This path does not use Sepolia ENS. See [BNB Chain wallet configuration](https://docs.bnbchain.org/bnb-smart-chain/developers/wallet-configuration/).

## Sepolia deployment

Set deployment values in the shell; never commit the private key:

```bash
export SEPOLIA_RPC_URL="https://your-sepolia-rpc-endpoint"
export SEPOLIA_PRIVATE_KEY="0x..."
npx hardhat run scripts/deploy.ts --network sepolia
```

`SEPOLIA_RPC_URL` is optional because the config has a public Sepolia RPC fallback. A funded account supplied by `SEPOLIA_PRIVATE_KEY` is required to deploy. The script deploys the factory, creates a `Seed Token (SEED)`, and prints both addresses once the transactions are mined.

The Angular service looks up the factory at the Sepolia ENS name `seed-token-factory.eth`, unless `QUOTE_PLOT_FACTORY_ADDRESS` is configured. Configure that name to resolve to the deployed factory before using token management. A connected wallet should be on Sepolia (chain ID `11155111`). No deployment is performed by tests, and no live deployment address is checked in here.
