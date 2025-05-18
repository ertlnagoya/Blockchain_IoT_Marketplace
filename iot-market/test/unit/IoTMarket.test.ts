import { ethers, network } from "hardhat";
import "@nomicfoundation/hardhat-ethers";
import { assert } from "chai";
import { loadFixture } from "@nomicfoundation/hardhat-toolbox/network-helpers";
import { developmentChains } from "../../helper-hardhat-config";

const deployFixture = async () => {
  const [marketOwner, iotOwner, buyer, deniedBuyer] = await ethers.getSigners();

  const pubKeyFactory = await ethers.getContractFactory("PubKey", marketOwner);
  const pubKey = await pubKeyFactory.deploy();

  const IotMarketFactory = await ethers.getContractFactory(
    "IoTMarket",
    marketOwner
  );
  const IoTMarket = await IotMarketFactory.deploy();
  return { marketOwner, iotOwner, buyer, pubKey, IoTMarket, deniedBuyer };
};

const merchandisesFixture = async () => {
  const { marketOwner, iotOwner, buyer, pubKey, IoTMarket, deniedBuyer } =
    await loadFixture(deployFixture);

  const merchandiseFacotry = await ethers.getContractFactory(
    "Merchandise",
    iotOwner
  );
  const merchandises = [];
  for (let i = 0; i < 5; i++) {
    const merchandise = await merchandiseFacotry.deploy(
      ethers.parseEther("0.01"),
      ethers.encodeBytes32String("test"),
      pubKey,
      [deniedBuyer],
      ["fileType", "dataSize"],
      ["mp4", "100MB"]
    );
    merchandises.push(merchandise);
    await IoTMarket.registerMerchandise(merchandise);
  }
  console.log(merchandises.length);
  return { marketOwner, iotOwner, buyer, IoTMarket, pubKey, merchandises };
};

!developmentChains.includes(network.name)
  ? describe.skip
  : describe("IoTMarket", () => {
      describe("Deployment", () => {
        it("There are no Merchandises", async () => {
          const { IoTMarket } = await loadFixture(deployFixture);
          const response = await IoTMarket.getMerchandises();
          assert.isEmpty(response);
        });
      });
      describe("Deploy Merchandiseis", () => {
        it("There are 5 Merchandises", async () => {
          const { IoTMarket } = await loadFixture(merchandisesFixture);
          const response = await IoTMarket.getMerchandises();
          assert.lengthOf(response, 5);
        });
        it("Every Merchandise has correct owner", async () => {
          const { IoTMarket, iotOwner, merchandises } = await loadFixture(
            merchandisesFixture
          );
          for (const merchandise of merchandises) {
            const owner = await merchandise.getOwner();
            assert.equal(iotOwner.address, owner);
          }
        });
      });
    });
