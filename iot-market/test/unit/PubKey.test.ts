import { ethers, network } from "hardhat";
import "@nomicfoundation/hardhat-ethers";
import { assert, expect } from "chai";
import { loadFixture } from "@nomicfoundation/hardhat-toolbox/network-helpers";
import { developmentChains } from "../../helper-hardhat-config";

const PUB_KEY = `{"n":"1ybSJguycYonJ3JJo+u1MwF2h93zf3zuwSNKQbrrY7YMarsdnyHPshx9C26gGthrONqZnnz4kF9V5N4GC3UPIbNGBdeEJX/Hp+McGRUPgS/zTXvVZYo1oxOVzCaARv055BdcweCHaWzO0U+lwtTvR8588ezD/xcvg3tXrnXeDRZ4a0Hmgul/9IF8t92gEiTCFFDZyiWJhOPMSAdYhHjw0k47B337oiGUfr3YcAQmrrlZO78U+44vHkd2CxE4OLfH0yss+GHZYa1slKriQlivj2bBwESmNO6BkqUa52Tes0VFxRr7F4lKLvgx5skN5kzACsga2HaheXjHJqWx5tx9hw==","e":"65537"}`;

const deployFixture = async () => {
  const [marketOwner, iotOwner, buyer] = await ethers.getSigners();
  const pubKeyFactory = await ethers.getContractFactory("PubKey", marketOwner);
  const pubKey = await pubKeyFactory.deploy();
  return { marketOwner, iotOwner, buyer, pubKey };
};
!developmentChains.includes(network.name)
  ? describe.skip
  : describe("PubKey", () => {
      describe("Deployment", () => {
        it("There is no Pubkeys", () => async () => {
          const { buyer, pubKey } = await loadFixture(deployFixture);
          await expect(
            pubKey.connect(buyer).getPubKey(buyer)
          ).to.be.revertedWithCustomError(pubKey, "PubKey__NotRegistered");
        });
      });
      describe("Register PubKey", () => {
        it("Valid PubKey can be registerd", async () => {
          const { buyer, pubKey } = await loadFixture(deployFixture);
          await pubKey.connect(buyer).registerKey(PUB_KEY);

          const key = await pubKey.connect(buyer).getPubKey(buyer);
          assert.equal(PUB_KEY, key);
        });

        it("Invalid PubKey String will be reverted", async () => {
          const { buyer, pubKey } = await loadFixture(deployFixture);
          const invalidKey = `Hello, this is not Key`;
          await expect(
            pubKey.connect(buyer).registerKey(invalidKey)
          ).to.be.revertedWithCustomError(pubKey, "PubKey__InvalidPubKey");
        });
      });
    });
