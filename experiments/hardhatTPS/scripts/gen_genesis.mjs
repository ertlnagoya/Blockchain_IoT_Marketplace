/**
 * Create a Geth --dev compatible genesis.json that:
 *  Pre-funds all 5001 accounts with 10,000 ETH each
 *  Uses chainId 1337 (matches Hardhat default)
 *  Sets gasLimit high enough to avoid throttling
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ── Load accounts
const accountsPath = path.join(__dirname, "accounts.json");
if (!fs.existsSync(accountsPath)) {
  console.error("accounts.json not found. Run gen_accounts.mjs first.");
  process.exit(1);
}

const { accounts } = JSON.parse(fs.readFileSync(accountsPath, "utf-8"));
console.log(`Loaded ${accounts.length} accounts`);


const TEN_THOUSAND_ETH_HEX = "0x" + (10000n * 10n ** 18n).toString(16);

const alloc = {};
for (const { address } of accounts) {
  // Remove leading "0x" for genesis alloc keys
  alloc[address.toLowerCase()] = {
    balance: TEN_THOUSAND_ETH_HEX,
  };
}

console.log(`Pre-funded ${Object.keys(alloc).length} accounts with 10,000 ETH each`);


// Geth --dev ignores this genesis and uses its own internal dev genesis.
// gasLimit=0x1C9C380 = 30,000,000
const genesis = {
  config: {
    chainId: 1337,
    homesteadBlock: 0,
    eip150Block: 0,
    eip155Block: 0,
    eip158Block: 0,
    byzantiumBlock: 0,
    constantinopleBlock: 0,
    petersburgBlock: 0,
    istanbulBlock: 0,
    berlinBlock: 0,
    londonBlock: 0,
  },
  difficulty: "0x1",
  gasLimit: "0x1C9C380",
  alloc,
};

// ── Write output
const outDir = path.join(__dirname, "..", "geth-setup");
fs.mkdirSync(outDir, { recursive: true });

const outPath = path.join(outDir, "genesis.json");
fs.writeFileSync(outPath, JSON.stringify(genesis, null, 2));

console.log(`\nSaved: ${outPath}`);
console.log(`  chainId:  ${genesis.config.chainId}`);
console.log(`  gasLimit: ${parseInt(genesis.gasLimit, 16).toLocaleString()} gas`);
console.log(`  accounts: ${Object.keys(alloc).length}`);
console.log("\nDone! Next step: run start_geth_dev.sh to launch Geth --dev node");
