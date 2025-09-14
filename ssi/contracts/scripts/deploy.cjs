const hre = require("hardhat");

async function main() {
  const [deployer, other] = await hre.ethers.getSigners();
  const Verifier = await hre.ethers.getContractFactory("DataUserVerifier");
  // 用第二个metamask账户部署
  const verifier = await Verifier.connect(other).deploy();
  await verifier.waitForDeployment();
  console.log("✅ Contract deployed at:", verifier.target);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});