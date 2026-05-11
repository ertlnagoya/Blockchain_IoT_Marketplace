import { ethers } from "ethers";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ── Config ────────────────────────────────────────────────────────────────────
const MNEMONIC =
  "test test test test test test test test test test test junk";

const ACCOUNT_COUNT = 5001; // deployer(1) + buyers(5000)
const HD_PATH = "m/44'/60'/0'/0"; // standard Ethereum derivation path


console.log(`Deriving ${ACCOUNT_COUNT} accounts from Hardhat default mnemonic...`);
console.log(`Mnemonic: "${MNEMONIC}"`);
console.log(`HD path:  ${HD_PATH}/index\n`);

const wallet = ethers.HDNodeWallet.fromMnemonic(
  ethers.Mnemonic.fromPhrase(MNEMONIC),
  HD_PATH
);

const accounts = [];

for (let i = 0; i < ACCOUNT_COUNT; i++) {
  const child = wallet.deriveChild(i);
  accounts.push({
    index: i,
    address: child.address,
    privateKey: child.privateKey,
  });

  if (i % 500 === 0) {
    process.stdout.write(`  Derived ${i}/${ACCOUNT_COUNT}...\r`);
  }
}

console.log(`  Derived ${ACCOUNT_COUNT}/${ACCOUNT_COUNT} ✅          `);

// Write accounts.json
const outPath = path.join(__dirname, "accounts.json");
fs.writeFileSync(outPath, JSON.stringify({ accounts }, null, 2));
console.log(`\nSaved: ${outPath}`);
console.log(`  Account[0] deployer:  ${accounts[0].address}`);
console.log(`  Account[1] buyer #1:  ${accounts[1].address}`);
console.log(`  Account[5000] buyer #5000: ${accounts[5000].address}`);

// Also write a separate addresses-only file (for genesis.json)
const addressesPath = path.join(__dirname, "addresses.txt");
fs.writeFileSync(addressesPath, accounts.map((a) => a.address).join("\n") + "\n");
console.log(`Saved addresses only: ${addressesPath}`);

console.log("\nDone! Next step: run gen_genesis.mjs to create genesis.json");
