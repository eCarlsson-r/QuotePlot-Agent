import hardhatToolboxMochaEthersPlugin from "@nomicfoundation/hardhat-toolbox-mocha-ethers";
import { defineConfig } from "hardhat/config";
import { definePlugin } from "hardhat/plugins";
import { Web3, Web3Context } from "web3";

declare module "hardhat/types/hre" {
  interface HardhatRuntimeEnvironment {
    Web3: typeof Web3;
    Web3Context: typeof Web3Context;
    web3: Web3;
    web3Context: Web3Context;
  }
}

const web3Plugin = definePlugin({
  id: "web3",
  hookHandlers: {
    hre: async () => ({
      default: async () => ({
        created: async (_context, hre) => {
          const networkConnection = await hre.network.connect();
          const provider = networkConnection.provider;
          hre.Web3 = Web3;
          hre.Web3Context = Web3Context;
          hre.web3 = new Web3(provider);
          hre.web3Context = new Web3Context({
            provider,
            config: {
              contractDataInputFill: "data",
            },
          });
        },
      }),
    }),
  },
});

export default defineConfig({
  plugins: [hardhatToolboxMochaEthersPlugin, web3Plugin],
  solidity: {
    version: "0.8.28",
    settings: {
      optimizer: {
        enabled: true,
        runs: 100,
      },
    }
  },
  networks: {
    hardhat: {
      type: "edr-simulated",
      mining: {
        auto: true,
        interval: [11000, 13000]
      }
    }
  },
});