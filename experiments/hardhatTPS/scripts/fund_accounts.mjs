/**
 * fund_accounts.mjs
 *
 * Purpose:
 *   Geth --dev auto-creates a "dev" account with unlimited ETH.
 *   This script uses that dev account to fund all 5001 of our derived accounts with 100 ETH each so they can pay gas fees.
 */

import { ethers } from "ethers";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const RPC_URL = "http://127.0.0.1:8545";
const FUND_AMOUNT = ethers.parseEther("100"); // 100 ETH per account

// ── Load accounts
const accountsPath = path.join(__dirname, "accounts.json");
const { accounts } = JSON.parse(fs.readFileSync(accountsPath, "utf-8"));
console.log(`Loaded ${accounts.length} target accounts`);

// ── Connect to Geth
const provider = new ethers.JsonRpcProvider(RPC_URL);

// Check Geth is alive
let chainId;
try {
  const network = await provider.getNetwork();
  chainId = network.chainId;
  console.log(`Connected to Geth (chainId=${chainId})`);
} catch (e) {
  console.error("Cannot connect to Geth. Is it running?");
  console.error("   Run: ./scripts/start_geth_dev.sh");
  process.exit(1);
}

// ── Get Geth dev account (coinbase)
// Geth --dev creates a special dev account with unlimited ETH.
// It is typically the coinbase address.
const devAccounts = await provider.send("eth_accounts", []);
if (devAccounts.length === 0) {
  console.error("No accounts found in Geth. Is --dev mode enabled?");
  process.exit(1);
}

const devAddress = devAccounts[0]; // deployer
const devBalance = await provider.getBalance(devAddress);
console.log(`Dev account: ${devAddress}`);
console.log(`Dev balance: ${ethers.formatEther(devBalance)} ETH`);

if (devBalance < FUND_AMOUNT * BigInt(accounts.length)) {
  console.warn(" Dev account may not have enough ETH for all accounts");
  console.warn("   (Geth --dev uses a special unlimited account, this should be OK)");
}

// ── Helper: poll for receipt with generous timeout for Geth --dev batch mining
async function waitReceipt(txHash, maxRetries = 300, intervalMs = 500) {
  for (let i = 0; i < maxRetries; i++) {
    const receipt = await provider.send("eth_getTransactionReceipt", [txHash]);
    if (receipt && receipt.blockNumber) return receipt;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`Timeout waiting for receipt: ${txHash}`);
}

// fund accounts: send ALL txs first, then wait for all receipts
console.log(`\nFunding ${accounts.length} accounts with ${ethers.formatEther(FUND_AMOUNT)} ETH each...`);

let nonce = Number(await provider.send("eth_getTransactionCount", [devAddress, "latest"]));
const startTime = Date.now();
const SEND_BATCH = 200; // how many to send at once (RPC burst)

console.log(`Starting nonce: ${nonce}`);
console.log(`Sending all transactions...`);

// Phase 1: send all transactions in bursts of SEND_BATCH
const allHashes = [];
for (let i = 0; i < accounts.length; i += SEND_BATCH) {
  const batch = accounts.slice(i, i + SEND_BATCH);
  const hashes = await Promise.all(batch.map(({ address }, j) =>
    provider.send("eth_sendTransaction", [{
      from: devAddress,
      to: address,
      value: "0x" + FUND_AMOUNT.toString(16),
      gas: "0x5208",
      nonce: "0x" + (nonce + i + j).toString(16),// prevent nonce repetition
    }])
  ));
  allHashes.push(...hashes);
  process.stdout.write(`  Sent ${allHashes.length}/${accounts.length}\r`);
}

const sendElapsed = ((Date.now() - startTime) / 1000).toFixed(1);
console.log(`\nAll ${allHashes.length} txs sent in ${sendElapsed}s. Waiting for mining...`);

// Phase 2: wait for all receipts in batches to avoid overwhelming RPC
const WAIT_BATCH = 500;
for (let i = 0; i < allHashes.length; i += WAIT_BATCH) {
  const batch = allHashes.slice(i, i + WAIT_BATCH);
  await Promise.all(batch.map((hash) => waitReceipt(hash)));
  process.stdout.write(`  Confirmed ${Math.min(i + WAIT_BATCH, allHashes.length)}/${allHashes.length}\r`);
}

const totalElapsed = ((Date.now() - startTime) / 1000).toFixed(1);
console.log(`\n\n✅ All ${accounts.length} accounts funded! (${totalElapsed}s total)`);

// ── Verify a sample
const sample = [accounts[0], accounts[1], accounts[5000]];
console.log("\nBalance verification:");
for (const { index, address } of sample) {
  const bal = await provider.getBalance(address);
  console.log(`  accounts[${index}] ${address}: ${ethers.formatEther(bal)} ETH`);
}
