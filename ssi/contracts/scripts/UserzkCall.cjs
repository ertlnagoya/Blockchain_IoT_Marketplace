/* eslint-disable no-undef */
const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const zkAddr = process.env.ZK_ADDR || "";
  if (!/^0x[0-9a-fA-F]{40}$/.test(zkAddr)) {
    throw new Error("请用环境变量 ZK_ADDR 传入 DataUserZKAccess 地址");
  }

  const calldataPath = path.join(__dirname, "../../circuits/calldata.txt");
  const raw = fs.readFileSync(calldataPath, "utf8").trim();
  const [a, b, c, inputs] = JSON.parse("[" + raw + "]");
  const level = Number(inputs[0]);

  try {
    const pub = JSON.parse(fs.readFileSync(path.join(__dirname, "../../circuits/public.json"), "utf8"));
    if (String(level) !== String(pub[0])) {
      throw new Error(`inputs[0]=${level} 与 public.json[0]=${pub[0]} 不一致`);
    }
  } catch {}

  const abi = (await hre.artifacts.readArtifact("DataUserZKAccess")).abi;
  const [signer] = await hre.ethers.getSigners();
  const contract = new hre.ethers.Contract(zkAddr, abi, signer);

  console.log("verifyUserLevelZK level =", level);
  const tx = await contract.verifyUserLevelZK(a, b, c, level);
  const rc = await tx.wait();
  console.log("tx:", rc.hash || rc.transactionHash);

  const iface = new hre.ethers.Interface(abi);
  for (const log of rc.logs) {
    try {
      const parsed = iface.parseLog(log);
      if (parsed?.name === "UserZKVerified") {
        console.log("UserZKVerified:", parsed.args);
      }
    } catch {}
  }
}

main().catch((e) => { console.error(e); process.exit(1); });