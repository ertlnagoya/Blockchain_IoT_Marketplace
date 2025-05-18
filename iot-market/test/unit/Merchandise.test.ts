import { ethers, network } from "hardhat";
import { developmentChains } from "../../helper-hardhat-config";
import { loadFixture } from "@nomicfoundation/hardhat-toolbox/network-helpers";
import { assert, expect } from "chai";

const PUB_KEY = `{"n":"1ybSJguycYonJ3JJo+u1MwF2h93zf3zuwSNKQbrrY7YMarsdnyHPshx9C26gGthrONqZnnz4kF9V5N4GC3UPIbNGBdeEJX/Hp+McGRUPgS/zTXvVZYo1oxOVzCaARv055BdcweCHaWzO0U+lwtTvR8588ezD/xcvg3tXrnXeDRZ4a0Hmgul/9IF8t92gEiTCFFDZyiWJhOPMSAdYhHjw0k47B337oiGUfr3YcAQmrrlZO78U+44vHkd2CxE4OLfH0yss+GHZYa1slKriQlivj2bBwESmNO6BkqUa52Tes0VFxRr7F4lKLvgx5skN5kzACsga2HaheXjHJqWx5tx9hw==","e":"65537"}`;

const MerchandiseState = {
  SALE: 0n,
  IN_PROGRESS: 1n,
  BANNED: 2n,
};

type MerchandiseState =
  (typeof MerchandiseState)[keyof typeof MerchandiseState];

const deployPubKeyFixture = async () => {
  const [marketOwner, _, buyer] = await ethers.getSigners();
  const pubKeyFactory = await ethers.getContractFactory("PubKey", marketOwner);
  const pubKey = await pubKeyFactory.deploy();

  await pubKey.connect(buyer).registerKey(PUB_KEY);

  return { pubKey };
};

const deployFixture = async () => {
  const [marketOwner, iotOwner, buyer, deniedBuyer] = await ethers.getSigners();
  const { pubKey } = await loadFixture(deployPubKeyFixture);
  const merchandiseFactory = await ethers.getContractFactory(
    "Merchandise",
    iotOwner
  );
  const merchandise = await merchandiseFactory.deploy(
    ethers.parseEther("0.01"),
    ethers.encodeBytes32String("test"),
    pubKey,
    [deniedBuyer],
    ["fileType", "dataSize"],
    ["mp4", "100MB"]
  );
  return {
    marketOwner,
    iotOwner,
    buyer,
    merchandise,
    pubKey,
    deniedBuyer,
  };
};

const purchaseFixture = async () => {
  const { marketOwner, iotOwner, buyer, merchandise } = await loadFixture(
    deployFixture
  );
  await merchandise.connect(buyer).purchase({
    value: ethers.parseEther("0.01"),
  });
  return { marketOwner, iotOwner, buyer, merchandise };
};

const verifysuccessFixture = async () => {
  const { marketOwner, iotOwner, buyer, merchandise } = await loadFixture(
    purchaseFixture
  );
  await merchandise.connect(buyer).verify(ethers.encodeBytes32String("test"));
  return { marketOwner, iotOwner, buyer, merchandise };
};

const verifyfailFixture = async () => {
  const { marketOwner, iotOwner, buyer, merchandise } = await loadFixture(
    purchaseFixture
  );
  for (let i = 0; i < 10; i++) {
    await merchandise
      .connect(buyer)
      .verify(ethers.encodeBytes32String("wrong data"));
  }
  return { marketOwner, iotOwner, buyer, merchandise };
};

!developmentChains.includes(network.name)
  ? describe.skip
  : describe("Merchandise", () => {
      describe("Deployment", () => {
        it("Merchandise has const Retry limit(10)", async () => {
          const { merchandise } = await loadFixture(deployFixture);
          const response = await merchandise.getRetryLimit();
          assert.equal(response, 10n);
        });

        it("Merchandise has right owner", async () => {
          const { iotOwner, merchandise } = await loadFixture(deployFixture);
          const response = await merchandise.getOwner();
          assert.equal(response, iotOwner.address);
        });

        it("Merchandise has DataHash", async () => {
          const { merchandise } = await loadFixture(deployFixture);
          const response = await merchandise.getDataHash();
          assert.equal(response, ethers.encodeBytes32String("test"));
        });

        it("Merchandise has initial price", async () => {
          const { merchandise } = await loadFixture(deployFixture);
          const response = await merchandise.getPrice();
          assert.equal(response, ethers.parseEther("0.01"));
        });

        it("Merchandise has initial state as SALE", async () => {
          const { merchandise } = await loadFixture(deployFixture);
          const response = await merchandise.getState();
          assert.equal(response, 0n);
        });

        it("Merchandise has trial count as 0", async () => {
          const { merchandise } = await loadFixture(deployFixture);
          const response = await merchandise.getTrialCount();
          assert.equal(response, 0n);
        });

        it("Merchandise has no progress buyers", async () => {
          const { merchandise } = await loadFixture(deployFixture);
          const response = await merchandise.getProgressBuyer();
          assert.equal(response, ethers.ZeroAddress);
        });

        it("Merchandise has no confirmed buyers", async () => {
          const { marketOwner, iotOwner, buyer, merchandise } =
            await loadFixture(deployFixture);
          const user1 = await merchandise.isConfirmedBuyer(buyer);
          const user2 = await merchandise.isConfirmedBuyer(iotOwner);
          const user3 = await merchandise.isConfirmedBuyer(marketOwner);
          for (const user of [user1, user2, user3]) {
            assert.isFalse(user);
          }
        });

        it("Merchandise has related PubKey Contract", async () => {
          const { merchandise, pubKey } = await loadFixture(deployFixture);
          const pubKeyAddress = await merchandise.getPubKeyAddress();
          assert.equal(await pubKey.getAddress(), pubKeyAddress);
        });

        it("Failed if someone try to confirm", async () => {
          const { buyer, merchandise } = await loadFixture(deployFixture);
          await expect(
            merchandise
              .connect(buyer)
              .verify(ethers.encodeBytes32String("test"))
          ).to.be.revertedWithCustomError(
            merchandise,
            "Merchandise__NotInProgress"
          );
        });
      });

      describe("After deployment", () => {
        it("You can get Additional Info", async () => {
          const { merchandise } = await loadFixture(deployFixture);
          const response = await merchandise.getAllAdditionalInfo();
          const expected: [string, string] = ["fileType", "mp4"];
          const expected2: [string, string] = ["dataSize", "100MB"];
          assert.deepEqual(response[0], expected);
          assert.deepEqual(response[1], expected2);
        });
      });

      describe("Purchase", () => {
        it("Fails if buyer don't send enough money", async () => {
          const { buyer, merchandise } = await loadFixture(deployFixture);
          await expect(
            merchandise.connect(buyer).purchase()
          ).to.be.revertedWithCustomError(
            merchandise,
            "Merchandise__NotEnoughETH"
          );
        });

        it("Fails if buyer don't have PubKey", async () => {
          const { iotOwner, merchandise, pubKey } = await loadFixture(
            deployFixture
          );
          await expect(
            merchandise.connect(iotOwner).purchase({
              value: ethers.parseEther("0.01"),
            })
          ).to.be.revertedWithCustomError(pubKey, "PubKey__NotRegistered");
        });

        it("Fails if denied buyer try to purchase", async () => {
          const { merchandise, deniedBuyer } = await loadFixture(deployFixture);
          await expect(
            merchandise.connect(deniedBuyer).purchase({
              value: ethers.parseEther("0.01"),
            })
          ).to.be.revertedWithCustomError(
            merchandise,
            "Merchandise__AccessDenied"
          );
        });

        it("Buyer can purchase merchandise", async () => {
          const { iotOwner, buyer, merchandise } = await loadFixture(
            deployFixture
          );
          await expect(
            merchandise.connect(buyer).purchase({
              value: ethers.parseEther("0.01"),
            })
          )
            .to.emit(merchandise, "Purchase")
            .withArgs(iotOwner, buyer, PUB_KEY);
          const buyerAddress = await merchandise.getProgressBuyer();
          const state = await merchandise.getState();
          assert.equal(buyerAddress, buyer.address);
          assert.equal(state, MerchandiseState.IN_PROGRESS);
        });
      });

      describe("At state IN_PROGRESS", () => {
        it("No other user can purchase", async () => {
          const { iotOwner, merchandise } = await loadFixture(purchaseFixture);
          await expect(
            merchandise.connect(iotOwner).purchase({
              value: ethers.parseEther("0.01"),
            })
          ).to.be.revertedWithCustomError(
            merchandise,
            "Merchandise__NotForSale"
          );
        });

        it("Owner can emit event Upload", async () => {
          const { iotOwner, buyer, merchandise } = await loadFixture(
            purchaseFixture
          );
          await expect(merchandise.connect(iotOwner).emitUpload("test"))
            .to.emit(merchandise, "Upload")
            .withArgs(iotOwner, buyer, "test");
        });

        it("Failed if someone without buyer try to confirm", async () => {
          const { iotOwner, merchandise } = await loadFixture(purchaseFixture);
          await expect(
            merchandise
              .connect(iotOwner)
              .verify(ethers.encodeBytes32String("test"))
          ).to.be.revertedWithCustomError(merchandise, "Merchandise__NotBuyer");
        });

        it("Failed if buyer try to confirm with wrong data", async () => {
          const { iotOwner, buyer, merchandise } = await loadFixture(
            purchaseFixture
          );
          const wrongHash = ethers.encodeBytes32String("wrong data");
          await expect(merchandise.connect(buyer).verify(wrongHash))
            .to.emit(merchandise, "Verify")
            .withArgs(iotOwner, buyer, false);
        });

        it("Buyer can confirm data", async () => {
          const { iotOwner, buyer, merchandise } = await loadFixture(
            purchaseFixture
          );
          const wrongHash = ethers.encodeBytes32String("test");
          await expect(merchandise.connect(buyer).verify(wrongHash))
            .to.emit(merchandise, "Verify")
            .withArgs(iotOwner, buyer, true);
        });
      });

      describe("After verify fail", () => {
        it("Merchandise state is changed to BANNED", async () => {
          const { merchandise } = await loadFixture(verifyfailFixture);
          const response = await merchandise.getState();
          assert.equal(response, MerchandiseState.BANNED);
        });

        it("Failed if iotOwner try to withdraw", async () => {
          const { iotOwner, merchandise } = await loadFixture(
            verifyfailFixture
          );
          await expect(
            merchandise.connect(iotOwner).withdraw()
          ).to.be.revertedWithCustomError(merchandise, "Merchandise__Bunned");
        });
      });

      describe("After verify success", () => {
        it("Merchandise state is changed to SALE", async () => {
          const { merchandise } = await loadFixture(verifysuccessFixture);
          const response = await merchandise.getState();
          assert.equal(response, MerchandiseState.SALE);
        });

        it("Failed if someone without iotOwner try to withdraw", async () => {
          const { buyer, merchandise } = await loadFixture(purchaseFixture);
          await expect(
            merchandise.connect(buyer).withdraw()
          ).to.be.revertedWithCustomError(merchandise, "Merchandise__NotOwner");
        });

        it("IotOwner can withdraw money from Merchandise", async () => {
          const { iotOwner, merchandise } = await loadFixture(
            verifysuccessFixture
          );
          const iotOwnerBeforeBalance = await ethers.provider.getBalance(
            iotOwner
          );
          const merchandiseBeforeBalance = await ethers.provider.getBalance(
            merchandise
          );
          const response = await merchandise.connect(iotOwner).withdraw();

          const receipt = await response.wait();
          const gasUsed = receipt?.gasPrice! * receipt?.gasUsed!;

          const iotOwnerAfterBalance = await ethers.provider.getBalance(
            iotOwner
          );
          const merchandiseAfterBalance = await ethers.provider.getBalance(
            merchandise
          );

          assert.equal(merchandiseAfterBalance, 0n);
          assert.equal(
            iotOwnerAfterBalance + gasUsed,
            iotOwnerBeforeBalance + merchandiseBeforeBalance
          );
        });
      });
    });
