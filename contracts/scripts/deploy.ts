import { network } from "hardhat";

const { ethers } = await network.create();

async function main() {
  const [deployer] = await ethers.getSigners();
  if (!deployer) {
    throw new Error("No deployer account is configured for the selected network.");
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
  console.log(`Network: ${await ethers.provider.getNetwork().then(({ name, chainId }) => `${name} (${chainId})`)}`);
  console.log("Configure seed-token-factory.eth to resolve to the factory address before using the Angular token-management UI.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
