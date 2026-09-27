import { network } from "hardhat";

const { ethers } = await network.create();

async function main() {
  const [deployer] = await ethers.getSigners();
  if (!deployer) {
    throw new Error("No deployer account is configured for the selected network.");
  }

  const { chainId, name } = await ethers.provider.getNetwork();
  if (![97n, 11155111n].includes(chainId)) {
    throw new Error(`Refusing deployment to unsupported chain ${name} (${chainId}).`);
  }

  console.log(`Deploying SeedTokenFactory from ${deployer.address}`);
  const factory = await (await ethers.getContractFactory("SeedTokenFactory")).deploy();
  await factory.waitForDeployment();
  const factoryAddress = await factory.getAddress();

  const transaction = await factory.create("Seed Token", "SEED");
  const receipt = await transaction.wait();
  if (!receipt) throw new Error("Factory token creation transaction was not mined.");

  const tokenAddress = await factory.tokens(0);
  console.log(`SeedTokenFactory: ${factoryAddress}`);
  console.log(`Seed Token (SEED): ${tokenAddress}`);
  console.log(`Network: ${name} (${chainId})`);
  console.log(`Explorer: ${chainId === 97n ? "https://testnet.bscscan.com/address/" : "https://sepolia.etherscan.io/address/"}${factoryAddress}`);
  if (chainId === 11155111n) {
    console.log("Configure seed-token-factory.eth to resolve to the factory address before using the Angular token-management UI.");
  } else {
    console.log("Set QUOTE_PLOT_NETWORK=bscTestnet and QUOTE_PLOT_FACTORY_ADDRESS to this factory address in the frontend deployment.");
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
