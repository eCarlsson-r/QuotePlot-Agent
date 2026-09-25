import { expect } from "chai";
import { network } from "hardhat";

const { ethers } = await network.create();

describe("Compiled contract deployment", function () {
  it("deploys the factory and creates a token on the local chain", async function () {
    const [owner] = await ethers.getSigners();
    const factory = await (await ethers.getContractFactory("SeedTokenFactory")).deploy();
    await factory.waitForDeployment();

    await expect(factory.create("Demo Token", "DEMO"))
      .to.emit(factory, "SeedTokenCreation");
    expect(await factory.getNumberOfTokens()).to.equal(1n);

    const tokenAddress = await factory.tokens(0);
    const token = await ethers.getContractAt("SeedToken", tokenAddress);
    expect(await token.owner()).to.equal(owner.address);
    expect(await token.name()).to.equal("Demo Token");
    expect(await token.symbol()).to.equal("DEMO");
  });

  it("keeps SeedToken runtime bytecode below the EVM contract size limit", async function () {
    const [owner] = await ethers.getSigners();
    const token = await (await ethers.getContractFactory("SeedToken")).deploy(
      owner.address,
      "Seed Token",
      "SEED",
    );
    await token.waitForDeployment();

    const code = await ethers.provider.getCode(await token.getAddress());
    const sizeInBytes = (code.length - 2) / 2;
    expect(sizeInBytes).to.be.greaterThan(0);
    expect(sizeInBytes).to.be.at.most(24 * 1024);
  });
});
