/**
 * ============================================================
 *  Experiment 1: User Number vs GAS (Throughput)
 * ============================================================
 *
 *  Goal:
 *    With a fixed total number of transactions (T),
 *    increase the number of concurrent users (N) and
 *    measure the system throughput (TPS) by GAS consumption.
 *
 *  Method:
 *    - Deploy T Merchandise contracts (one per transaction)
 *    - N users each call purchase() on T/N different contracts
 *    - All N users submit their transactions concurrently via Promise.all()
 *
 *  Optimizations for large-scale (N=1000~5000):
 *    - Larger batch sizes for deployment & PubKey registration
 *    - Progress reporting with ETA
 *    - T scales with N to ensure each user has at least 1 tx
 */

import { ethers } from "hardhat";
import fs from "fs";
import path from "path";

// ======================== Configuration ========================
const TOTAL_TRANSACTIONS = 5000; // Fixed total number of purchase() calls (must be >= max USER_COUNTS)
const USER_COUNTS = [1, 2, 5, 10, 20, 50, 100, 500, 1000, 2000, 3000, 4000, 5000]; // Vary the number of users
const PRICE = 1n; // 1 wei — benchmark measures gas throughput, not ETH value transfer
const ROUNDS = 3; // Repeat each experiment N times and average
const DEPLOY_BATCH_SIZE = 50; // Parallel deploys per batch
const REGISTER_BATCH_SIZE = 100; // Parallel PubKey registrations per batch
// ===============================================================

interface RoundResult {
  userCount: number;
  round: number;
  totalTx: number;
  totalTimeMs: number;
  tps: number;
  gps: number;              // Gas Per Second (client-side wall clock, includes submit overhead)
  onChainGps: number;       // Gas Per Second (chain-observed: lastBlock.ts - firstBlock.ts)
  blockGasUtil: number;     // avg gasUsed per block / blockGasLimit  (0~1, time-independent)
  totalGasUsed: bigint;
  avgGasPerTx: number;
  avgLatencyMs: number;
  maxLatencyMs: number;
  minLatencyMs: number;
}

interface AggregatedResult {
  userCount: number;
  totalTx: number;
  avgTps: number;
  avgGps: number;
  avgOnChainGps: number;
  avgBlockGasUtil: number;
  avgGasPerTx: number;
  avgLatencyMs: number;
  maxLatencyMs: number;
  minLatencyMs: number;
  rounds: RoundResult[];
}

/**
 * Create a deterministic dataHash from an index
 */
function createDataHash(index: number): string {
  return ethers.keccak256(ethers.toUtf8Bytes(`benchmark-data-${index}`));
}

/**
 * Format elapsed time as human-readable string
 */
function formatTime(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

/**
 * Deploy infrastructure contracts: PubKey + IoTMarket
 */
async function deployInfrastructure(deployer: any) {
  console.log("  Deploying PubKey...");
  const pubKey = await ethers.deployContract("PubKey", [], deployer);
  await pubKey.waitForDeployment();

  console.log("  Deploying IoTMarket...");
  const iotMarket = await ethers.deployContract("IoTMarket", [], deployer);
  await iotMarket.waitForDeployment();

  return { pubKey, iotMarket };
}

/**
 * Register PubKey for each buyer (needed by purchase() → getPubKey())
 */
async function registerBuyerKeys(pubKeyContract: any, buyers: any[]) {
  console.log(`  Registering PubKeys for ${buyers.length} buyers...`);
  const startTime = Date.now();

  for (let i = 0; i < buyers.length; i += REGISTER_BATCH_SIZE) {
    const batch = buyers.slice(i, i + REGISTER_BATCH_SIZE);
    await Promise.all(
      batch.map(async (buyer) => {
        const tx = await pubKeyContract
          .connect(buyer)
          .registerKey("[benchmark-pubkey]");
        await tx.wait();
      })
    );

    const done = Math.min(i + REGISTER_BATCH_SIZE, buyers.length);
    const elapsed = Date.now() - startTime;
    const eta = done > 0 ? (elapsed / done) * (buyers.length - done) : 0;
    if (done % 500 === 0 || done === buyers.length) {
      console.log(
        `    Registered ${done}/${buyers.length} (${formatTime(elapsed)} elapsed, ETA ${formatTime(Math.round(eta))})`
      );
    }
  }
}

/**
 * Deploy T Merchandise contracts in batches
 */
async function deployMerchandises(
  count: number,
  pubKeyAddress: string,
  deployer: any
): Promise<string[]> {
  console.log(`  Deploying ${count} Merchandise contracts...`);
  const addresses: string[] = [];
  const startTime = Date.now();

  // Fetch deployer's current nonce once and assign manually to avoid "replacement transaction underpriced" with concurrent sends on Geth.
  const factory = await ethers.getContractFactory("Merchandise", deployer);
  let deployerNonce = await deployer.getNonce("latest");

  for (let i = 0; i < count; i += DEPLOY_BATCH_SIZE) {
    const batchEnd = Math.min(i + DEPLOY_BATCH_SIZE, count);
    const batchPromises = [];

    for (let j = i; j < batchEnd; j++) {
      const nonce = deployerNonce++;
      batchPromises.push(
        (async () => {
          const dataHash = createDataHash(j);
          const merchandise = await factory.deploy(
            PRICE, dataHash, pubKeyAddress, [], [], [],
            { nonce }
          );
          await merchandise.waitForDeployment();
          return merchandise.getAddress();
        })()
      );
    }

    const batchAddresses = await Promise.all(batchPromises);
    addresses.push(...batchAddresses);

    const done = batchEnd;
    const elapsed = Date.now() - startTime;
    const eta = done > 0 ? (elapsed / done) * (count - done) : 0;
    if (done % 500 === 0 || done === count) {
      console.log(
        `    Deployed ${done}/${count} (${formatTime(elapsed)} elapsed, ETA ${formatTime(Math.round(eta))})`
      );
    }
  }

  return addresses;
}

/**
 * Run a single benchmark round:
 *  - N users concurrently purchase T/N Merchandise contracts each
 *  - Two-phase approach:
 *      Phase 1 (Submit): All users send their tx to the mempool as fast as possible
 *                         (await send, but NOT await receipt)
 *      Phase 2 (Confirm): Wait for all receipts in parallel
 *  - For large N, users are batched to avoid overwhelming the event loop
 */
async function runBenchmarkRound(
  userCount: number,
  merchandiseAddresses: string[],
  buyers: any[]
): Promise<RoundResult> {
  const baseTxPerUser = Math.floor(TOTAL_TRANSACTIONS / userCount);
  const remainder = TOTAL_TRANSACTIONS % userCount;
  // Distribute remainder: first `remainder` users get one extra tx
  // e.g. 5000 / 2000 = 2 rem 1000 → users[0..999] get 3 tx, users[1000..1999] get 2 tx
  const userTxCounts: number[] = Array.from({ length: userCount }, (_, i) =>
    baseTxPerUser + (i < remainder ? 1 : 0)
  );
  // Pre-compute start index in merchandiseAddresses for each user
  const userStartIdx: number[] = new Array(userCount);
  userStartIdx[0] = 0;
  for (let i = 1; i < userCount; i++) {
    userStartIdx[i] = userStartIdx[i - 1] + userTxCounts[i - 1];
  }
  const actualTotalTx = TOTAL_TRANSACTIONS;
  const latencies: number[] = [];
  let totalGasUsed = 0n;
  // For on-chain GPS: track block timestamps (seconds) and per-block gas
  let firstBlockTimestamp: number | null = null;
  let lastBlockTimestamp: number | null = null;
  const blockGasMap = new Map<number, bigint>(); // blockNumber → gasUsed in that block
  const blockLimitMap = new Map<number, bigint>(); // blockNumber → gasLimit (from block header)
  // Cache block info (timestamp + gasLimit) to avoid duplicate eth_getBlockByNumber calls
  const blockCache = new Map<number, { timestamp: number; gasLimit: bigint }>();

  const startTime = Date.now();

  // For very large user counts, batch the concurrent users to avoid overwhelming Node.js with too many simultaneous promises
  const USER_CONCURRENCY = Math.min(userCount, 200);
  const userBatches: { buyer: any; globalIdx: number }[][] = [];
  for (let i = 0; i < userCount; i += USER_CONCURRENCY) {
    const batch = buyers
      .slice(i, Math.min(i + USER_CONCURRENCY, userCount))
      .map((buyer, localIdx) => ({
        buyer,
        globalIdx: i + localIdx,
      }));
    userBatches.push(batch);
  }

  for (const batch of userBatches) {
    // ---- Phase 1: Submit all transactions to the mempool ----
    // Each user sends all their tx concurrently; 
    const allPendingTx: {
      txResponse: any;
      submitTime: number;
    }[] = [];

    const submitPromises = batch.map(async ({ buyer, globalIdx }) => {
      const startIdx = userStartIdx[globalIdx];
      const txCount = userTxCounts[globalIdx];
      const pending: { txResponse: any; submitTime: number }[] = [];

      // Fetch nonce once per buyer to avoid "replacement transaction underpriced"
      // when txCount > 1 (ethers.js would re-query "latest" nonce each time
      // getting duplicate values for still-pending txs in Geth --dev)
      let nonce = await buyer.getNonce("pending");

      for (let t = 0; t < txCount; t++) {
        const merchAddr = merchandiseAddresses[startIdx + t];
        const merchandise = await ethers.getContractAt(
          "Merchandise",
          merchAddr,
          buyer
        );

        const submitTime = Date.now();
        const txResponse = await merchandise.purchase({ value: PRICE, nonce: nonce++ });
        pending.push({ txResponse, submitTime });
      }

      return pending;
    });

    const submitResults = await Promise.all(submitPromises);// users simultaneously call `purchase`
    for (const userPending of submitResults) {
      allPendingTx.push(...userPending);
    }

    // ---- Phase 2: Wait for all receipts ----
    // wait for confirmations and record latencies and gas used
    // Batch the waits to avoid overwhelming Geth with thousands of concurrent polling connections
    const RECEIPT_BATCH = 200;
    for (let rb = 0; rb < allPendingTx.length; rb += RECEIPT_BATCH) {
      const receiptBatch = allPendingTx.slice(rb, rb + RECEIPT_BATCH);
      const batchResults = await Promise.all(
        receiptBatch.map(async ({ txResponse, submitTime }) => {
          const receipt = await txResponse.wait();
          const confirmedTime = Date.now();
          // Use block cache to avoid duplicate eth_getBlockByNumber for the same block
          let blockInfo = blockCache.get(receipt.blockNumber);
          if (!blockInfo) {
            const block = await ethers.provider.getBlock(receipt.blockNumber);
            blockInfo = { timestamp: block!.timestamp, gasLimit: block!.gasLimit };
            blockCache.set(receipt.blockNumber, blockInfo);
          }
          return {
            latency: confirmedTime - submitTime,
            gasUsed: receipt.gasUsed as bigint,
            blockNumber: receipt.blockNumber as number,
            blockTimestamp: blockInfo.timestamp,
            blockGasLimit: blockInfo.gasLimit,
          };
        })
      );
      for (const { latency, gasUsed, blockNumber, blockTimestamp, blockGasLimit } of batchResults) {
        latencies.push(latency);
        totalGasUsed += gasUsed;
        // Accumulate gas per block, also store gasLimit per block for utilization calc
        const prev = blockGasMap.get(blockNumber);
        blockGasMap.set(blockNumber, (prev ?? 0n) + gasUsed);
        // Store gasLimit per block (all txs in same block share same limit)
        if (!blockLimitMap.has(blockNumber)) blockLimitMap.set(blockNumber, blockGasLimit);
        // Track first/last block timestamp
        if (firstBlockTimestamp === null || blockTimestamp < firstBlockTimestamp)
          firstBlockTimestamp = blockTimestamp;
        if (lastBlockTimestamp === null || blockTimestamp > lastBlockTimestamp)
          lastBlockTimestamp = blockTimestamp;
      }
    }
  }

  const endTime = Date.now();

  const totalTimeMs = endTime - startTime;
  const tps = (actualTotalTx / totalTimeMs) * 1000;
  const gps = (Number(totalGasUsed) / totalTimeMs) * 1000;

  // On-chain GPS: use block timestamps from receipts.
  // This removes client-side submit/polling overhead from the denominator.
  // If all txs land in the same block, onChainGps = Infinity (one instant block)
  // fall back to client GPS in that edge case
  const blockTimeDeltaSec = (lastBlockTimestamp ?? 0) - (firstBlockTimestamp ?? 0);
  const onChainGps = blockTimeDeltaSec > 0
    ? (Number(totalGasUsed) / blockTimeDeltaSec)
    : gps; // fallback: single-block burst, use client GPS

  // Block gas utilization: per-block gasUsed / gasLimit, then averaged across blocks
  // Uses the actual gasLimit fetched from each block header
  let blockGasUtilSum = 0;
  for (const [blockNum, gasUsed] of blockGasMap.entries()) {
    const gasLimit = blockLimitMap.get(blockNum) ?? 1n; // fallback to 1 to avoid /0
    blockGasUtilSum += Number(gasUsed) / Number(gasLimit);
  }
  const blockGasUtil = blockGasMap.size > 0 ? blockGasUtilSum / blockGasMap.size : 0;

  const avgLatencyMs =
    latencies.reduce((a, b) => a + b, 0) / latencies.length;
  const maxLatencyMs = Math.max(...latencies);
  const minLatencyMs = Math.min(...latencies);

  return {
    userCount,
    round: 0,
    totalTx: actualTotalTx,
    totalTimeMs,
    tps,
    gps,
    onChainGps,
    blockGasUtil,
    totalGasUsed,
    avgGasPerTx: Number(totalGasUsed) / actualTotalTx,
    avgLatencyMs,
    maxLatencyMs,
    minLatencyMs,
  };
}


function saveResults(results: AggregatedResult[]) {
  const outputDir = path.resolve(__dirname, "../results");
  fs.mkdirSync(outputDir, { recursive: true });

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");

  // CSV
  const csvHeader =
    "UserCount,TotalTx,AvgTPS,AvgGPS_client,AvgGPS_chain,AvgBlockGasUtil,AvgGasPerTx,AvgLatencyMs,MaxLatencyMs,MinLatencyMs\n";
  const csvRows = results
    .map(
      (r) =>
        `${r.userCount},${r.totalTx},${r.avgTps.toFixed(2)},${r.avgGps.toFixed(0)},${r.avgOnChainGps.toFixed(0)},${r.avgBlockGasUtil.toFixed(4)},${r.avgGasPerTx.toFixed(0)},${r.avgLatencyMs.toFixed(2)},${r.maxLatencyMs.toFixed(2)},${r.minLatencyMs.toFixed(2)}`
    )
    .join("\n");

  const csvPathLatest = path.join(outputDir, "gas_benchmark_results.csv");
  const csvPathTimestamp = path.join(outputDir, `gas_benchmark_${timestamp}.csv`);
  fs.writeFileSync(csvPathLatest, csvHeader + csvRows);
  fs.writeFileSync(csvPathTimestamp, csvHeader + csvRows);
  console.log(`\nResults saved to ${csvPathLatest}`);

  // JSON
  const jsonPathLatest = path.join(outputDir, "gas_benchmark_results.json");
  const jsonPathTimestamp = path.join(
    outputDir,
    `gas_benchmark_${timestamp}.json`
  );
  fs.writeFileSync(jsonPathLatest, JSON.stringify(results, (_key, value) =>
    typeof value === "bigint" ? value.toString() : value, 2));
  fs.writeFileSync(jsonPathTimestamp, JSON.stringify(results, (_key, value) =>
    typeof value === "bigint" ? value.toString() : value, 2));
  console.log(`Results saved to ${jsonPathLatest}`);
  console.log(`Timestamped copies saved with prefix: benchmark_${timestamp}`);
}

async function main() {
  const experimentStart = Date.now();

  console.log("=".repeat(60));
  console.log("  Experiment 1: User Number vs GAS (Throughput)");
  console.log("=".repeat(60));
  console.log(`  Total Transactions per round: ${TOTAL_TRANSACTIONS}`);
  console.log(`  User counts to test: [${USER_COUNTS.join(", ")}]`);
  console.log(`  Rounds per user count: ${ROUNDS}`);
  console.log(`  Price per Merchandise: ${ethers.formatEther(PRICE)} ETH`);
  console.log(`  Deploy batch size: ${DEPLOY_BATCH_SIZE}`);
  console.log(`  Register batch size: ${REGISTER_BATCH_SIZE}`);
  console.log("=".repeat(60));

  // Validate: T must be >= max(USER_COUNTS)
  const maxUsers = Math.max(...USER_COUNTS);
  if (TOTAL_TRANSACTIONS < maxUsers) {
    throw new Error(
      `TOTAL_TRANSACTIONS (${TOTAL_TRANSACTIONS}) must be >= max USER_COUNTS (${maxUsers}). ` +
        `Each user needs at least 1 transaction.`
    );
  }

  // Get all available signers
  console.log("\n[Phase 0] Loading signers...");
  const allSigners = await ethers.getSigners();
  console.log(`  Available signers: ${allSigners.length}`);

  if (allSigners.length < maxUsers + 1) {
    throw new Error(
      `Need at least ${maxUsers + 1} signers, but only have ${allSigners.length}. ` +
        `Increase 'accounts.count' in hardhat.config.ts.`
    );
  }

  // Signer[0] = deployer/owner, Signer[1..N] = buyers
  const deployer = allSigners[0];
  const allBuyers = allSigners.slice(1, maxUsers + 1);

  console.log(`  Deployer: ${deployer.address}`);
  console.log(`  Total buyers to prepare: ${allBuyers.length}`);

  // Deploy infrastructure (once)
  console.log("\n[Phase 1] Deploying infrastructure...");
  const { pubKey } = await deployInfrastructure(deployer);
  const pubKeyAddress = await pubKey.getAddress();

  // Register PubKeys for all buyers (once)
  console.log("\n[Phase 2] Registering buyer PubKeys...");
  await registerBuyerKeys(pubKey, allBuyers);
  console.log(
    `  PubKey registration complete. (${formatTime(Date.now() - experimentStart)} total elapsed)`
  );

  // Run benchmark for each user count
  const aggregatedResults: AggregatedResult[] = [];

  for (const userCount of USER_COUNTS) {
    console.log(`\n${"─".repeat(60)}`);
    console.log(`  Testing with ${userCount} users...`);
    const baseTx = Math.floor(TOTAL_TRANSACTIONS / userCount);
    const rem = TOTAL_TRANSACTIONS % userCount;
    console.log(
      `  (Each user sends ${baseTx}~${baseTx + (rem > 0 ? 1 : 0)} tx, total = ${TOTAL_TRANSACTIONS})`
    );
    console.log(`${"─".repeat(60)}`);

    const rounds: RoundResult[] = [];

    for (let r = 0; r < ROUNDS; r++) {
      console.log(`\n  [Round ${r + 1}/${ROUNDS}]`);

      // Deploy fresh Merchandise contracts for this round
      console.log("  [Phase 3] Deploying Merchandise contracts...");
      const deployStart = Date.now();
      const merchandiseAddresses = await deployMerchandises(
        TOTAL_TRANSACTIONS,
        pubKeyAddress,
        deployer
      );
      console.log(
        `  Deployment done in ${formatTime(Date.now() - deployStart)}`
      );

      // Run the benchmark
      console.log("  [Phase 4] Running purchase() benchmark...");
      const result = await runBenchmarkRound(
        userCount,
        merchandiseAddresses,
        allBuyers
      );
      result.round = r + 1;
      rounds.push(result);

      console.log(`    Total time:    ${result.totalTimeMs} ms`);
      console.log(`    TPS:           ${result.tps.toFixed(2)}`);
      console.log(`    GPS (client):  ${(result.gps / 1e6).toFixed(2)} Mgas/s`);
      console.log(`    GPS (chain):   ${(result.onChainGps / 1e6).toFixed(2)} Mgas/s`);
      console.log(`    BlockGasUtil:  ${(result.blockGasUtil * 100).toFixed(1)}%`);
      console.log(`    Avg gas/tx:    ${result.avgGasPerTx.toFixed(0)}`);
      console.log(`    Avg latency:   ${result.avgLatencyMs.toFixed(2)} ms`);
      console.log(`    Max latency:   ${result.maxLatencyMs.toFixed(2)} ms`);
      console.log(`    Min latency:   ${result.minLatencyMs.toFixed(2)} ms`);
    }

    // Aggregate results across rounds
    const avgTps = rounds.reduce((a, b) => a + b.tps, 0) / rounds.length;
    const avgGps = rounds.reduce((a, b) => a + b.gps, 0) / rounds.length;
    const avgOnChainGps = rounds.reduce((a, b) => a + b.onChainGps, 0) / rounds.length;
    const avgBlockGasUtil = rounds.reduce((a, b) => a + b.blockGasUtil, 0) / rounds.length;
    const avgGasPerTx = rounds.reduce((a, b) => a + b.avgGasPerTx, 0) / rounds.length;
    const avgLatency =
      rounds.reduce((a, b) => a + b.avgLatencyMs, 0) / rounds.length;
    const maxLatency = Math.max(...rounds.map((r) => r.maxLatencyMs));
    const minLatency = Math.min(...rounds.map((r) => r.minLatencyMs));

    aggregatedResults.push({
      userCount,
      totalTx: TOTAL_TRANSACTIONS,
      avgTps,
      avgGps,
      avgOnChainGps,
      avgBlockGasUtil,
      avgGasPerTx,
      avgLatencyMs: avgLatency,
      maxLatencyMs: maxLatency,
      minLatencyMs: minLatency,
      rounds,
    });

    console.log(
      `\n  ▸ ${userCount} users | Avg TPS: ${avgTps.toFixed(2)} | GPS(client): ${(avgGps / 1e6).toFixed(2)} Mgas/s | GPS(chain): ${(avgOnChainGps / 1e6).toFixed(2)} Mgas/s | BlockUtil: ${(avgBlockGasUtil * 100).toFixed(1)}%`
    );
    console.log(
      `  Total experiment time so far: ${formatTime(Date.now() - experimentStart)}`
    );
  }

  // Print summary table
  console.log("\n" + "=".repeat(100));
  console.log("  SUMMARY");
  console.log("=".repeat(100));
  console.log(
    "  Users  | TotalTx | Avg TPS   | GPS-client(Mgas/s) | GPS-chain(Mgas/s) | BlkUtil% | Avg Gas/tx | Avg Latency"
  );
  console.log("  " + "─".repeat(98));
  for (const r of aggregatedResults) {
    console.log(
      `  ${String(r.userCount).padStart(6)} | ` +
        `${String(r.totalTx).padStart(7)} | ` +
        `${r.avgTps.toFixed(2).padStart(9)} | ` +
        `${(r.avgGps / 1e6).toFixed(2).padStart(18)} | ` +
        `${(r.avgOnChainGps / 1e6).toFixed(2).padStart(17)} | ` +
        `${(r.avgBlockGasUtil * 100).toFixed(1).padStart(8)} | ` +
        `${r.avgGasPerTx.toFixed(0).padStart(10)} | ` +
        `${r.avgLatencyMs.toFixed(2).padStart(11)}`
    );
  }

  // Save to files
  saveResults(aggregatedResults);

  console.log(
    `\nBenchmark complete! Total time: ${formatTime(Date.now() - experimentStart)}`
  );
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("Benchmark failed:", error);
    process.exit(1);
  });
