import { network, run } from "hardhat";
import { Contract } from "ethers";

export const verify = async (contract: Contract) => {
  if (network.config.chainId !== 31337 && process.env.ETHERSCAN_API_KEY) {
    console.log("network is not Hardhat: verify() will run");
    console.log(`wait for a moment for Etherscan gets the byte code`);
    await contract.deploymentTransaction()?.wait(5);
    console.log(`Verifying the contract on Etherscan...`);
    await run("verify:verify", {
      address: await contract.getAddress(),
      constructorArguments: [],
    })
      .then(() => {
        console.log(`Contract verified!`);
      })
      .catch((error: Error) => {
        console.log(`Error while running verify:verify: ${error.message}`);
      });
  }
};
