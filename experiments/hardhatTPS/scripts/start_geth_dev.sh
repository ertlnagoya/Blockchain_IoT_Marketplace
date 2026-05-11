# Launch a Geth --dev node with:
# chainId 1337 (matches Hardhat default)
# auto mining (--dev.period 0)
# HTTP JSON-RPC on port 8545
# WebSocket JSON-RPC on port 8546
# 5001 accounts
# High gas limit (30M)
# Logs written to geth-dev.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SETUP_DIR="${PROJECT_DIR}/geth-setup"
DATA_DIR="/tmp/geth-dev-data"   # Use short path to avoid IPC 103-char limit on macOS
LOG_FILE="${SETUP_DIR}/geth-dev.log"
PID_FILE="${SETUP_DIR}/geth.pid"

# ── Clean up old data
if [[ "${1:-}" == "--reset" ]]; then
  echo "Resetting geth data directory..."
  rm -rf "${DATA_DIR}"
fi

mkdir -p "${DATA_DIR}"

# ── Load deployer address (account[0])
ACCOUNTS_JSON="${SCRIPT_DIR}/accounts.json"
if [[ ! -f "${ACCOUNTS_JSON}" ]]; then
  echo "❌ accounts.json not found. Run: node scripts/gen_accounts.mjs"
  exit 1
fi

# Extract address[0] (deployer) using Node.js (already available)
DEPLOYER_ADDR=$(node -e "
  const d = JSON.parse(require('fs').readFileSync('${ACCOUNTS_JSON}'));
  console.log(d.accounts[0].address.toLowerCase());
")

echo "================================================"
echo "  Starting Geth --dev node"
echo "  Data dir:  ${DATA_DIR}"
echo "  Log file:  ${LOG_FILE}"
echo "  HTTP RPC:  http://127.0.0.1:8545"
echo "  WS RPC:    ws://127.0.0.1:8546"
echo "  Deployer:  ${DEPLOYER_ADDR}"
echo "  Chain ID:  1337"
echo "================================================"
echo ""

# ── Start Geth --dev
# --dev           : Developer mode — instant mining, no PoW/PoA
# --dev.period 0  : Mine only when there are pending transactions (instant)
# --datadir       : Persistent data directory
# --networkid     : Must match chainId for MetaMask / ethers.js
# --http.*        : Enable HTTP JSON-RPC
# --ws.*          : Enable WebSocket JSON-RPC
# --miner.gaslimit: Set block gas limit to 30M
# --allow-insecure-unlock: Required to unlock accounts via API
# --unlock        : Pre-unlock the deployer so Hardhat can submit txs
#                   (Geth --dev auto-creates a dev account, but we want
#                    our derived account to be the sender)
# --password      : Empty password file for unlocking

EMPTY_PWD_FILE="${SETUP_DIR}/empty_password.txt"
echo -n "" > "${EMPTY_PWD_FILE}"

geth \
  --dev \
  --dev.period 0 \
  --datadir "${DATA_DIR}" \
  --networkid 1337 \
  --http \
  --http.addr "127.0.0.1" \
  --http.port 8545 \
  --http.api "eth,net,web3,personal,txpool,debug" \
  --http.corsdomain "*" \
  --http.vhosts "*" \
  --ws \
  --ws.addr "127.0.0.1" \
  --ws.port 8546 \
  --ws.api "eth,net,web3,personal,txpool,debug" \
  --ws.origins "*" \
  --miner.gaslimit 30000000 \
  --rpc.gascap 0 \
  --rpc.txfeecap 0 \
  --rpc.batch-request-limit 2000 \
  --rpc.batch-response-max-size 104857600 \
  --verbosity 3 \
  > "${LOG_FILE}" 2>&1 &

GETH_PID=$!
echo "${GETH_PID}" > "${PID_FILE}"

echo "Geth started with PID ${GETH_PID}"
echo "PID saved to: ${PID_FILE}"
echo ""
echo "Waiting for RPC to become available..."

# ── Wait for Geth to be ready
for i in $(seq 1 30); do
  sleep 1
  if curl -sf -X POST http://127.0.0.1:8545 \
       -H "Content-Type: application/json" \
       -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' \
       > /dev/null 2>&1; then
    echo "Geth RPC is ready! (${i}s)"
    break
  fi
  echo -n "  ..."
  if [[ ${i} -eq 30 ]]; then
    echo ""
    echo "❌ Geth did not start within 30s. Check logs: tail -f ${LOG_FILE}"
    exit 1
  fi
done

echo ""
echo "Chain ID check:"
curl -s -X POST http://127.0.0.1:8545 \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'
echo ""
echo ""
echo "================================================"
echo " Geth --dev node is running!"
echo ""
echo "  To fund accounts, run:"
echo "    node scripts/fund_accounts.mjs"
echo ""
echo " To stop Geth:"
echo "    kill \$(cat ${PID_FILE})"
echo ""
echo " To watch logs:"
echo "    tail -f ${LOG_FILE}"
echo "================================================"
