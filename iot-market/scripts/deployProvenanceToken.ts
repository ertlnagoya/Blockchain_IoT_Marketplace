import { ethers } from "hardhat";

// Stage P (C2PA provenance) P2: deploy the ProvenanceToken. The deployer
// (Hardhat account #0) is the only minter; the publisher mints through
// that unlocked account via PROVENANCE_RPC_URL.
const main = async () => {
  const [minter] = await ethers.getSigners();
  const token = await ethers.deployContract("ProvenanceToken", minter);
  await token.waitForDeployment();
  console.log(`Contract "ProvenanceToken" with ${await token.getAddress()} deployed`);
  console.log(`minter: ${minter.address}`);
};

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
