import { ethers } from "hardhat";
import "dotenv/config";

const main = async () => {
  const [marketOwner, iotOwner, buyer, deniedBuyer] = await ethers.getSigners();
  const pubKey = await ethers.deployContract("PubKey");
  await pubKey.waitForDeployment();
  console.log(`Contract "PubKey" with ${await pubKey.getAddress()} deployed`);

  let merchandise = await ethers.deployContract(
    "Merchandise",
    [
      ethers.parseEther("0.01"),
      ethers.encodeBytes32String("test"),
      pubKey,
      [deniedBuyer],
      ["fileType", "dataSize"],
      ["mp4", "100MB"],
    ],
    iotOwner
  );
  await merchandise.waitForDeployment();
  console.log(
    `Contract "Merchandise" with ${await merchandise.getAddress()} deployed`
  );
};

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
