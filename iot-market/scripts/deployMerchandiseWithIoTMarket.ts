import { ethers } from "hardhat";
import "dotenv/config";

const metadatas = [
  { fileType: "mp4", dataSize: "100MB" },
  { fileType: "jpg", dataSize: "10MB" },
  { fileType: "txt", dataSize: "1MB" },
  { fileType: "mp4", dataSize: "16MB" },
  { fileType: "png", dataSize: "5MB" },
];

const main = async () => {
  const [marketOwner, iotOwner, buyer, deniedBuyer] = await ethers.getSigners();
  const pubKey = await ethers.deployContract("PubKey");
  await pubKey.waitForDeployment();
  console.log(`Contract "PubKey" with ${await pubKey.getAddress()} deployed`);

  const iotMarket = await ethers.deployContract("IoTMarket", [], marketOwner);
  await iotMarket.waitForDeployment();
  console.log(
    `Contract "IoTMarket" with ${await iotMarket.getAddress()} deployed`
  );

  for (let i = 0; i < 5; i++) {
    const merchandise = await ethers.deployContract("Merchandise", [
      ethers.parseEther("0.01"),
      await createDataHash("test"),
      pubKey,
      [deniedBuyer],
      ["fileType", "dataSize"],
      [metadatas[i].fileType, metadatas[i].dataSize],
    ]);

    await merchandise.waitForDeployment();
    console.log(
      `Contract "Merchandise" with ${await merchandise.getAddress()} deployed`
    );
    await iotMarket.registerMerchandise(merchandise);
    console.log(`Merchandise ${i} registered`);
  }
};

const createDataHash = async (data: string) => {
  const digestArrayBuffer = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(data)
  );
  const hashArray = new Uint8Array(digestArrayBuffer);
  const hash = Array.from(hashArray)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return "0x" + hash;
};

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
