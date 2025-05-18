import { ethers } from "hardhat";
import "dotenv/config";

const main = async () => {
  const [marketOwner, iotOwner, buyer] = await ethers.getSigners();
  let iotMarket = await ethers.deployContract("IoTMarket", [], marketOwner);
  await iotMarket.waitForDeployment();
  console.log(
    `Contract "IoTMarket" with ${await iotMarket.getAddress()} deployed`
  );
};

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
