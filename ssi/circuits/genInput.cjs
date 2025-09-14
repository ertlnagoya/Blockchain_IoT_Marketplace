const fs = require('fs');

const args = process.argv.slice(2).map(Number);


let entityType         = 1; // 0:Other, 1:Gov, 2:Police, 3:Enterprise, 4:ResearchOrg
let purpose            = 3; // 0:Other, 1:CrimeSearch, 2:TrafficMgmt, 3:Research
let legalCompliance    = 1; // 0/1
let dataHandlingPolicy = 1; // 0/1
let misuseRecord       = 0; // 0/1

if (args.length === 5) {
  [entityType, purpose, legalCompliance, dataHandlingPolicy, misuseRecord] = args;
}


const isGov      = Number(entityType === 1);
const isPolice   = Number(entityType === 2);
const isEnterp   = Number(entityType === 3);
const isResearch = Number(entityType === 4);
const isGovOrPolice = isGov + isPolice - isGov * isPolice;
const isOtherEntity = 1 - (isGovOrPolice + isEnterp + isResearch);

const isCrime     = Number(purpose === 1);
const isTraffic   = Number(purpose === 2);
const isResearchP = Number(purpose === 3);
const isOtherPurpose = 1 - (isCrime + isTraffic + isResearchP);


const entityScore  = 35*isGovOrPolice + 20*isEnterp + 15*isResearch + 5*isOtherEntity;
const purposeScore = 25*isCrime + 20*isTraffic + 15*isResearchP + 5*isOtherPurpose;
const legalScore   = 15*legalCompliance;
const policyScore  = 15*dataHandlingPolicy;
const misuseScore  = 10 - 20*misuseRecord;
const score = entityScore + purposeScore + legalScore + policyScore + misuseScore;

// 生成 b（7 位，b[0] 为最低位）
if (score < 0 || score > 127) {
  throw new Error(`score 超出 7 位范围: ${score}`);
}
const b = Array.from({ length: 7 }, (_, i) => (score >> i) & 1);

// 期望 level：>=80 为2；>=60 且 <80 为1；否则0
const level = score >= 80 ? 2 : (score >= 60 ? 1 : 0);

const input = { entityType, purpose, legalCompliance, dataHandlingPolicy, misuseRecord, b };
fs.writeFileSync('input.json', JSON.stringify(input, null, 2));

console.log('输入：', { entityType, purpose, legalCompliance, dataHandlingPolicy, misuseRecord });
console.log('得分/位分解：', { score, b, level });
console.log('已写入 input.json');