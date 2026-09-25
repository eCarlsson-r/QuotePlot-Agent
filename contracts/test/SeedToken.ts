import { expect } from "chai";
import { network } from "hardhat";

const { ethers } = await network.create();

describe("SeedToken", function () {
  async function deployToken() {
    const [owner] = await ethers.getSigners();
    const token = await (await ethers.getContractFactory("SeedToken")).deploy(
      owner.address,
      "Seed Token",
      "SEED",
    );
    await token.waitForDeployment();
    return { token, owner };
  }

  it("sets the initial owner and ERC-20 metadata", async function () {
    const { token, owner } = await deployToken();
    expect(await token.owner()).to.equal(owner.address);
    expect(await token.name()).to.equal("Seed Token");
    expect(await token.symbol()).to.equal("SEED");
    expect(await token.decimals()).to.equal(18n);
  });

  it("lets only the owner mint the requested whole-token amount", async function () {
    const { token, owner } = await deployToken();
    const [, other] = await ethers.getSigners();

    await expect(token.mint(12345)).to.emit(token, "Transfer");
    expect(await token.totalSupply()).to.equal(12345n * 10n ** 18n);
    expect(await token.balanceOf(owner.address)).to.equal(12345n * 10n ** 18n);
    await expect(token.connect(other).mint(1)).to.be.revertedWithCustomError(token, "Unauthorized");
  });

  it("lets only the owner transfer ownership", async function () {
    const { token, owner: originalOwner } = await deployToken();
    const [, newOwner, other] = await ethers.getSigners();

    await expect(token.connect(newOwner).changeOwner(other.address)).to.be.revertedWithCustomError(token, "Unauthorized");
    await token.changeOwner(newOwner.address);
    expect(await token.owner()).to.equal(newOwner.address);
    await expect(token.mint(1)).to.be.revertedWithCustomError(token, "Unauthorized");
    await token.connect(newOwner).mint(1);
    expect(await token.balanceOf(newOwner.address)).to.equal(10n ** 18n);
    expect(originalOwner.address).not.to.equal(newOwner.address);
  });
});
