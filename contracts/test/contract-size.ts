import { expect } from "chai";
import { network } from "hardhat";
import { Web3 } from 'web3';

const web3 = new Web3('https://rpc.sepolia.org');
const { ethers } = await network.create();

const maxContractSize = 24*1024;

const abi = require("../artifacts/contracts/SeedToken.sol/SeedToken.json").abi;
const bytecode = require("../artifacts/contracts/SeedToken.sol/SeedToken.json").bytecode;
 
describe("Compiled Smart Contracts Size Test", function () {
    it("Should deploy the SeedToken contract", async function () {
        const SeedToken = await ethers.getContractFactory("SeedToken");
        const SeedToken_ = new web3.eth.Contract(abi);
 
        const [deployer] = await ethers.getSigners();
        const [deployer_] = await web3.eth.getAccounts();
 
        const seedToken = await SeedToken.deploy(deployer.address, "Seed Token", "SEED");
        const deployment = SeedToken_.deploy({
            data: bytecode,
            arguments: [deployer_, "Seed Token", "SEED"]
        });
 
        await seedToken.waitForDeployment();
        const receipt = await deployment.send({
            from: deployer_
        });
 
        const deployedAddress = await seedToken.getAddress();
        const deployedAddress_ = receipt.options.address;
 
        expect(deployedAddress).to.exist;
        expect(deployedAddress_).to.exist;
 
        const deployedCode = await seedToken.getDeployedCode();
        const deployedCode_ = deployedAddress_ ? await web3.eth.getCode(deployedAddress_) : null;
 
        //- 2 to remove the leading 0x, /2 because 2 hexadecimal ciphers = 1 byte
        const size = deployedCode ? (deployedCode.length - 2)/2 : 0;
        const size_ = deployedCode_ ? (deployedCode_.length - 2)/2 : 0;
 
        console.log('    SeedToken contract size: ' + size + ' bytes');
        console.log('    SeedToken contract size: ' + size_ + ' bytes');
 
        expect(size <= maxContractSize).to.be.true;
        expect(size_ <= maxContractSize).to.be.true;
    });
});