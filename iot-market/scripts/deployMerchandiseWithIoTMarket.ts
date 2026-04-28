import { ethers } from "hardhat";
import "dotenv/config";

// Stage 6 / case B: each Merchandise advertises its dataset_id in
// additionalInfo so the bridge (and iot-market-ui) can read the dataset
// straight off chain instead of relying on a hardcoded default.
const metadatas = [
  { fileType: "mp4", dataSize: "100MB", datasetId: "home/env/temperature" },
  { fileType: "jpg", dataSize: "10MB", datasetId: "home/env/temperature" },
  { fileType: "txt", dataSize: "1MB", datasetId: "home/env/humidity" },
  { fileType: "mp4", dataSize: "16MB", datasetId: "home/env/temperature" },
  { fileType: "png", dataSize: "5MB", datasetId: "home/env/flood_risk_high" },
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
      ["fileType", "dataSize", "dataset_id"],
      [metadatas[i].fileType, metadatas[i].dataSize, metadatas[i].datasetId],
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
