/* eslint-disable no-undef */
const hre = require("hardhat");

async function main() {
  const Verifier = await hre.ethers.getContractFactory(
    "contracts/UserTrustScoreLevelVerifier.sol:Groth16Verifier"
  );
  const verifier = await Verifier.deploy();
  await verifier.waitForDeployment();
  const verifierAddr = (await verifier.getAddress?.()) ?? verifier.target;
  console.log("Verifier deployed:", verifierAddr);

  const ZKAccess = await hre.ethers.getContractFactory("DataUserZKAccess");
  const zk = await ZKAccess.deploy(verifierAddr);
  await zk.waitForDeployment();
  const zkAddr = (await zk.getAddress?.()) ?? zk.target;
  console.log("DataUserZKAccess deployed:", zkAddr);
}

main().catch((e) => { console.error(e); process.exit(1); });