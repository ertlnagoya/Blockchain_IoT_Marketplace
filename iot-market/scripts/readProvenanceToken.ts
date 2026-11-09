import { ethers } from "hardhat";

// Stage P (C2PA provenance) P2: print what a ProvenanceToken anchors.
//   TOKEN_ADDRESS=0x... TOKEN_ID=1 npx hardhat run scripts/readProvenanceToken.ts --network localhost
const main = async () => {
  const address = process.env.TOKEN_ADDRESS;
  if (!address) throw new Error("set TOKEN_ADDRESS to the deployed ProvenanceToken");
  const tokenId = BigInt(process.env.TOKEN_ID ?? "1");
  const token = await ethers.getContractAt("ProvenanceToken", address);
  const p = await token.provenanceOf(tokenId);
  console.log(`token #${tokenId} owner ${await token.ownerOf(tokenId)}`);
  console.log(`manifestLabel ${p.manifestLabel}`);
  console.log(`assetSha256   ${p.assetSha256}`);
  console.log(`cid           ${p.cid || "(none)"}`);
  console.log(`sellerDid     ${p.sellerDid || "(none)"}`);
};

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
