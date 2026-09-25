# QuotePlot Agent contracts

This Hardhat 3 project contains the `SeedToken` ERC-20 and `SeedTokenFactory` used by the Angular token-management UI.

## Local validation

Tests run on Hardhat's local simulated chain. They do not contact Sepolia and do not use external private keys.

```bash
npm ci
npx hardhat compile
npx hardhat test
```

The tests cover token metadata, ownership, mint permissions, factory token creation, and the EVM runtime bytecode size limit.

## Sepolia deployment

Set deployment values in the shell; never commit the private key:

```bash
export SEPOLIA_RPC_URL="https://your-sepolia-rpc-endpoint"
export SEPOLIA_PRIVATE_KEY="0x..."
npx hardhat run scripts/deploy.ts --network sepolia
```

`SEPOLIA_RPC_URL` is optional because the config has a public Sepolia RPC fallback. A funded account supplied by `SEPOLIA_PRIVATE_KEY` is required to deploy. The script deploys the factory, creates a `Seed Token (SEED)`, and prints both addresses once the transactions are mined.

The Angular service looks up the factory at the Sepolia ENS name `seed-token-factory.eth`. Configure that name to resolve to the deployed factory before using token management. A connected wallet should be on Sepolia (chain ID `11155111`). No deployment is performed by tests, and no live deployment address is checked in here.
