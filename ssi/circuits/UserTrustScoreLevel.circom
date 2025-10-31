
template IsZero() {
    signal input in;
    signal output out;
    signal inv;

    // witness 提示（0.5 必需）：in==0 时 inv=0；否则 inv=1/in
    inv <-- in == 0 ? 0 : 1/in;
    // 显式赋值 out，保证可计算
    out <== 1 - in * inv;

    
    out * (out - 1) === 0;
    in * out === 0;
    (1 - out) === in * inv;
}

// 将 x(7位) 与常量K进行比较：输出 lt=1 当且仅当 x < K
// 常量 K 的二进制自高位到低位（b6..b0）作为参数传入
template LessThanConst7(k6, k5, k4, k3, k2, k1, k0) {
    signal input xbits[7];   // x 的 7 个比特，高位在 [6]
    signal output lt;

    for (var i = 0; i < 7; i++) {
        xbits[i] * (xbits[i] - 1) === 0;
    }

    // 逐位比较（从高位到低位）
    signal eq6; eq6 <== 1;  // 初始高位都相等
    // bit 6
    signal xor6; xor6 <== xbits[6] + k6 - 2*xbits[6]*k6;
    signal less6; less6 <== eq6 * ((1 - xbits[6]) * k6);
    signal eq5;  eq5  <== eq6 * (1 - xor6);
    // bit 5
    signal xor5; xor5 <== xbits[5] + k5 - 2*xbits[5]*k5;
    signal less5; less5 <== eq5 * ((1 - xbits[5]) * k5);
    signal eq4;  eq4  <== eq5 * (1 - xor5);
    // bit 4
    signal xor4; xor4 <== xbits[4] + k4 - 2*xbits[4]*k4;
    signal less4; less4 <== eq4 * ((1 - xbits[4]) * k4);
    signal eq3;  eq3  <== eq4 * (1 - xor4);
    // bit 3
    signal xor3; xor3 <== xbits[3] + k3 - 2*xbits[3]*k3;
    signal less3; less3 <== eq3 * ((1 - xbits[3]) * k3);
    signal eq2;  eq2  <== eq3 * (1 - xor3);
    // bit 2
    signal xor2; xor2 <== xbits[2] + k2 - 2*xbits[2]*k2;
    signal less2; less2 <== eq2 * ((1 - xbits[2]) * k2);
    signal eq1;  eq1  <== eq2 * (1 - xor2);
    // bit 1
    signal xor1; xor1 <== xbits[1] + k1 - 2*xbits[1]*k1;
    signal less1; less1 <== eq1 * ((1 - xbits[1]) * k1);
    signal eq0;  eq0  <== eq1 * (1 - xor1);
    // bit 0
    signal xor0; xor0 <== xbits[0] + k0 - 2*xbits[0]*k0;
    signal less0; less0 <== eq0 * ((1 - xbits[0]) * k0);

    lt <== less6 + less5 + less4 + less3 + less2 + less1 + less0;
    lt * (lt - 1) === 0; // 布尔
}

// 主电路：计算分数并仅输出 level
template UserTrustScoreLevel() {
    signal private input entityType;         // 0:Other, 1:Gov, 2:Police, 3:Enterprise, 4:ResearchOrg
    signal private input purpose;            // 0:Other, 1:CrimeSearch, 2:TrafficMgmt, 3:Research
    signal private input legalCompliance;    // 0/1
    signal private input dataHandlingPolicy; // 0:Other, 1:ISO27001
    signal private input misuseRecord;       // 0:false, 1:true

    signal output level; // 0/1/2

    legalCompliance * (legalCompliance - 1) === 0;
    dataHandlingPolicy * (dataHandlingPolicy - 1) === 0;
    misuseRecord * (misuseRecord - 1) === 0;

    // entityType 匹配
    component e1 = IsZero(); e1.in <== entityType - 1; // Gov
    component e2 = IsZero(); e2.in <== entityType - 2; // Police
    component e3 = IsZero(); e3.in <== entityType - 3; // Enterprise
    component e4 = IsZero(); e4.in <== entityType - 4; // ResearchOrg
    signal isGov;      isGov      <== e1.out;
    signal isPolice;   isPolice   <== e2.out;
    signal isEnterp;   isEnterp   <== e3.out;
    signal isResearch; isResearch <== e4.out;

    signal isGovOrPolice; isGovOrPolice <== isGov + isPolice - isGov * isPolice;
    signal isOtherEntity; isOtherEntity <== 1 - (isGovOrPolice + isEnterp + isResearch);

    isGov*(isGov-1) === 0;
    isPolice*(isPolice-1) === 0;
    isEnterp*(isEnterp-1) === 0;
    isResearch*(isResearch-1) === 0;
    isGovOrPolice*(isGovOrPolice-1) === 0;
    isOtherEntity*(isOtherEntity-1) === 0;

    // purpose 匹配
    component p1 = IsZero(); p1.in <== purpose - 1; // Crime Search
    component p2 = IsZero(); p2.in <== purpose - 2; // Traffic Mgmt
    component p3 = IsZero(); p3.in <== purpose - 3; // Research
    signal isCrime;     isCrime     <== p1.out;
    signal isTraffic;   isTraffic   <== p2.out;
    signal isResearchP; isResearchP <== p3.out;
    signal isOtherPurpose; isOtherPurpose <== 1 - (isCrime + isTraffic + isResearchP);
    isCrime*(isCrime-1) === 0;
    isTraffic*(isTraffic-1) === 0;
    isResearchP*(isResearchP-1) === 0;
    isOtherPurpose*(isOtherPurpose-1) === 0;

    // 各项得分
    signal entityScore;  entityScore  <== 35*isGovOrPolice + 20*isEnterp + 15*isResearch + 5*isOtherEntity;
    signal purposeScore; purposeScore <== 25*isCrime + 20*isTraffic + 15*isResearchP + 5*isOtherPurpose;
    signal legalScore;   legalScore   <== 15*legalCompliance;
    signal policyScore;  policyScore  <== 15*dataHandlingPolicy;
    signal misuseScore;  misuseScore  <== 10 - 20*misuseRecord;

    // 总分
    signal scoreCalc; scoreCalc <== entityScore + purposeScore + legalScore + policyScore + misuseScore;

    // score 的 7 位分解（0..127）
    signal private input b[7];
    for (var i = 0; i < 7; i++) { b[i] * (b[i] - 1) === 0; }
    signal recomposed;
    recomposed <== b[0] + 2*b[1] + 4*b[2] + 8*b[3] + 16*b[4] + 32*b[5] + 64*b[6];

    scoreCalc === recomposed;

    // 与 60(0b0111100) 比较（xbits[6]为最高位，b[6]也是最高位，按位对应）
    component lt60 = LessThanConst7(0,1,1,1,1,0,0);
    for (var i = 0; i < 7; i++) { lt60.xbits[i] <== b[i]; }

    // 与 80(0b1010000) 比较（同样按位对应）
    component lt80 = LessThanConst7(1,0,1,0,0,0,0);
    for (var i = 0; i < 7; i++) { lt80.xbits[i] <== b[i]; }

    signal ge60; ge60 <== 1 - lt60.lt; // score >= 60
    signal ge80; ge80 <== 1 - lt80.lt; // score >= 80

    // full 条件：score>=80 且 (Gov或Police)
    signal fullCond; fullCond <== ge80 * isGovOrPolice;

    // level2 = fullCond; level1 = ge60 且 非level2; level0 = 其余
    signal level2; level2 <== fullCond;
    signal level1; level1 <== ge60 * (1 - level2);
    signal level0; level0 <== 1 - (level2 + level1);

    level0*(level0-1) === 0; level1*(level1-1) === 0; level2*(level2-1) === 0;

    level <== level1 + 2*level2;
}

component main = UserTrustScoreLevel();