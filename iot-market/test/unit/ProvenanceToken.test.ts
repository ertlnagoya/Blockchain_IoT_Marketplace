import { expect } from "chai";
import { ethers } from "hardhat";

describe("ProvenanceToken", () => {
  const label = "urn:c2pa:4f3037d8-edf8-40e9-b759-c86e7f88b945";
  const sha = "0x" + "ab".repeat(32);
  const cid = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi";
  const did = "did:jwk:seller";

  const deploy = async () => {
    const [minter, other] = await ethers.getSigners();
    const token = await ethers.deployContract("ProvenanceToken", minter);
    await token.waitForDeployment();
    return { token, minter, other };
  };

  it("mints token 1 to the given owner and records the provenance", async () => {
    const { token, minter } = await deploy();
    await expect(token.mint(minter.address, label, sha, cid, did))
      .to.emit(token, "ProvenanceAnchored")
      .withArgs(1n, sha, label, cid, did);
    expect(await token.ownerOf(1n)).to.equal(minter.address);
    const p = await token.provenanceOf(1n);
    expect(p.manifestLabel).to.equal(label);
    expect(p.assetSha256).to.equal(sha);
    expect(p.cid).to.equal(cid);
    expect(p.sellerDid).to.equal(did);
    expect(await token.tokenOfAsset(sha)).to.equal(1n);
  });

  it("returns JSON metadata as a data URI", async () => {
    const { token, minter } = await deploy();
    await token.mint(minter.address, label, sha, cid, did);
    const uri = await token.tokenURI(1n);
    expect(uri.startsWith("data:application/json;base64,")).to.equal(true);
    const json = JSON.parse(
      Buffer.from(uri.split(",")[1], "base64").toString("utf8")
    );
    expect(json).to.deep.equal({
      name: "IW3IP Provenance #1",
      manifestLabel: label,
      assetSha256: sha,
      cid,
      sellerDid: did,
    });
  });

  it("anchors an asset only once", async () => {
    const { token, minter } = await deploy();
    await token.mint(minter.address, label, sha, cid, did);
    await expect(
      token.mint(minter.address, label, sha, cid, did)
    ).to.be.revertedWithCustomError(token, "ProvenanceToken__AlreadyAnchored");
  });

  it("only lets the deployer mint", async () => {
    const { token, other } = await deploy();
    await expect(
      token.connect(other).mint(other.address, label, sha, cid, did)
    ).to.be.revertedWithCustomError(token, "ProvenanceToken__NotMinter");
  });

  it("rejects strings that would break the metadata JSON", async () => {
    const { token, minter } = await deploy();
    await expect(
      token.mint(minter.address, 'urn:"x', sha, cid, did)
    ).to.be.revertedWithCustomError(token, "ProvenanceToken__BadString");
  });

  it("has the selectors the publisher's chain client uses", async () => {
    const { token } = await deploy();
    expect(token.interface.getFunction("mint")!.selector).to.equal("0x04bcdede");
    expect(token.interface.getFunction("tokenOfAsset")!.selector).to.equal("0x160e475d");
  });
});
