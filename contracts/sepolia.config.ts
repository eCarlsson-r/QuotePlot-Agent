import hardhatToolboxMochaEthersPlugin from "@nomicfoundation/hardhat-toolbox-mocha-ethers";
import { createRequire } from "node:module";
import { defineConfig } from "hardhat/config";

const require = createRequire(import.meta.url);
const { infuraApiKey, account1PrivateKey, account2PrivateKey, account3PrivateKey, account4PrivateKey, account5PrivateKey } = require("./infura.json") as {
  infuraApiKey: string;
  account1PrivateKey: string;
  account2PrivateKey: string;
  account3PrivateKey: string;
  account4PrivateKey: string;
  account5PrivateKey: string;
};

export default defineConfig({
  plugins: [hardhatToolboxMochaEthersPlugin],
  solidity: {
    version: "0.8.28",
    settings: {
      optimizer: {
        enabled: true,
        runs: 1000
      }
    }
  },
  networks: {
    sepolia: {
      type: "http",
      url: `https://sepolia.infura.io/v3/${infuraApiKey}`,
      accounts: [account1PrivateKey, account2PrivateKey, account3PrivateKey, account4PrivateKey, account5PrivateKey]
    }
  }
});