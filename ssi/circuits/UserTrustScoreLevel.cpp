#include "circom.hpp"
#include "calcwit.hpp"
#define NSignals 116
#define NComponents 10
#define NOutputs 1
#define NInputs 5
#define NVars 44
#define NPublic 6
#define __P__ "21888242871839275222246405745257275088548364400416034343698204186575808495617"

/*
UserTrustScoreLevel
*/
void UserTrustScoreLevel_75c5e8ce71c83660(Circom_CalcWit *ctx, int __cIdx) {
    FrElement _sigValue[1];
    FrElement _sigValue_1[1];
    FrElement _tmp[1];
    FrElement _tmp_1[1];
    FrElement _sigValue_2[1];
    FrElement _sigValue_3[1];
    FrElement _tmp_2[1];
    FrElement _tmp_3[1];
    FrElement _sigValue_4[1];
    FrElement _sigValue_5[1];
    FrElement _tmp_4[1];
    FrElement _tmp_5[1];
    FrElement _sigValue_6[1];
    FrElement _tmp_6[1];
    FrElement _sigValue_7[1];
    FrElement _tmp_7[1];
    FrElement _sigValue_8[1];
    FrElement _tmp_8[1];
    FrElement _sigValue_9[1];
    FrElement _tmp_9[1];
    FrElement _sigValue_10[1];
    FrElement _sigValue_11[1];
    FrElement _sigValue_12[1];
    FrElement _sigValue_13[1];
    FrElement _sigValue_14[1];
    FrElement _sigValue_15[1];
    FrElement _tmp_10[1];
    FrElement _sigValue_16[1];
    FrElement _sigValue_17[1];
    FrElement _tmp_11[1];
    FrElement _tmp_12[1];
    FrElement _sigValue_18[1];
    FrElement _sigValue_19[1];
    FrElement _tmp_13[1];
    FrElement _sigValue_20[1];
    FrElement _tmp_14[1];
    FrElement _tmp_15[1];
    FrElement _sigValue_21[1];
    FrElement _sigValue_22[1];
    FrElement _tmp_16[1];
    FrElement _tmp_17[1];
    FrElement _sigValue_23[1];
    FrElement _sigValue_24[1];
    FrElement _tmp_18[1];
    FrElement _tmp_19[1];
    FrElement _sigValue_25[1];
    FrElement _sigValue_26[1];
    FrElement _tmp_20[1];
    FrElement _tmp_21[1];
    FrElement _sigValue_27[1];
    FrElement _sigValue_28[1];
    FrElement _tmp_22[1];
    FrElement _tmp_23[1];
    FrElement _sigValue_29[1];
    FrElement _sigValue_30[1];
    FrElement _tmp_24[1];
    FrElement _tmp_25[1];
    FrElement _sigValue_31[1];
    FrElement _sigValue_32[1];
    FrElement _tmp_26[1];
    FrElement _tmp_27[1];
    FrElement _sigValue_33[1];
    FrElement _tmp_28[1];
    FrElement _sigValue_34[1];
    FrElement _tmp_29[1];
    FrElement _sigValue_35[1];
    FrElement _tmp_30[1];
    FrElement _sigValue_36[1];
    FrElement _sigValue_37[1];
    FrElement _sigValue_38[1];
    FrElement _sigValue_39[1];
    FrElement _sigValue_40[1];
    FrElement _tmp_31[1];
    FrElement _sigValue_41[1];
    FrElement _tmp_32[1];
    FrElement _tmp_33[1];
    FrElement _sigValue_42[1];
    FrElement _sigValue_43[1];
    FrElement _tmp_34[1];
    FrElement _tmp_35[1];
    FrElement _sigValue_44[1];
    FrElement _sigValue_45[1];
    FrElement _tmp_36[1];
    FrElement _tmp_37[1];
    FrElement _sigValue_46[1];
    FrElement _sigValue_47[1];
    FrElement _tmp_38[1];
    FrElement _tmp_39[1];
    FrElement _sigValue_48[1];
    FrElement _sigValue_49[1];
    FrElement _tmp_40[1];
    FrElement _tmp_41[1];
    FrElement _sigValue_50[1];
    FrElement _tmp_42[1];
    FrElement _sigValue_51[1];
    FrElement _tmp_43[1];
    FrElement _tmp_44[1];
    FrElement _sigValue_52[1];
    FrElement _tmp_45[1];
    FrElement _tmp_46[1];
    FrElement _sigValue_53[1];
    FrElement _tmp_47[1];
    FrElement _tmp_48[1];
    FrElement _sigValue_54[1];
    FrElement _tmp_49[1];
    FrElement _sigValue_55[1];
    FrElement _tmp_50[1];
    FrElement _tmp_51[1];
    FrElement _sigValue_56[1];
    FrElement _tmp_52[1];
    FrElement _tmp_53[1];
    FrElement _sigValue_57[1];
    FrElement _tmp_54[1];
    FrElement _tmp_55[1];
    FrElement _sigValue_58[1];
    FrElement _tmp_56[1];
    FrElement _sigValue_59[1];
    FrElement _tmp_57[1];
    FrElement _sigValue_60[1];
    FrElement _tmp_58[1];
    FrElement _tmp_59[1];
    FrElement _sigValue_61[1];
    FrElement _sigValue_62[1];
    FrElement _tmp_60[1];
    FrElement _sigValue_63[1];
    FrElement _tmp_61[1];
    FrElement _sigValue_64[1];
    FrElement _tmp_62[1];
    FrElement _sigValue_65[1];
    FrElement _tmp_63[1];
    FrElement _sigValue_66[1];
    FrElement _sigValue_67[1];
    FrElement _tmp_65[1];
    FrElement _tmp_66[1];
    FrElement _tmp_69[1];
    FrElement i[1];
    FrElement _sigValue_68[1];
    FrElement _sigValue_69[1];
    FrElement _tmp_70[1];
    FrElement _tmp_71[1];
    FrElement _tmp_73[1];
    FrElement _tmp_72[1];
    FrElement _tmp_74[1];
    FrElement _sigValue_70[1];
    FrElement _sigValue_71[1];
    FrElement _tmp_75[1];
    FrElement _tmp_76[1];
    FrElement _sigValue_72[1];
    FrElement _tmp_77[1];
    FrElement _tmp_78[1];
    FrElement _sigValue_73[1];
    FrElement _tmp_79[1];
    FrElement _tmp_80[1];
    FrElement _sigValue_74[1];
    FrElement _tmp_81[1];
    FrElement _tmp_82[1];
    FrElement _sigValue_75[1];
    FrElement _tmp_83[1];
    FrElement _tmp_84[1];
    FrElement _sigValue_76[1];
    FrElement _tmp_85[1];
    FrElement _tmp_86[1];
    FrElement _sigValue_77[1];
    FrElement _sigValue_78[1];
    FrElement _sigValue_79[1];
    FrElement _tmp_90[1];
    FrElement i_1[1];
    FrElement _sigValue_80[1];
    FrElement _tmp_92[1];
    FrElement _tmp_91[1];
    FrElement _tmp_93[1];
    FrElement _sigValue_81[1];
    FrElement _tmp_97[1];
    FrElement i_2[1];
    FrElement _sigValue_82[1];
    FrElement _tmp_99[1];
    FrElement _tmp_98[1];
    FrElement _tmp_100[1];
    FrElement _sigValue_83[1];
    FrElement _tmp_101[1];
    FrElement _sigValue_84[1];
    FrElement _tmp_102[1];
    FrElement _sigValue_85[1];
    FrElement _sigValue_86[1];
    FrElement _tmp_103[1];
    FrElement _sigValue_87[1];
    FrElement _sigValue_88[1];
    FrElement _sigValue_89[1];
    FrElement _tmp_104[1];
    FrElement _tmp_105[1];
    FrElement _sigValue_90[1];
    FrElement _sigValue_91[1];
    FrElement _tmp_106[1];
    FrElement _tmp_107[1];
    FrElement _sigValue_92[1];
    FrElement _sigValue_93[1];
    FrElement _tmp_108[1];
    FrElement _tmp_109[1];
    FrElement _sigValue_94[1];
    FrElement _sigValue_95[1];
    FrElement _tmp_110[1];
    FrElement _tmp_111[1];
    FrElement _sigValue_96[1];
    FrElement _sigValue_97[1];
    FrElement _tmp_112[1];
    FrElement _tmp_113[1];
    FrElement _sigValue_98[1];
    FrElement _sigValue_99[1];
    FrElement _tmp_114[1];
    FrElement _tmp_115[1];
    int _legalCompliance_sigIdx_;
    int _dataHandlingPolicy_sigIdx_;
    int _misuseRecord_sigIdx_;
    int _compIdx;
    int _in_sigIdx_;
    int _entityType_sigIdx_;
    int _compIdx_1;
    int _in_sigIdx__1;
    int _compIdx_2;
    int _in_sigIdx__2;
    int _compIdx_3;
    int _in_sigIdx__3;
    int _compIdx_4;
    int _out_sigIdx_;
    int _isGov_sigIdx_;
    int _compIdx_5;
    int _out_sigIdx__1;
    int _isPolice_sigIdx_;
    int _compIdx_6;
    int _out_sigIdx__2;
    int _isEnterp_sigIdx_;
    int _compIdx_7;
    int _out_sigIdx__3;
    int _isResearch_sigIdx_;
    int _isGovOrPolice_sigIdx_;
    int _isOtherEntity_sigIdx_;
    int _compIdx_8;
    int _in_sigIdx__4;
    int _purpose_sigIdx_;
    int _compIdx_9;
    int _in_sigIdx__5;
    int _compIdx_10;
    int _in_sigIdx__6;
    int _compIdx_11;
    int _out_sigIdx__4;
    int _isCrime_sigIdx_;
    int _compIdx_12;
    int _out_sigIdx__5;
    int _isTraffic_sigIdx_;
    int _compIdx_13;
    int _out_sigIdx__6;
    int _isResearchP_sigIdx_;
    int _isOtherPurpose_sigIdx_;
    int _entityScore_sigIdx_;
    int _purposeScore_sigIdx_;
    int _legalScore_sigIdx_;
    int _policyScore_sigIdx_;
    int _misuseScore_sigIdx_;
    int _scoreCalc_sigIdx_;
    int _b_sigIdx_;
    int _offset_3;
    int _offset_5;
    int _offset_10;
    int _offset_12;
    int _offset_16;
    int _offset_17;
    int _offset_18;
    int _offset_19;
    int _offset_20;
    int _offset_21;
    int _offset_22;
    int _recomposed_sigIdx_;
    int _compIdx_14;
    int _xbits_sigIdx_;
    int _offset_26;
    int _offset_28;
    int _compIdx_15;
    int _xbits_sigIdx__1;
    int _offset_33;
    int _offset_35;
    int _compIdx_16;
    int _xbits_sigIdx__2;
    int _offset_42;
    int _offset_44;
    int _compIdx_17;
    int _xbits_sigIdx__3;
    int _offset_49;
    int _offset_51;
    int _compIdx_18;
    int _lt_sigIdx_;
    int _ge60_sigIdx_;
    int _compIdx_19;
    int _lt_sigIdx__1;
    int _ge80_sigIdx_;
    int _fullCond_sigIdx_;
    int _level2_sigIdx_;
    int _level1_sigIdx_;
    int _level0_sigIdx_;
    int _level_sigIdx_;
    Circom_Sizes _sigSizes_b;
    Circom_Sizes _sigSizes_xbits;
    Circom_Sizes _sigSizes_xbits_1;
    Circom_Sizes _sigSizes_xbits_2;
    Circom_Sizes _sigSizes_xbits_3;
    PFrElement _loopCond;
    PFrElement _loopCond_1;
    PFrElement _loopCond_2;
    Fr_copy(&(_tmp_69[0]), ctx->circuit->constants +1);
    Fr_copy(&(i[0]), ctx->circuit->constants +1);
    Fr_copy(&(_tmp_90[0]), ctx->circuit->constants +1);
    Fr_copy(&(i_1[0]), ctx->circuit->constants +1);
    Fr_copy(&(_tmp_97[0]), ctx->circuit->constants +1);
    Fr_copy(&(i_2[0]), ctx->circuit->constants +1);
    _legalCompliance_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xaaaeed8652ff55b5LL /* legalCompliance */);
    _dataHandlingPolicy_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x450f63bc8ba9d84eLL /* dataHandlingPolicy */);
    _misuseRecord_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x116bf540c7410dc2LL /* misuseRecord */);
    _entityType_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x723f446c06303a1aLL /* entityType */);
    _isGov_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x6f46c3fa21606cb7LL /* isGov */);
    _isPolice_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xf9d58738cf7d54ebLL /* isPolice */);
    _isEnterp_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x6ed8aab22e83b6b7LL /* isEnterp */);
    _isResearch_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x82faf3fd511f871cLL /* isResearch */);
    _isGovOrPolice_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x69c7d752bcb61a04LL /* isGovOrPolice */);
    _isOtherEntity_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x6e888f19b14534baLL /* isOtherEntity */);
    _purpose_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x4819bf2dd779d6c1LL /* purpose */);
    _isCrime_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x7f3d7a2ceaab7025LL /* isCrime */);
    _isTraffic_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x66ae3c83738a6cb6LL /* isTraffic */);
    _isResearchP_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xaff3e370d892e624LL /* isResearchP */);
    _isOtherPurpose_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x76867ca191437c81LL /* isOtherPurpose */);
    _entityScore_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xa7cb87533d1d7080LL /* entityScore */);
    _purposeScore_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc4d61b5c5e7d0e69LL /* purposeScore */);
    _legalScore_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xab8f2abda9f1ad90LL /* legalScore */);
    _policyScore_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc19d733569f190d3LL /* policyScore */);
    _misuseScore_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x429341dc777e212fLL /* misuseScore */);
    _scoreCalc_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xb3e5240149d611a4LL /* scoreCalc */);
    _b_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xaf63df4c8601f1a5LL /* b */);
    _recomposed_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x5885cf9f05a1c408LL /* recomposed */);
    _ge60_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x6808b671f06bea77LL /* ge60 */);
    _ge80_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x67d92271f0437e39LL /* ge80 */);
    _fullCond_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x48bfeacb2bc66f54LL /* fullCond */);
    _level2_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x2d4d4c099a73795dLL /* level2 */);
    _level1_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x2d4d49099a737444LL /* level1 */);
    _level0_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x2d4d4a099a7375f7LL /* level0 */);
    _level_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xe8ddc90a9d7c709dLL /* level */);
    _sigSizes_b = ctx->getSignalSizes(__cIdx, 0xaf63df4c8601f1a5LL /* b */);
    /* signal input entityType */
    /* signal input purpose */
    /* signal input legalCompliance */
    /* signal input dataHandlingPolicy */
    /* signal input misuseRecord */
    /* signal output level */
    /* legalCompliance * (legalCompliance - 1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _legalCompliance_sigIdx_, _sigValue, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _legalCompliance_sigIdx_, _sigValue_1, 1);
    Fr_sub(_tmp, _sigValue_1, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_1, _sigValue, _tmp);
    ctx->checkConstraint(__cIdx, _tmp_1, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:70:4");
    /* dataHandlingPolicy * (dataHandlingPolicy - 1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _dataHandlingPolicy_sigIdx_, _sigValue_2, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _dataHandlingPolicy_sigIdx_, _sigValue_3, 1);
    Fr_sub(_tmp_2, _sigValue_3, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_3, _sigValue_2, _tmp_2);
    ctx->checkConstraint(__cIdx, _tmp_3, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:71:4");
    /* misuseRecord * (misuseRecord - 1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _misuseRecord_sigIdx_, _sigValue_4, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _misuseRecord_sigIdx_, _sigValue_5, 1);
    Fr_sub(_tmp_4, _sigValue_5, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_5, _sigValue_4, _tmp_4);
    ctx->checkConstraint(__cIdx, _tmp_5, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:72:4");
    /* component e1 = IsZero() */
    /* e1.in <== entityType - 1 */
    _compIdx = ctx->getSubComponentOffset(__cIdx, 0x088e7b07b539b883LL /* e1 */);
    _in_sigIdx_ = ctx->getSignalOffset(_compIdx, 0x08b73807b55c4bbeLL /* in */);
    ctx->multiGetSignal(__cIdx, __cIdx, _entityType_sigIdx_, _sigValue_6, 1);
    Fr_sub(_tmp_6, _sigValue_6, (ctx->circuit->constants + 1));
    ctx->setSignal(__cIdx, _compIdx, _in_sigIdx_, _tmp_6);
    /* component e2 = IsZero() */
    /* e2.in <== entityType - 2 */
    _compIdx_1 = ctx->getSubComponentOffset(__cIdx, 0x088e7c07b539ba36LL /* e2 */);
    _in_sigIdx__1 = ctx->getSignalOffset(_compIdx_1, 0x08b73807b55c4bbeLL /* in */);
    ctx->multiGetSignal(__cIdx, __cIdx, _entityType_sigIdx_, _sigValue_7, 1);
    Fr_sub(_tmp_7, _sigValue_7, (ctx->circuit->constants + 2));
    ctx->setSignal(__cIdx, _compIdx_1, _in_sigIdx__1, _tmp_7);
    /* component e3 = IsZero() */
    /* e3.in <== entityType - 3 */
    _compIdx_2 = ctx->getSubComponentOffset(__cIdx, 0x088e7d07b539bbe9LL /* e3 */);
    _in_sigIdx__2 = ctx->getSignalOffset(_compIdx_2, 0x08b73807b55c4bbeLL /* in */);
    ctx->multiGetSignal(__cIdx, __cIdx, _entityType_sigIdx_, _sigValue_8, 1);
    Fr_sub(_tmp_8, _sigValue_8, (ctx->circuit->constants + 3));
    ctx->setSignal(__cIdx, _compIdx_2, _in_sigIdx__2, _tmp_8);
    /* component e4 = IsZero() */
    /* e4.in <== entityType - 4 */
    _compIdx_3 = ctx->getSubComponentOffset(__cIdx, 0x088e7e07b539bd9cLL /* e4 */);
    _in_sigIdx__3 = ctx->getSignalOffset(_compIdx_3, 0x08b73807b55c4bbeLL /* in */);
    ctx->multiGetSignal(__cIdx, __cIdx, _entityType_sigIdx_, _sigValue_9, 1);
    Fr_sub(_tmp_9, _sigValue_9, (ctx->circuit->constants + 4));
    ctx->setSignal(__cIdx, _compIdx_3, _in_sigIdx__3, _tmp_9);
    /* signal isGov */
    /* isGov      <== e1.out */
    _compIdx_4 = ctx->getSubComponentOffset(__cIdx, 0x088e7b07b539b883LL /* e1 */);
    _out_sigIdx_ = ctx->getSignalOffset(_compIdx_4, 0x19f79b1921bbcfffLL /* out */);
    ctx->multiGetSignal(__cIdx, _compIdx_4, _out_sigIdx_, _sigValue_10, 1);
    ctx->setSignal(__cIdx, __cIdx, _isGov_sigIdx_, _sigValue_10);
    /* signal isPolice */
    /* isPolice   <== e2.out */
    _compIdx_5 = ctx->getSubComponentOffset(__cIdx, 0x088e7c07b539ba36LL /* e2 */);
    _out_sigIdx__1 = ctx->getSignalOffset(_compIdx_5, 0x19f79b1921bbcfffLL /* out */);
    ctx->multiGetSignal(__cIdx, _compIdx_5, _out_sigIdx__1, _sigValue_11, 1);
    ctx->setSignal(__cIdx, __cIdx, _isPolice_sigIdx_, _sigValue_11);
    /* signal isEnterp */
    /* isEnterp   <== e3.out */
    _compIdx_6 = ctx->getSubComponentOffset(__cIdx, 0x088e7d07b539bbe9LL /* e3 */);
    _out_sigIdx__2 = ctx->getSignalOffset(_compIdx_6, 0x19f79b1921bbcfffLL /* out */);
    ctx->multiGetSignal(__cIdx, _compIdx_6, _out_sigIdx__2, _sigValue_12, 1);
    ctx->setSignal(__cIdx, __cIdx, _isEnterp_sigIdx_, _sigValue_12);
    /* signal isResearch */
    /* isResearch <== e4.out */
    _compIdx_7 = ctx->getSubComponentOffset(__cIdx, 0x088e7e07b539bd9cLL /* e4 */);
    _out_sigIdx__3 = ctx->getSignalOffset(_compIdx_7, 0x19f79b1921bbcfffLL /* out */);
    ctx->multiGetSignal(__cIdx, _compIdx_7, _out_sigIdx__3, _sigValue_13, 1);
    ctx->setSignal(__cIdx, __cIdx, _isResearch_sigIdx_, _sigValue_13);
    /* signal isGovOrPolice */
    /* isGovOrPolice <== isGov + isPolice - isGov * isPolice */
    ctx->multiGetSignal(__cIdx, __cIdx, _isGov_sigIdx_, _sigValue_14, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isPolice_sigIdx_, _sigValue_15, 1);
    Fr_add(_tmp_10, _sigValue_14, _sigValue_15);
    ctx->multiGetSignal(__cIdx, __cIdx, _isGov_sigIdx_, _sigValue_16, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isPolice_sigIdx_, _sigValue_17, 1);
    Fr_mul(_tmp_11, _sigValue_16, _sigValue_17);
    Fr_sub(_tmp_12, _tmp_10, _tmp_11);
    ctx->setSignal(__cIdx, __cIdx, _isGovOrPolice_sigIdx_, _tmp_12);
    /* signal isOtherEntity */
    /* isOtherEntity <== 1 - (isGovOrPolice + isEnterp + isResearch) */
    ctx->multiGetSignal(__cIdx, __cIdx, _isGovOrPolice_sigIdx_, _sigValue_18, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isEnterp_sigIdx_, _sigValue_19, 1);
    Fr_add(_tmp_13, _sigValue_18, _sigValue_19);
    ctx->multiGetSignal(__cIdx, __cIdx, _isResearch_sigIdx_, _sigValue_20, 1);
    Fr_add(_tmp_14, _tmp_13, _sigValue_20);
    Fr_sub(_tmp_15, (ctx->circuit->constants + 1), _tmp_14);
    ctx->setSignal(__cIdx, __cIdx, _isOtherEntity_sigIdx_, _tmp_15);
    /* isGov*(isGov-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _isGov_sigIdx_, _sigValue_21, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isGov_sigIdx_, _sigValue_22, 1);
    Fr_sub(_tmp_16, _sigValue_22, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_17, _sigValue_21, _tmp_16);
    ctx->checkConstraint(__cIdx, _tmp_17, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:89:4");
    /* isPolice*(isPolice-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _isPolice_sigIdx_, _sigValue_23, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isPolice_sigIdx_, _sigValue_24, 1);
    Fr_sub(_tmp_18, _sigValue_24, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_19, _sigValue_23, _tmp_18);
    ctx->checkConstraint(__cIdx, _tmp_19, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:90:4");
    /* isEnterp*(isEnterp-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _isEnterp_sigIdx_, _sigValue_25, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isEnterp_sigIdx_, _sigValue_26, 1);
    Fr_sub(_tmp_20, _sigValue_26, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_21, _sigValue_25, _tmp_20);
    ctx->checkConstraint(__cIdx, _tmp_21, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:91:4");
    /* isResearch*(isResearch-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _isResearch_sigIdx_, _sigValue_27, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isResearch_sigIdx_, _sigValue_28, 1);
    Fr_sub(_tmp_22, _sigValue_28, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_23, _sigValue_27, _tmp_22);
    ctx->checkConstraint(__cIdx, _tmp_23, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:92:4");
    /* isGovOrPolice*(isGovOrPolice-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _isGovOrPolice_sigIdx_, _sigValue_29, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isGovOrPolice_sigIdx_, _sigValue_30, 1);
    Fr_sub(_tmp_24, _sigValue_30, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_25, _sigValue_29, _tmp_24);
    ctx->checkConstraint(__cIdx, _tmp_25, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:93:4");
    /* isOtherEntity*(isOtherEntity-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _isOtherEntity_sigIdx_, _sigValue_31, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isOtherEntity_sigIdx_, _sigValue_32, 1);
    Fr_sub(_tmp_26, _sigValue_32, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_27, _sigValue_31, _tmp_26);
    ctx->checkConstraint(__cIdx, _tmp_27, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:94:4");
    /* component p1 = IsZero() */
    /* p1.in <== purpose - 1 */
    _compIdx_8 = ctx->getSubComponentOffset(__cIdx, 0x08d59707b575eabaLL /* p1 */);
    _in_sigIdx__4 = ctx->getSignalOffset(_compIdx_8, 0x08b73807b55c4bbeLL /* in */);
    ctx->multiGetSignal(__cIdx, __cIdx, _purpose_sigIdx_, _sigValue_33, 1);
    Fr_sub(_tmp_28, _sigValue_33, (ctx->circuit->constants + 1));
    ctx->setSignal(__cIdx, _compIdx_8, _in_sigIdx__4, _tmp_28);
    /* component p2 = IsZero() */
    /* p2.in <== purpose - 2 */
    _compIdx_9 = ctx->getSubComponentOffset(__cIdx, 0x08d59607b575e907LL /* p2 */);
    _in_sigIdx__5 = ctx->getSignalOffset(_compIdx_9, 0x08b73807b55c4bbeLL /* in */);
    ctx->multiGetSignal(__cIdx, __cIdx, _purpose_sigIdx_, _sigValue_34, 1);
    Fr_sub(_tmp_29, _sigValue_34, (ctx->circuit->constants + 2));
    ctx->setSignal(__cIdx, _compIdx_9, _in_sigIdx__5, _tmp_29);
    /* component p3 = IsZero() */
    /* p3.in <== purpose - 3 */
    _compIdx_10 = ctx->getSubComponentOffset(__cIdx, 0x08d59507b575e754LL /* p3 */);
    _in_sigIdx__6 = ctx->getSignalOffset(_compIdx_10, 0x08b73807b55c4bbeLL /* in */);
    ctx->multiGetSignal(__cIdx, __cIdx, _purpose_sigIdx_, _sigValue_35, 1);
    Fr_sub(_tmp_30, _sigValue_35, (ctx->circuit->constants + 3));
    ctx->setSignal(__cIdx, _compIdx_10, _in_sigIdx__6, _tmp_30);
    /* signal isCrime */
    /* isCrime     <== p1.out */
    _compIdx_11 = ctx->getSubComponentOffset(__cIdx, 0x08d59707b575eabaLL /* p1 */);
    _out_sigIdx__4 = ctx->getSignalOffset(_compIdx_11, 0x19f79b1921bbcfffLL /* out */);
    ctx->multiGetSignal(__cIdx, _compIdx_11, _out_sigIdx__4, _sigValue_36, 1);
    ctx->setSignal(__cIdx, __cIdx, _isCrime_sigIdx_, _sigValue_36);
    /* signal isTraffic */
    /* isTraffic   <== p2.out */
    _compIdx_12 = ctx->getSubComponentOffset(__cIdx, 0x08d59607b575e907LL /* p2 */);
    _out_sigIdx__5 = ctx->getSignalOffset(_compIdx_12, 0x19f79b1921bbcfffLL /* out */);
    ctx->multiGetSignal(__cIdx, _compIdx_12, _out_sigIdx__5, _sigValue_37, 1);
    ctx->setSignal(__cIdx, __cIdx, _isTraffic_sigIdx_, _sigValue_37);
    /* signal isResearchP */
    /* isResearchP <== p3.out */
    _compIdx_13 = ctx->getSubComponentOffset(__cIdx, 0x08d59507b575e754LL /* p3 */);
    _out_sigIdx__6 = ctx->getSignalOffset(_compIdx_13, 0x19f79b1921bbcfffLL /* out */);
    ctx->multiGetSignal(__cIdx, _compIdx_13, _out_sigIdx__6, _sigValue_38, 1);
    ctx->setSignal(__cIdx, __cIdx, _isResearchP_sigIdx_, _sigValue_38);
    /* signal isOtherPurpose */
    /* isOtherPurpose <== 1 - (isCrime + isTraffic + isResearchP) */
    ctx->multiGetSignal(__cIdx, __cIdx, _isCrime_sigIdx_, _sigValue_39, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isTraffic_sigIdx_, _sigValue_40, 1);
    Fr_add(_tmp_31, _sigValue_39, _sigValue_40);
    ctx->multiGetSignal(__cIdx, __cIdx, _isResearchP_sigIdx_, _sigValue_41, 1);
    Fr_add(_tmp_32, _tmp_31, _sigValue_41);
    Fr_sub(_tmp_33, (ctx->circuit->constants + 1), _tmp_32);
    ctx->setSignal(__cIdx, __cIdx, _isOtherPurpose_sigIdx_, _tmp_33);
    /* isCrime*(isCrime-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _isCrime_sigIdx_, _sigValue_42, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isCrime_sigIdx_, _sigValue_43, 1);
    Fr_sub(_tmp_34, _sigValue_43, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_35, _sigValue_42, _tmp_34);
    ctx->checkConstraint(__cIdx, _tmp_35, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:104:4");
    /* isTraffic*(isTraffic-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _isTraffic_sigIdx_, _sigValue_44, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isTraffic_sigIdx_, _sigValue_45, 1);
    Fr_sub(_tmp_36, _sigValue_45, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_37, _sigValue_44, _tmp_36);
    ctx->checkConstraint(__cIdx, _tmp_37, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:105:4");
    /* isResearchP*(isResearchP-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _isResearchP_sigIdx_, _sigValue_46, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isResearchP_sigIdx_, _sigValue_47, 1);
    Fr_sub(_tmp_38, _sigValue_47, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_39, _sigValue_46, _tmp_38);
    ctx->checkConstraint(__cIdx, _tmp_39, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:106:4");
    /* isOtherPurpose*(isOtherPurpose-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _isOtherPurpose_sigIdx_, _sigValue_48, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isOtherPurpose_sigIdx_, _sigValue_49, 1);
    Fr_sub(_tmp_40, _sigValue_49, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_41, _sigValue_48, _tmp_40);
    ctx->checkConstraint(__cIdx, _tmp_41, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:107:4");
    /* signal entityScore */
    /* entityScore  <== 35*isGovOrPolice + 20*isEnterp + 15*isResearch + 5*isOtherEntity */
    ctx->multiGetSignal(__cIdx, __cIdx, _isGovOrPolice_sigIdx_, _sigValue_50, 1);
    Fr_mul(_tmp_42, (ctx->circuit->constants + 5), _sigValue_50);
    ctx->multiGetSignal(__cIdx, __cIdx, _isEnterp_sigIdx_, _sigValue_51, 1);
    Fr_mul(_tmp_43, (ctx->circuit->constants + 6), _sigValue_51);
    Fr_add(_tmp_44, _tmp_42, _tmp_43);
    ctx->multiGetSignal(__cIdx, __cIdx, _isResearch_sigIdx_, _sigValue_52, 1);
    Fr_mul(_tmp_45, (ctx->circuit->constants + 7), _sigValue_52);
    Fr_add(_tmp_46, _tmp_44, _tmp_45);
    ctx->multiGetSignal(__cIdx, __cIdx, _isOtherEntity_sigIdx_, _sigValue_53, 1);
    Fr_mul(_tmp_47, (ctx->circuit->constants + 8), _sigValue_53);
    Fr_add(_tmp_48, _tmp_46, _tmp_47);
    ctx->setSignal(__cIdx, __cIdx, _entityScore_sigIdx_, _tmp_48);
    /* signal purposeScore */
    /* purposeScore <== 25*isCrime + 20*isTraffic + 15*isResearchP + 5*isOtherPurpose */
    ctx->multiGetSignal(__cIdx, __cIdx, _isCrime_sigIdx_, _sigValue_54, 1);
    Fr_mul(_tmp_49, (ctx->circuit->constants + 9), _sigValue_54);
    ctx->multiGetSignal(__cIdx, __cIdx, _isTraffic_sigIdx_, _sigValue_55, 1);
    Fr_mul(_tmp_50, (ctx->circuit->constants + 6), _sigValue_55);
    Fr_add(_tmp_51, _tmp_49, _tmp_50);
    ctx->multiGetSignal(__cIdx, __cIdx, _isResearchP_sigIdx_, _sigValue_56, 1);
    Fr_mul(_tmp_52, (ctx->circuit->constants + 7), _sigValue_56);
    Fr_add(_tmp_53, _tmp_51, _tmp_52);
    ctx->multiGetSignal(__cIdx, __cIdx, _isOtherPurpose_sigIdx_, _sigValue_57, 1);
    Fr_mul(_tmp_54, (ctx->circuit->constants + 8), _sigValue_57);
    Fr_add(_tmp_55, _tmp_53, _tmp_54);
    ctx->setSignal(__cIdx, __cIdx, _purposeScore_sigIdx_, _tmp_55);
    /* signal legalScore */
    /* legalScore   <== 15*legalCompliance */
    ctx->multiGetSignal(__cIdx, __cIdx, _legalCompliance_sigIdx_, _sigValue_58, 1);
    Fr_mul(_tmp_56, (ctx->circuit->constants + 7), _sigValue_58);
    ctx->setSignal(__cIdx, __cIdx, _legalScore_sigIdx_, _tmp_56);
    /* signal policyScore */
    /* policyScore  <== 15*dataHandlingPolicy */
    ctx->multiGetSignal(__cIdx, __cIdx, _dataHandlingPolicy_sigIdx_, _sigValue_59, 1);
    Fr_mul(_tmp_57, (ctx->circuit->constants + 7), _sigValue_59);
    ctx->setSignal(__cIdx, __cIdx, _policyScore_sigIdx_, _tmp_57);
    /* signal misuseScore */
    /* misuseScore  <== 10 - 20*misuseRecord */
    ctx->multiGetSignal(__cIdx, __cIdx, _misuseRecord_sigIdx_, _sigValue_60, 1);
    Fr_mul(_tmp_58, (ctx->circuit->constants + 6), _sigValue_60);
    Fr_sub(_tmp_59, (ctx->circuit->constants + 10), _tmp_58);
    ctx->setSignal(__cIdx, __cIdx, _misuseScore_sigIdx_, _tmp_59);
    /* signal scoreCalc */
    /* scoreCalc <== entityScore + purposeScore + legalScore + policyScore + misuseScore */
    ctx->multiGetSignal(__cIdx, __cIdx, _entityScore_sigIdx_, _sigValue_61, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _purposeScore_sigIdx_, _sigValue_62, 1);
    Fr_add(_tmp_60, _sigValue_61, _sigValue_62);
    ctx->multiGetSignal(__cIdx, __cIdx, _legalScore_sigIdx_, _sigValue_63, 1);
    Fr_add(_tmp_61, _tmp_60, _sigValue_63);
    ctx->multiGetSignal(__cIdx, __cIdx, _policyScore_sigIdx_, _sigValue_64, 1);
    Fr_add(_tmp_62, _tmp_61, _sigValue_64);
    ctx->multiGetSignal(__cIdx, __cIdx, _misuseScore_sigIdx_, _sigValue_65, 1);
    Fr_add(_tmp_63, _tmp_62, _sigValue_65);
    ctx->setSignal(__cIdx, __cIdx, _scoreCalc_sigIdx_, _tmp_63);
    /* signal b[7] */
    /* for (var i = 0;i < 7;i++) */
    /* b[i] * (b[i] - 1) === 0 */
    _offset_3 = _b_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_3, _sigValue_66, 1);
    _offset_5 = _b_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_5, _sigValue_67, 1);
    Fr_sub(_tmp_65, _sigValue_67, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_66, _sigValue_66, _tmp_65);
    ctx->checkConstraint(__cIdx, _tmp_66, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:121:34");
    _loopCond = _tmp_69;
    while (Fr_isTrue(_loopCond)) {
        /* b[i] * (b[i] - 1) === 0 */
        _offset_10 = _b_sigIdx_ + Fr_toInt(i)*_sigSizes_b[1];
        ctx->multiGetSignal(__cIdx, __cIdx, _offset_10, _sigValue_68, 1);
        _offset_12 = _b_sigIdx_ + Fr_toInt(i)*_sigSizes_b[1];
        ctx->multiGetSignal(__cIdx, __cIdx, _offset_12, _sigValue_69, 1);
        Fr_sub(_tmp_70, _sigValue_69, (ctx->circuit->constants + 1));
        Fr_mul(_tmp_71, _sigValue_68, _tmp_70);
        ctx->checkConstraint(__cIdx, _tmp_71, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:121:34");
        Fr_copyn(_tmp_73, i, 1);
        Fr_add(_tmp_72, i, (ctx->circuit->constants + 1));
        Fr_copyn(i, _tmp_72, 1);
        Fr_lt(_tmp_74, i, (ctx->circuit->constants + 11));
        _loopCond = _tmp_74;
    }
    /* signal recomposed */
    /* recomposed <== b[0] + 2*b[1] + 4*b[2] + 8*b[3] + 16*b[4] + 32*b[5] + 64*b[6] */
    _offset_16 = _b_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_16, _sigValue_70, 1);
    _offset_17 = _b_sigIdx_ + 1*_sigSizes_b[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_17, _sigValue_71, 1);
    Fr_mul(_tmp_75, (ctx->circuit->constants + 2), _sigValue_71);
    Fr_add(_tmp_76, _sigValue_70, _tmp_75);
    _offset_18 = _b_sigIdx_ + 2*_sigSizes_b[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_18, _sigValue_72, 1);
    Fr_mul(_tmp_77, (ctx->circuit->constants + 4), _sigValue_72);
    Fr_add(_tmp_78, _tmp_76, _tmp_77);
    _offset_19 = _b_sigIdx_ + 3*_sigSizes_b[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_19, _sigValue_73, 1);
    Fr_mul(_tmp_79, (ctx->circuit->constants + 12), _sigValue_73);
    Fr_add(_tmp_80, _tmp_78, _tmp_79);
    _offset_20 = _b_sigIdx_ + 4*_sigSizes_b[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_20, _sigValue_74, 1);
    Fr_mul(_tmp_81, (ctx->circuit->constants + 13), _sigValue_74);
    Fr_add(_tmp_82, _tmp_80, _tmp_81);
    _offset_21 = _b_sigIdx_ + 5*_sigSizes_b[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_21, _sigValue_75, 1);
    Fr_mul(_tmp_83, (ctx->circuit->constants + 14), _sigValue_75);
    Fr_add(_tmp_84, _tmp_82, _tmp_83);
    _offset_22 = _b_sigIdx_ + 6*_sigSizes_b[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_22, _sigValue_76, 1);
    Fr_mul(_tmp_85, (ctx->circuit->constants + 15), _sigValue_76);
    Fr_add(_tmp_86, _tmp_84, _tmp_85);
    ctx->setSignal(__cIdx, __cIdx, _recomposed_sigIdx_, _tmp_86);
    /* scoreCalc === recomposed */
    ctx->multiGetSignal(__cIdx, __cIdx, _scoreCalc_sigIdx_, _sigValue_77, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _recomposed_sigIdx_, _sigValue_78, 1);
    ctx->checkConstraint(__cIdx, _sigValue_77, _sigValue_78, "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:126:4");
    /* component lt60 = LessThanConst7(0,1,1,1,1,0,0) */
    /* for (var i = 0;i < 7;i++) */
    /* lt60.xbits[i] <== b[i] */
    _compIdx_14 = ctx->getSubComponentOffset(__cIdx, 0xb9cde7adf70120c3LL /* lt60 */);
    _xbits_sigIdx_ = ctx->getSignalOffset(_compIdx_14, 0x5c2ca035e26da383LL /* xbits */);
    _sigSizes_xbits = ctx->getSignalSizes(_compIdx_14, 0x5c2ca035e26da383LL /* xbits */);
    _offset_26 = _xbits_sigIdx_;
    _offset_28 = _b_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_28, _sigValue_79, 1);
    ctx->setSignal(__cIdx, _compIdx_14, _offset_26, _sigValue_79);
    _loopCond_1 = _tmp_90;
    while (Fr_isTrue(_loopCond_1)) {
        /* lt60.xbits[i] <== b[i] */
        _compIdx_15 = ctx->getSubComponentOffset(__cIdx, 0xb9cde7adf70120c3LL /* lt60 */);
        _xbits_sigIdx__1 = ctx->getSignalOffset(_compIdx_15, 0x5c2ca035e26da383LL /* xbits */);
        _sigSizes_xbits_1 = ctx->getSignalSizes(_compIdx_15, 0x5c2ca035e26da383LL /* xbits */);
        _offset_33 = _xbits_sigIdx__1 + Fr_toInt(i_1)*_sigSizes_xbits_1[1];
        _offset_35 = _b_sigIdx_ + Fr_toInt(i_1)*_sigSizes_b[1];
        ctx->multiGetSignal(__cIdx, __cIdx, _offset_35, _sigValue_80, 1);
        ctx->setSignal(__cIdx, _compIdx_15, _offset_33, _sigValue_80);
        Fr_copyn(_tmp_92, i_1, 1);
        Fr_add(_tmp_91, i_1, (ctx->circuit->constants + 1));
        Fr_copyn(i_1, _tmp_91, 1);
        Fr_lt(_tmp_93, i_1, (ctx->circuit->constants + 11));
        _loopCond_1 = _tmp_93;
    }
    /* component lt80 = LessThanConst7(1,0,1,0,0,0,0) */
    /* for (var i = 0;i < 7;i++) */
    /* lt80.xbits[i] <== b[i] */
    _compIdx_16 = ctx->getSubComponentOffset(__cIdx, 0xb9b983adf6efcdcdLL /* lt80 */);
    _xbits_sigIdx__2 = ctx->getSignalOffset(_compIdx_16, 0x5c2ca035e26da383LL /* xbits */);
    _sigSizes_xbits_2 = ctx->getSignalSizes(_compIdx_16, 0x5c2ca035e26da383LL /* xbits */);
    _offset_42 = _xbits_sigIdx__2;
    _offset_44 = _b_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_44, _sigValue_81, 1);
    ctx->setSignal(__cIdx, _compIdx_16, _offset_42, _sigValue_81);
    _loopCond_2 = _tmp_97;
    while (Fr_isTrue(_loopCond_2)) {
        /* lt80.xbits[i] <== b[i] */
        _compIdx_17 = ctx->getSubComponentOffset(__cIdx, 0xb9b983adf6efcdcdLL /* lt80 */);
        _xbits_sigIdx__3 = ctx->getSignalOffset(_compIdx_17, 0x5c2ca035e26da383LL /* xbits */);
        _sigSizes_xbits_3 = ctx->getSignalSizes(_compIdx_17, 0x5c2ca035e26da383LL /* xbits */);
        _offset_49 = _xbits_sigIdx__3 + Fr_toInt(i_2)*_sigSizes_xbits_3[1];
        _offset_51 = _b_sigIdx_ + Fr_toInt(i_2)*_sigSizes_b[1];
        ctx->multiGetSignal(__cIdx, __cIdx, _offset_51, _sigValue_82, 1);
        ctx->setSignal(__cIdx, _compIdx_17, _offset_49, _sigValue_82);
        Fr_copyn(_tmp_99, i_2, 1);
        Fr_add(_tmp_98, i_2, (ctx->circuit->constants + 1));
        Fr_copyn(i_2, _tmp_98, 1);
        Fr_lt(_tmp_100, i_2, (ctx->circuit->constants + 11));
        _loopCond_2 = _tmp_100;
    }
    /* signal ge60 */
    /* ge60 <== 1 - lt60.lt */
    _compIdx_18 = ctx->getSubComponentOffset(__cIdx, 0xb9cde7adf70120c3LL /* lt60 */);
    _lt_sigIdx_ = ctx->getSignalOffset(_compIdx_18, 0x08ad5407b55426cdLL /* lt */);
    ctx->multiGetSignal(__cIdx, _compIdx_18, _lt_sigIdx_, _sigValue_83, 1);
    Fr_sub(_tmp_101, (ctx->circuit->constants + 1), _sigValue_83);
    ctx->setSignal(__cIdx, __cIdx, _ge60_sigIdx_, _tmp_101);
    /* signal ge80 */
    /* ge80 <== 1 - lt80.lt */
    _compIdx_19 = ctx->getSubComponentOffset(__cIdx, 0xb9b983adf6efcdcdLL /* lt80 */);
    _lt_sigIdx__1 = ctx->getSignalOffset(_compIdx_19, 0x08ad5407b55426cdLL /* lt */);
    ctx->multiGetSignal(__cIdx, _compIdx_19, _lt_sigIdx__1, _sigValue_84, 1);
    Fr_sub(_tmp_102, (ctx->circuit->constants + 1), _sigValue_84);
    ctx->setSignal(__cIdx, __cIdx, _ge80_sigIdx_, _tmp_102);
    /* signal fullCond */
    /* fullCond <== ge80 * isGovOrPolice */
    ctx->multiGetSignal(__cIdx, __cIdx, _ge80_sigIdx_, _sigValue_85, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _isGovOrPolice_sigIdx_, _sigValue_86, 1);
    Fr_mul(_tmp_103, _sigValue_85, _sigValue_86);
    ctx->setSignal(__cIdx, __cIdx, _fullCond_sigIdx_, _tmp_103);
    /* signal level2 */
    /* level2 <== fullCond */
    ctx->multiGetSignal(__cIdx, __cIdx, _fullCond_sigIdx_, _sigValue_87, 1);
    ctx->setSignal(__cIdx, __cIdx, _level2_sigIdx_, _sigValue_87);
    /* signal level1 */
    /* level1 <== ge60 * (1 - level2) */
    ctx->multiGetSignal(__cIdx, __cIdx, _ge60_sigIdx_, _sigValue_88, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _level2_sigIdx_, _sigValue_89, 1);
    Fr_sub(_tmp_104, (ctx->circuit->constants + 1), _sigValue_89);
    Fr_mul(_tmp_105, _sigValue_88, _tmp_104);
    ctx->setSignal(__cIdx, __cIdx, _level1_sigIdx_, _tmp_105);
    /* signal level0 */
    /* level0 <== 1 - (level2 + level1) */
    ctx->multiGetSignal(__cIdx, __cIdx, _level2_sigIdx_, _sigValue_90, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _level1_sigIdx_, _sigValue_91, 1);
    Fr_add(_tmp_106, _sigValue_90, _sigValue_91);
    Fr_sub(_tmp_107, (ctx->circuit->constants + 1), _tmp_106);
    ctx->setSignal(__cIdx, __cIdx, _level0_sigIdx_, _tmp_107);
    /* level0*(level0-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _level0_sigIdx_, _sigValue_92, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _level0_sigIdx_, _sigValue_93, 1);
    Fr_sub(_tmp_108, _sigValue_93, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_109, _sigValue_92, _tmp_108);
    ctx->checkConstraint(__cIdx, _tmp_109, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:147:4");
    /* level1*(level1-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _level1_sigIdx_, _sigValue_94, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _level1_sigIdx_, _sigValue_95, 1);
    Fr_sub(_tmp_110, _sigValue_95, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_111, _sigValue_94, _tmp_110);
    ctx->checkConstraint(__cIdx, _tmp_111, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:147:29");
    /* level2*(level2-1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _level2_sigIdx_, _sigValue_96, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _level2_sigIdx_, _sigValue_97, 1);
    Fr_sub(_tmp_112, _sigValue_97, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_113, _sigValue_96, _tmp_112);
    ctx->checkConstraint(__cIdx, _tmp_113, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:147:54");
    /* level <== level1 + 2*level2 */
    ctx->multiGetSignal(__cIdx, __cIdx, _level1_sigIdx_, _sigValue_98, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _level2_sigIdx_, _sigValue_99, 1);
    Fr_mul(_tmp_114, (ctx->circuit->constants + 2), _sigValue_99);
    Fr_add(_tmp_115, _sigValue_98, _tmp_114);
    ctx->setSignal(__cIdx, __cIdx, _level_sigIdx_, _tmp_115);
    ctx->finished(__cIdx);
}
/*
IsZero
*/
void IsZero_0a2b8515b81b5ef3(Circom_CalcWit *ctx, int __cIdx) {
    FrElement _sigValue[1];
    FrElement _sigValue_1[1];
    FrElement _tmp[1];
    FrElement _tmp_1[1];
    FrElement _sigValue_2[1];
    FrElement _sigValue_3[1];
    FrElement _tmp_2[1];
    FrElement _sigValue_4[1];
    FrElement _tmp_3[1];
    FrElement _sigValue_5[1];
    FrElement _sigValue_6[1];
    FrElement _tmp_4[1];
    int _out_sigIdx_;
    int _in_sigIdx_;
    int _inv_sigIdx_;
    _out_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x19f79b1921bbcfffLL /* out */);
    _in_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x08b73807b55c4bbeLL /* in */);
    _inv_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x2b9ffd192bd4c4d8LL /* inv */);
    /* signal input in */
    /* signal output out */
    /* signal inv */
    /* out * (out - 1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _out_sigIdx_, _sigValue, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _out_sigIdx_, _sigValue_1, 1);
    Fr_sub(_tmp, _sigValue_1, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_1, _sigValue, _tmp);
    ctx->checkConstraint(__cIdx, _tmp_1, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:7:4");
    /* in * out === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _in_sigIdx_, _sigValue_2, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _out_sigIdx_, _sigValue_3, 1);
    Fr_mul(_tmp_2, _sigValue_2, _sigValue_3);
    ctx->checkConstraint(__cIdx, _tmp_2, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:8:4");
    /* (1 - out) === in * inv */
    ctx->multiGetSignal(__cIdx, __cIdx, _out_sigIdx_, _sigValue_4, 1);
    Fr_sub(_tmp_3, (ctx->circuit->constants + 1), _sigValue_4);
    ctx->multiGetSignal(__cIdx, __cIdx, _in_sigIdx_, _sigValue_5, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _inv_sigIdx_, _sigValue_6, 1);
    Fr_mul(_tmp_4, _sigValue_5, _sigValue_6);
    ctx->checkConstraint(__cIdx, _tmp_3, _tmp_4, "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:9:4");
    ctx->finished(__cIdx);
}
/*
LessThanConst7
k0=0
k1=0
k2=1
k3=1
k4=1
k5=1
k6=0
*/
void LessThanConst7_62c13aa59cd33892(Circom_CalcWit *ctx, int __cIdx) {
    FrElement _sigValue[1];
    FrElement _sigValue_1[1];
    FrElement _tmp_1[1];
    FrElement _tmp_2[1];
    FrElement _tmp_5[1];
    FrElement i[1];
    FrElement _sigValue_2[1];
    FrElement _sigValue_3[1];
    FrElement _tmp_6[1];
    FrElement _tmp_7[1];
    FrElement _tmp_9[1];
    FrElement _tmp_8[1];
    FrElement _tmp_10[1];
    FrElement _sigValue_4[1];
    FrElement _tmp_11[1];
    FrElement _sigValue_5[1];
    FrElement _tmp_12[1];
    FrElement _tmp_13[1];
    FrElement _tmp_14[1];
    FrElement _sigValue_6[1];
    FrElement _sigValue_7[1];
    FrElement _tmp_15[1];
    FrElement _tmp_16[1];
    FrElement _tmp_17[1];
    FrElement _sigValue_8[1];
    FrElement _sigValue_9[1];
    FrElement _tmp_18[1];
    FrElement _tmp_19[1];
    FrElement _sigValue_10[1];
    FrElement _tmp_20[1];
    FrElement _sigValue_11[1];
    FrElement _tmp_21[1];
    FrElement _tmp_22[1];
    FrElement _tmp_23[1];
    FrElement _sigValue_12[1];
    FrElement _sigValue_13[1];
    FrElement _tmp_24[1];
    FrElement _tmp_25[1];
    FrElement _tmp_26[1];
    FrElement _sigValue_14[1];
    FrElement _sigValue_15[1];
    FrElement _tmp_27[1];
    FrElement _tmp_28[1];
    FrElement _sigValue_16[1];
    FrElement _tmp_29[1];
    FrElement _sigValue_17[1];
    FrElement _tmp_30[1];
    FrElement _tmp_31[1];
    FrElement _tmp_32[1];
    FrElement _sigValue_18[1];
    FrElement _sigValue_19[1];
    FrElement _tmp_33[1];
    FrElement _tmp_34[1];
    FrElement _tmp_35[1];
    FrElement _sigValue_20[1];
    FrElement _sigValue_21[1];
    FrElement _tmp_36[1];
    FrElement _tmp_37[1];
    FrElement _sigValue_22[1];
    FrElement _tmp_38[1];
    FrElement _sigValue_23[1];
    FrElement _tmp_39[1];
    FrElement _tmp_40[1];
    FrElement _tmp_41[1];
    FrElement _sigValue_24[1];
    FrElement _sigValue_25[1];
    FrElement _tmp_42[1];
    FrElement _tmp_43[1];
    FrElement _tmp_44[1];
    FrElement _sigValue_26[1];
    FrElement _sigValue_27[1];
    FrElement _tmp_45[1];
    FrElement _tmp_46[1];
    FrElement _sigValue_28[1];
    FrElement _tmp_47[1];
    FrElement _sigValue_29[1];
    FrElement _tmp_48[1];
    FrElement _tmp_49[1];
    FrElement _tmp_50[1];
    FrElement _sigValue_30[1];
    FrElement _sigValue_31[1];
    FrElement _tmp_51[1];
    FrElement _tmp_52[1];
    FrElement _tmp_53[1];
    FrElement _sigValue_32[1];
    FrElement _sigValue_33[1];
    FrElement _tmp_54[1];
    FrElement _tmp_55[1];
    FrElement _sigValue_34[1];
    FrElement _tmp_56[1];
    FrElement _sigValue_35[1];
    FrElement _tmp_57[1];
    FrElement _tmp_58[1];
    FrElement _tmp_59[1];
    FrElement _sigValue_36[1];
    FrElement _sigValue_37[1];
    FrElement _tmp_60[1];
    FrElement _tmp_61[1];
    FrElement _tmp_62[1];
    FrElement _sigValue_38[1];
    FrElement _sigValue_39[1];
    FrElement _tmp_63[1];
    FrElement _tmp_64[1];
    FrElement _sigValue_40[1];
    FrElement _tmp_65[1];
    FrElement _sigValue_41[1];
    FrElement _tmp_66[1];
    FrElement _tmp_67[1];
    FrElement _tmp_68[1];
    FrElement _sigValue_42[1];
    FrElement _sigValue_43[1];
    FrElement _tmp_69[1];
    FrElement _tmp_70[1];
    FrElement _tmp_71[1];
    FrElement _sigValue_44[1];
    FrElement _sigValue_45[1];
    FrElement _tmp_72[1];
    FrElement _sigValue_46[1];
    FrElement _tmp_73[1];
    FrElement _sigValue_47[1];
    FrElement _tmp_74[1];
    FrElement _sigValue_48[1];
    FrElement _tmp_75[1];
    FrElement _sigValue_49[1];
    FrElement _tmp_76[1];
    FrElement _sigValue_50[1];
    FrElement _tmp_77[1];
    FrElement _sigValue_51[1];
    FrElement _sigValue_52[1];
    FrElement _tmp_78[1];
    FrElement _tmp_79[1];
    int _xbits_sigIdx_;
    int _offset_3;
    int _offset_5;
    int _offset_10;
    int _offset_12;
    int _eq6_sigIdx_;
    int _offset_16;
    int _offset_18;
    int _xor6_sigIdx_;
    int _offset_20;
    int _less6_sigIdx_;
    int _eq5_sigIdx_;
    int _offset_22;
    int _offset_24;
    int _xor5_sigIdx_;
    int _offset_26;
    int _less5_sigIdx_;
    int _eq4_sigIdx_;
    int _offset_28;
    int _offset_30;
    int _xor4_sigIdx_;
    int _offset_32;
    int _less4_sigIdx_;
    int _eq3_sigIdx_;
    int _offset_34;
    int _offset_36;
    int _xor3_sigIdx_;
    int _offset_38;
    int _less3_sigIdx_;
    int _eq2_sigIdx_;
    int _offset_40;
    int _offset_42;
    int _xor2_sigIdx_;
    int _offset_44;
    int _less2_sigIdx_;
    int _eq1_sigIdx_;
    int _offset_46;
    int _offset_48;
    int _xor1_sigIdx_;
    int _offset_50;
    int _less1_sigIdx_;
    int _eq0_sigIdx_;
    int _offset_52;
    int _offset_54;
    int _xor0_sigIdx_;
    int _offset_56;
    int _less0_sigIdx_;
    int _lt_sigIdx_;
    Circom_Sizes _sigSizes_xbits;
    PFrElement _loopCond;
    Fr_copy(&(_tmp_5[0]), ctx->circuit->constants +1);
    Fr_copy(&(i[0]), ctx->circuit->constants +1);
    _xbits_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x5c2ca035e26da383LL /* xbits */);
    _eq6_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa4318f05c114fLL /* eq6 */);
    _xor6_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fa95455aa6f98LL /* xor6 */);
    _less6_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e220a8c6b512aLL /* less6 */);
    _eq5_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa4418f05c1302LL /* eq5 */);
    _xor5_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fac5455aa74b1LL /* xor5 */);
    _less5_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e210a8c6b4f77LL /* less5 */);
    _eq4_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa4518f05c14b5LL /* eq4 */);
    _xor4_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fab5455aa72feLL /* xor4 */);
    _less4_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e200a8c6b4dc4LL /* less4 */);
    _eq3_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa3e18f05c08d0LL /* eq3 */);
    _xor3_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fae5455aa7817LL /* xor3 */);
    _less3_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e1f0a8c6b4c11LL /* less3 */);
    _eq2_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa3f18f05c0a83LL /* eq2 */);
    _xor2_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fad5455aa7664LL /* xor2 */);
    _less2_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e1e0a8c6b4a5eLL /* less2 */);
    _eq1_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa4018f05c0c36LL /* eq1 */);
    _xor1_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fb05455aa7b7dLL /* xor1 */);
    _less1_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e1d0a8c6b48abLL /* less1 */);
    _eq0_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa4118f05c0de9LL /* eq0 */);
    _xor0_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946faf5455aa79caLL /* xor0 */);
    _less0_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e1c0a8c6b46f8LL /* less0 */);
    _lt_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x08ad5407b55426cdLL /* lt */);
    _sigSizes_xbits = ctx->getSignalSizes(__cIdx, 0x5c2ca035e26da383LL /* xbits */);
    /* signal input xbits[7] */
    /* signal output lt */
    /* for (var i = 0;i < 7;i++) */
    /* xbits[i] * (xbits[i] - 1) === 0 */
    _offset_3 = _xbits_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_3, _sigValue, 1);
    _offset_5 = _xbits_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_5, _sigValue_1, 1);
    Fr_sub(_tmp_1, _sigValue_1, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_2, _sigValue, _tmp_1);
    ctx->checkConstraint(__cIdx, _tmp_2, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:20:8");
    _loopCond = _tmp_5;
    while (Fr_isTrue(_loopCond)) {
        /* xbits[i] * (xbits[i] - 1) === 0 */
        _offset_10 = _xbits_sigIdx_ + Fr_toInt(i)*_sigSizes_xbits[1];
        ctx->multiGetSignal(__cIdx, __cIdx, _offset_10, _sigValue_2, 1);
        _offset_12 = _xbits_sigIdx_ + Fr_toInt(i)*_sigSizes_xbits[1];
        ctx->multiGetSignal(__cIdx, __cIdx, _offset_12, _sigValue_3, 1);
        Fr_sub(_tmp_6, _sigValue_3, (ctx->circuit->constants + 1));
        Fr_mul(_tmp_7, _sigValue_2, _tmp_6);
        ctx->checkConstraint(__cIdx, _tmp_7, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:20:8");
        Fr_copyn(_tmp_9, i, 1);
        Fr_add(_tmp_8, i, (ctx->circuit->constants + 1));
        Fr_copyn(i, _tmp_8, 1);
        Fr_lt(_tmp_10, i, (ctx->circuit->constants + 11));
        _loopCond = _tmp_10;
    }
    /* signal eq6 */
    /* eq6 <== 1 */
    ctx->setSignal(__cIdx, __cIdx, _eq6_sigIdx_, (ctx->circuit->constants + 1));
    /* signal xor6 */
    /* xor6 <== xbits[6] + k6 - 2*xbits[6]*k6 */
    _offset_16 = _xbits_sigIdx_ + 6*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_16, _sigValue_4, 1);
    Fr_add(_tmp_11, _sigValue_4, (ctx->circuit->constants + 0));
    _offset_18 = _xbits_sigIdx_ + 6*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_18, _sigValue_5, 1);
    Fr_mul(_tmp_12, (ctx->circuit->constants + 2), _sigValue_5);
    Fr_mul(_tmp_13, _tmp_12, (ctx->circuit->constants + 0));
    Fr_sub(_tmp_14, _tmp_11, _tmp_13);
    ctx->setSignal(__cIdx, __cIdx, _xor6_sigIdx_, _tmp_14);
    /* signal less6 */
    /* less6 <== eq6 * ((1 - xbits[6]) * k6) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq6_sigIdx_, _sigValue_6, 1);
    _offset_20 = _xbits_sigIdx_ + 6*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_20, _sigValue_7, 1);
    Fr_sub(_tmp_15, (ctx->circuit->constants + 1), _sigValue_7);
    Fr_mul(_tmp_16, _tmp_15, (ctx->circuit->constants + 0));
    Fr_mul(_tmp_17, _sigValue_6, _tmp_16);
    ctx->setSignal(__cIdx, __cIdx, _less6_sigIdx_, _tmp_17);
    /* signal eq5 */
    /* eq5  <== eq6 * (1 - xor6) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq6_sigIdx_, _sigValue_8, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor6_sigIdx_, _sigValue_9, 1);
    Fr_sub(_tmp_18, (ctx->circuit->constants + 1), _sigValue_9);
    Fr_mul(_tmp_19, _sigValue_8, _tmp_18);
    ctx->setSignal(__cIdx, __cIdx, _eq5_sigIdx_, _tmp_19);
    /* signal xor5 */
    /* xor5 <== xbits[5] + k5 - 2*xbits[5]*k5 */
    _offset_22 = _xbits_sigIdx_ + 5*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_22, _sigValue_10, 1);
    Fr_add(_tmp_20, _sigValue_10, (ctx->circuit->constants + 1));
    _offset_24 = _xbits_sigIdx_ + 5*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_24, _sigValue_11, 1);
    Fr_mul(_tmp_21, (ctx->circuit->constants + 2), _sigValue_11);
    Fr_mul(_tmp_22, _tmp_21, (ctx->circuit->constants + 1));
    Fr_sub(_tmp_23, _tmp_20, _tmp_22);
    ctx->setSignal(__cIdx, __cIdx, _xor5_sigIdx_, _tmp_23);
    /* signal less5 */
    /* less5 <== eq5 * ((1 - xbits[5]) * k5) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq5_sigIdx_, _sigValue_12, 1);
    _offset_26 = _xbits_sigIdx_ + 5*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_26, _sigValue_13, 1);
    Fr_sub(_tmp_24, (ctx->circuit->constants + 1), _sigValue_13);
    Fr_mul(_tmp_25, _tmp_24, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_26, _sigValue_12, _tmp_25);
    ctx->setSignal(__cIdx, __cIdx, _less5_sigIdx_, _tmp_26);
    /* signal eq4 */
    /* eq4  <== eq5 * (1 - xor5) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq5_sigIdx_, _sigValue_14, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor5_sigIdx_, _sigValue_15, 1);
    Fr_sub(_tmp_27, (ctx->circuit->constants + 1), _sigValue_15);
    Fr_mul(_tmp_28, _sigValue_14, _tmp_27);
    ctx->setSignal(__cIdx, __cIdx, _eq4_sigIdx_, _tmp_28);
    /* signal xor4 */
    /* xor4 <== xbits[4] + k4 - 2*xbits[4]*k4 */
    _offset_28 = _xbits_sigIdx_ + 4*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_28, _sigValue_16, 1);
    Fr_add(_tmp_29, _sigValue_16, (ctx->circuit->constants + 1));
    _offset_30 = _xbits_sigIdx_ + 4*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_30, _sigValue_17, 1);
    Fr_mul(_tmp_30, (ctx->circuit->constants + 2), _sigValue_17);
    Fr_mul(_tmp_31, _tmp_30, (ctx->circuit->constants + 1));
    Fr_sub(_tmp_32, _tmp_29, _tmp_31);
    ctx->setSignal(__cIdx, __cIdx, _xor4_sigIdx_, _tmp_32);
    /* signal less4 */
    /* less4 <== eq4 * ((1 - xbits[4]) * k4) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq4_sigIdx_, _sigValue_18, 1);
    _offset_32 = _xbits_sigIdx_ + 4*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_32, _sigValue_19, 1);
    Fr_sub(_tmp_33, (ctx->circuit->constants + 1), _sigValue_19);
    Fr_mul(_tmp_34, _tmp_33, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_35, _sigValue_18, _tmp_34);
    ctx->setSignal(__cIdx, __cIdx, _less4_sigIdx_, _tmp_35);
    /* signal eq3 */
    /* eq3  <== eq4 * (1 - xor4) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq4_sigIdx_, _sigValue_20, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor4_sigIdx_, _sigValue_21, 1);
    Fr_sub(_tmp_36, (ctx->circuit->constants + 1), _sigValue_21);
    Fr_mul(_tmp_37, _sigValue_20, _tmp_36);
    ctx->setSignal(__cIdx, __cIdx, _eq3_sigIdx_, _tmp_37);
    /* signal xor3 */
    /* xor3 <== xbits[3] + k3 - 2*xbits[3]*k3 */
    _offset_34 = _xbits_sigIdx_ + 3*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_34, _sigValue_22, 1);
    Fr_add(_tmp_38, _sigValue_22, (ctx->circuit->constants + 1));
    _offset_36 = _xbits_sigIdx_ + 3*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_36, _sigValue_23, 1);
    Fr_mul(_tmp_39, (ctx->circuit->constants + 2), _sigValue_23);
    Fr_mul(_tmp_40, _tmp_39, (ctx->circuit->constants + 1));
    Fr_sub(_tmp_41, _tmp_38, _tmp_40);
    ctx->setSignal(__cIdx, __cIdx, _xor3_sigIdx_, _tmp_41);
    /* signal less3 */
    /* less3 <== eq3 * ((1 - xbits[3]) * k3) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq3_sigIdx_, _sigValue_24, 1);
    _offset_38 = _xbits_sigIdx_ + 3*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_38, _sigValue_25, 1);
    Fr_sub(_tmp_42, (ctx->circuit->constants + 1), _sigValue_25);
    Fr_mul(_tmp_43, _tmp_42, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_44, _sigValue_24, _tmp_43);
    ctx->setSignal(__cIdx, __cIdx, _less3_sigIdx_, _tmp_44);
    /* signal eq2 */
    /* eq2  <== eq3 * (1 - xor3) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq3_sigIdx_, _sigValue_26, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor3_sigIdx_, _sigValue_27, 1);
    Fr_sub(_tmp_45, (ctx->circuit->constants + 1), _sigValue_27);
    Fr_mul(_tmp_46, _sigValue_26, _tmp_45);
    ctx->setSignal(__cIdx, __cIdx, _eq2_sigIdx_, _tmp_46);
    /* signal xor2 */
    /* xor2 <== xbits[2] + k2 - 2*xbits[2]*k2 */
    _offset_40 = _xbits_sigIdx_ + 2*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_40, _sigValue_28, 1);
    Fr_add(_tmp_47, _sigValue_28, (ctx->circuit->constants + 1));
    _offset_42 = _xbits_sigIdx_ + 2*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_42, _sigValue_29, 1);
    Fr_mul(_tmp_48, (ctx->circuit->constants + 2), _sigValue_29);
    Fr_mul(_tmp_49, _tmp_48, (ctx->circuit->constants + 1));
    Fr_sub(_tmp_50, _tmp_47, _tmp_49);
    ctx->setSignal(__cIdx, __cIdx, _xor2_sigIdx_, _tmp_50);
    /* signal less2 */
    /* less2 <== eq2 * ((1 - xbits[2]) * k2) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq2_sigIdx_, _sigValue_30, 1);
    _offset_44 = _xbits_sigIdx_ + 2*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_44, _sigValue_31, 1);
    Fr_sub(_tmp_51, (ctx->circuit->constants + 1), _sigValue_31);
    Fr_mul(_tmp_52, _tmp_51, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_53, _sigValue_30, _tmp_52);
    ctx->setSignal(__cIdx, __cIdx, _less2_sigIdx_, _tmp_53);
    /* signal eq1 */
    /* eq1  <== eq2 * (1 - xor2) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq2_sigIdx_, _sigValue_32, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor2_sigIdx_, _sigValue_33, 1);
    Fr_sub(_tmp_54, (ctx->circuit->constants + 1), _sigValue_33);
    Fr_mul(_tmp_55, _sigValue_32, _tmp_54);
    ctx->setSignal(__cIdx, __cIdx, _eq1_sigIdx_, _tmp_55);
    /* signal xor1 */
    /* xor1 <== xbits[1] + k1 - 2*xbits[1]*k1 */
    _offset_46 = _xbits_sigIdx_ + 1*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_46, _sigValue_34, 1);
    Fr_add(_tmp_56, _sigValue_34, (ctx->circuit->constants + 0));
    _offset_48 = _xbits_sigIdx_ + 1*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_48, _sigValue_35, 1);
    Fr_mul(_tmp_57, (ctx->circuit->constants + 2), _sigValue_35);
    Fr_mul(_tmp_58, _tmp_57, (ctx->circuit->constants + 0));
    Fr_sub(_tmp_59, _tmp_56, _tmp_58);
    ctx->setSignal(__cIdx, __cIdx, _xor1_sigIdx_, _tmp_59);
    /* signal less1 */
    /* less1 <== eq1 * ((1 - xbits[1]) * k1) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq1_sigIdx_, _sigValue_36, 1);
    _offset_50 = _xbits_sigIdx_ + 1*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_50, _sigValue_37, 1);
    Fr_sub(_tmp_60, (ctx->circuit->constants + 1), _sigValue_37);
    Fr_mul(_tmp_61, _tmp_60, (ctx->circuit->constants + 0));
    Fr_mul(_tmp_62, _sigValue_36, _tmp_61);
    ctx->setSignal(__cIdx, __cIdx, _less1_sigIdx_, _tmp_62);
    /* signal eq0 */
    /* eq0  <== eq1 * (1 - xor1) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq1_sigIdx_, _sigValue_38, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor1_sigIdx_, _sigValue_39, 1);
    Fr_sub(_tmp_63, (ctx->circuit->constants + 1), _sigValue_39);
    Fr_mul(_tmp_64, _sigValue_38, _tmp_63);
    ctx->setSignal(__cIdx, __cIdx, _eq0_sigIdx_, _tmp_64);
    /* signal xor0 */
    /* xor0 <== xbits[0] + k0 - 2*xbits[0]*k0 */
    _offset_52 = _xbits_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_52, _sigValue_40, 1);
    Fr_add(_tmp_65, _sigValue_40, (ctx->circuit->constants + 0));
    _offset_54 = _xbits_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_54, _sigValue_41, 1);
    Fr_mul(_tmp_66, (ctx->circuit->constants + 2), _sigValue_41);
    Fr_mul(_tmp_67, _tmp_66, (ctx->circuit->constants + 0));
    Fr_sub(_tmp_68, _tmp_65, _tmp_67);
    ctx->setSignal(__cIdx, __cIdx, _xor0_sigIdx_, _tmp_68);
    /* signal less0 */
    /* less0 <== eq0 * ((1 - xbits[0]) * k0) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq0_sigIdx_, _sigValue_42, 1);
    _offset_56 = _xbits_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_56, _sigValue_43, 1);
    Fr_sub(_tmp_69, (ctx->circuit->constants + 1), _sigValue_43);
    Fr_mul(_tmp_70, _tmp_69, (ctx->circuit->constants + 0));
    Fr_mul(_tmp_71, _sigValue_42, _tmp_70);
    ctx->setSignal(__cIdx, __cIdx, _less0_sigIdx_, _tmp_71);
    /* lt <== less6 + less5 + less4 + less3 + less2 + less1 + less0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _less6_sigIdx_, _sigValue_44, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _less5_sigIdx_, _sigValue_45, 1);
    Fr_add(_tmp_72, _sigValue_44, _sigValue_45);
    ctx->multiGetSignal(__cIdx, __cIdx, _less4_sigIdx_, _sigValue_46, 1);
    Fr_add(_tmp_73, _tmp_72, _sigValue_46);
    ctx->multiGetSignal(__cIdx, __cIdx, _less3_sigIdx_, _sigValue_47, 1);
    Fr_add(_tmp_74, _tmp_73, _sigValue_47);
    ctx->multiGetSignal(__cIdx, __cIdx, _less2_sigIdx_, _sigValue_48, 1);
    Fr_add(_tmp_75, _tmp_74, _sigValue_48);
    ctx->multiGetSignal(__cIdx, __cIdx, _less1_sigIdx_, _sigValue_49, 1);
    Fr_add(_tmp_76, _tmp_75, _sigValue_49);
    ctx->multiGetSignal(__cIdx, __cIdx, _less0_sigIdx_, _sigValue_50, 1);
    Fr_add(_tmp_77, _tmp_76, _sigValue_50);
    ctx->setSignal(__cIdx, __cIdx, _lt_sigIdx_, _tmp_77);
    /* lt * (lt - 1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _lt_sigIdx_, _sigValue_51, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _lt_sigIdx_, _sigValue_52, 1);
    Fr_sub(_tmp_78, _sigValue_52, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_79, _sigValue_51, _tmp_78);
    ctx->checkConstraint(__cIdx, _tmp_79, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:54:4");
    ctx->finished(__cIdx);
}
/*
LessThanConst7
k0=0
k1=0
k2=0
k3=0
k4=1
k5=0
k6=1
*/
void LessThanConst7_fd4377c26e549e32(Circom_CalcWit *ctx, int __cIdx) {
    FrElement _sigValue[1];
    FrElement _sigValue_1[1];
    FrElement _tmp_1[1];
    FrElement _tmp_2[1];
    FrElement _tmp_5[1];
    FrElement i[1];
    FrElement _sigValue_2[1];
    FrElement _sigValue_3[1];
    FrElement _tmp_6[1];
    FrElement _tmp_7[1];
    FrElement _tmp_9[1];
    FrElement _tmp_8[1];
    FrElement _tmp_10[1];
    FrElement _sigValue_4[1];
    FrElement _tmp_11[1];
    FrElement _sigValue_5[1];
    FrElement _tmp_12[1];
    FrElement _tmp_13[1];
    FrElement _tmp_14[1];
    FrElement _sigValue_6[1];
    FrElement _sigValue_7[1];
    FrElement _tmp_15[1];
    FrElement _tmp_16[1];
    FrElement _tmp_17[1];
    FrElement _sigValue_8[1];
    FrElement _sigValue_9[1];
    FrElement _tmp_18[1];
    FrElement _tmp_19[1];
    FrElement _sigValue_10[1];
    FrElement _tmp_20[1];
    FrElement _sigValue_11[1];
    FrElement _tmp_21[1];
    FrElement _tmp_22[1];
    FrElement _tmp_23[1];
    FrElement _sigValue_12[1];
    FrElement _sigValue_13[1];
    FrElement _tmp_24[1];
    FrElement _tmp_25[1];
    FrElement _tmp_26[1];
    FrElement _sigValue_14[1];
    FrElement _sigValue_15[1];
    FrElement _tmp_27[1];
    FrElement _tmp_28[1];
    FrElement _sigValue_16[1];
    FrElement _tmp_29[1];
    FrElement _sigValue_17[1];
    FrElement _tmp_30[1];
    FrElement _tmp_31[1];
    FrElement _tmp_32[1];
    FrElement _sigValue_18[1];
    FrElement _sigValue_19[1];
    FrElement _tmp_33[1];
    FrElement _tmp_34[1];
    FrElement _tmp_35[1];
    FrElement _sigValue_20[1];
    FrElement _sigValue_21[1];
    FrElement _tmp_36[1];
    FrElement _tmp_37[1];
    FrElement _sigValue_22[1];
    FrElement _tmp_38[1];
    FrElement _sigValue_23[1];
    FrElement _tmp_39[1];
    FrElement _tmp_40[1];
    FrElement _tmp_41[1];
    FrElement _sigValue_24[1];
    FrElement _sigValue_25[1];
    FrElement _tmp_42[1];
    FrElement _tmp_43[1];
    FrElement _tmp_44[1];
    FrElement _sigValue_26[1];
    FrElement _sigValue_27[1];
    FrElement _tmp_45[1];
    FrElement _tmp_46[1];
    FrElement _sigValue_28[1];
    FrElement _tmp_47[1];
    FrElement _sigValue_29[1];
    FrElement _tmp_48[1];
    FrElement _tmp_49[1];
    FrElement _tmp_50[1];
    FrElement _sigValue_30[1];
    FrElement _sigValue_31[1];
    FrElement _tmp_51[1];
    FrElement _tmp_52[1];
    FrElement _tmp_53[1];
    FrElement _sigValue_32[1];
    FrElement _sigValue_33[1];
    FrElement _tmp_54[1];
    FrElement _tmp_55[1];
    FrElement _sigValue_34[1];
    FrElement _tmp_56[1];
    FrElement _sigValue_35[1];
    FrElement _tmp_57[1];
    FrElement _tmp_58[1];
    FrElement _tmp_59[1];
    FrElement _sigValue_36[1];
    FrElement _sigValue_37[1];
    FrElement _tmp_60[1];
    FrElement _tmp_61[1];
    FrElement _tmp_62[1];
    FrElement _sigValue_38[1];
    FrElement _sigValue_39[1];
    FrElement _tmp_63[1];
    FrElement _tmp_64[1];
    FrElement _sigValue_40[1];
    FrElement _tmp_65[1];
    FrElement _sigValue_41[1];
    FrElement _tmp_66[1];
    FrElement _tmp_67[1];
    FrElement _tmp_68[1];
    FrElement _sigValue_42[1];
    FrElement _sigValue_43[1];
    FrElement _tmp_69[1];
    FrElement _tmp_70[1];
    FrElement _tmp_71[1];
    FrElement _sigValue_44[1];
    FrElement _sigValue_45[1];
    FrElement _tmp_72[1];
    FrElement _sigValue_46[1];
    FrElement _tmp_73[1];
    FrElement _sigValue_47[1];
    FrElement _tmp_74[1];
    FrElement _sigValue_48[1];
    FrElement _tmp_75[1];
    FrElement _sigValue_49[1];
    FrElement _tmp_76[1];
    FrElement _sigValue_50[1];
    FrElement _tmp_77[1];
    FrElement _sigValue_51[1];
    FrElement _sigValue_52[1];
    FrElement _tmp_78[1];
    FrElement _tmp_79[1];
    int _xbits_sigIdx_;
    int _offset_3;
    int _offset_5;
    int _offset_10;
    int _offset_12;
    int _eq6_sigIdx_;
    int _offset_16;
    int _offset_18;
    int _xor6_sigIdx_;
    int _offset_20;
    int _less6_sigIdx_;
    int _eq5_sigIdx_;
    int _offset_22;
    int _offset_24;
    int _xor5_sigIdx_;
    int _offset_26;
    int _less5_sigIdx_;
    int _eq4_sigIdx_;
    int _offset_28;
    int _offset_30;
    int _xor4_sigIdx_;
    int _offset_32;
    int _less4_sigIdx_;
    int _eq3_sigIdx_;
    int _offset_34;
    int _offset_36;
    int _xor3_sigIdx_;
    int _offset_38;
    int _less3_sigIdx_;
    int _eq2_sigIdx_;
    int _offset_40;
    int _offset_42;
    int _xor2_sigIdx_;
    int _offset_44;
    int _less2_sigIdx_;
    int _eq1_sigIdx_;
    int _offset_46;
    int _offset_48;
    int _xor1_sigIdx_;
    int _offset_50;
    int _less1_sigIdx_;
    int _eq0_sigIdx_;
    int _offset_52;
    int _offset_54;
    int _xor0_sigIdx_;
    int _offset_56;
    int _less0_sigIdx_;
    int _lt_sigIdx_;
    Circom_Sizes _sigSizes_xbits;
    PFrElement _loopCond;
    Fr_copy(&(_tmp_5[0]), ctx->circuit->constants +1);
    Fr_copy(&(i[0]), ctx->circuit->constants +1);
    _xbits_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x5c2ca035e26da383LL /* xbits */);
    _eq6_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa4318f05c114fLL /* eq6 */);
    _xor6_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fa95455aa6f98LL /* xor6 */);
    _less6_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e220a8c6b512aLL /* less6 */);
    _eq5_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa4418f05c1302LL /* eq5 */);
    _xor5_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fac5455aa74b1LL /* xor5 */);
    _less5_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e210a8c6b4f77LL /* less5 */);
    _eq4_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa4518f05c14b5LL /* eq4 */);
    _xor4_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fab5455aa72feLL /* xor4 */);
    _less4_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e200a8c6b4dc4LL /* less4 */);
    _eq3_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa3e18f05c08d0LL /* eq3 */);
    _xor3_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fae5455aa7817LL /* xor3 */);
    _less3_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e1f0a8c6b4c11LL /* less3 */);
    _eq2_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa3f18f05c0a83LL /* eq2 */);
    _xor2_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fad5455aa7664LL /* xor2 */);
    _less2_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e1e0a8c6b4a5eLL /* less2 */);
    _eq1_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa4018f05c0c36LL /* eq1 */);
    _xor1_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946fb05455aa7b7dLL /* xor1 */);
    _less1_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e1d0a8c6b48abLL /* less1 */);
    _eq0_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xc2fa4118f05c0de9LL /* eq0 */);
    _xor0_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x946faf5455aa79caLL /* xor0 */);
    _less0_sigIdx_ = ctx->getSignalOffset(__cIdx, 0xcc1e1c0a8c6b46f8LL /* less0 */);
    _lt_sigIdx_ = ctx->getSignalOffset(__cIdx, 0x08ad5407b55426cdLL /* lt */);
    _sigSizes_xbits = ctx->getSignalSizes(__cIdx, 0x5c2ca035e26da383LL /* xbits */);
    /* signal input xbits[7] */
    /* signal output lt */
    /* for (var i = 0;i < 7;i++) */
    /* xbits[i] * (xbits[i] - 1) === 0 */
    _offset_3 = _xbits_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_3, _sigValue, 1);
    _offset_5 = _xbits_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_5, _sigValue_1, 1);
    Fr_sub(_tmp_1, _sigValue_1, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_2, _sigValue, _tmp_1);
    ctx->checkConstraint(__cIdx, _tmp_2, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:20:8");
    _loopCond = _tmp_5;
    while (Fr_isTrue(_loopCond)) {
        /* xbits[i] * (xbits[i] - 1) === 0 */
        _offset_10 = _xbits_sigIdx_ + Fr_toInt(i)*_sigSizes_xbits[1];
        ctx->multiGetSignal(__cIdx, __cIdx, _offset_10, _sigValue_2, 1);
        _offset_12 = _xbits_sigIdx_ + Fr_toInt(i)*_sigSizes_xbits[1];
        ctx->multiGetSignal(__cIdx, __cIdx, _offset_12, _sigValue_3, 1);
        Fr_sub(_tmp_6, _sigValue_3, (ctx->circuit->constants + 1));
        Fr_mul(_tmp_7, _sigValue_2, _tmp_6);
        ctx->checkConstraint(__cIdx, _tmp_7, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:20:8");
        Fr_copyn(_tmp_9, i, 1);
        Fr_add(_tmp_8, i, (ctx->circuit->constants + 1));
        Fr_copyn(i, _tmp_8, 1);
        Fr_lt(_tmp_10, i, (ctx->circuit->constants + 11));
        _loopCond = _tmp_10;
    }
    /* signal eq6 */
    /* eq6 <== 1 */
    ctx->setSignal(__cIdx, __cIdx, _eq6_sigIdx_, (ctx->circuit->constants + 1));
    /* signal xor6 */
    /* xor6 <== xbits[6] + k6 - 2*xbits[6]*k6 */
    _offset_16 = _xbits_sigIdx_ + 6*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_16, _sigValue_4, 1);
    Fr_add(_tmp_11, _sigValue_4, (ctx->circuit->constants + 1));
    _offset_18 = _xbits_sigIdx_ + 6*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_18, _sigValue_5, 1);
    Fr_mul(_tmp_12, (ctx->circuit->constants + 2), _sigValue_5);
    Fr_mul(_tmp_13, _tmp_12, (ctx->circuit->constants + 1));
    Fr_sub(_tmp_14, _tmp_11, _tmp_13);
    ctx->setSignal(__cIdx, __cIdx, _xor6_sigIdx_, _tmp_14);
    /* signal less6 */
    /* less6 <== eq6 * ((1 - xbits[6]) * k6) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq6_sigIdx_, _sigValue_6, 1);
    _offset_20 = _xbits_sigIdx_ + 6*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_20, _sigValue_7, 1);
    Fr_sub(_tmp_15, (ctx->circuit->constants + 1), _sigValue_7);
    Fr_mul(_tmp_16, _tmp_15, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_17, _sigValue_6, _tmp_16);
    ctx->setSignal(__cIdx, __cIdx, _less6_sigIdx_, _tmp_17);
    /* signal eq5 */
    /* eq5  <== eq6 * (1 - xor6) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq6_sigIdx_, _sigValue_8, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor6_sigIdx_, _sigValue_9, 1);
    Fr_sub(_tmp_18, (ctx->circuit->constants + 1), _sigValue_9);
    Fr_mul(_tmp_19, _sigValue_8, _tmp_18);
    ctx->setSignal(__cIdx, __cIdx, _eq5_sigIdx_, _tmp_19);
    /* signal xor5 */
    /* xor5 <== xbits[5] + k5 - 2*xbits[5]*k5 */
    _offset_22 = _xbits_sigIdx_ + 5*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_22, _sigValue_10, 1);
    Fr_add(_tmp_20, _sigValue_10, (ctx->circuit->constants + 0));
    _offset_24 = _xbits_sigIdx_ + 5*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_24, _sigValue_11, 1);
    Fr_mul(_tmp_21, (ctx->circuit->constants + 2), _sigValue_11);
    Fr_mul(_tmp_22, _tmp_21, (ctx->circuit->constants + 0));
    Fr_sub(_tmp_23, _tmp_20, _tmp_22);
    ctx->setSignal(__cIdx, __cIdx, _xor5_sigIdx_, _tmp_23);
    /* signal less5 */
    /* less5 <== eq5 * ((1 - xbits[5]) * k5) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq5_sigIdx_, _sigValue_12, 1);
    _offset_26 = _xbits_sigIdx_ + 5*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_26, _sigValue_13, 1);
    Fr_sub(_tmp_24, (ctx->circuit->constants + 1), _sigValue_13);
    Fr_mul(_tmp_25, _tmp_24, (ctx->circuit->constants + 0));
    Fr_mul(_tmp_26, _sigValue_12, _tmp_25);
    ctx->setSignal(__cIdx, __cIdx, _less5_sigIdx_, _tmp_26);
    /* signal eq4 */
    /* eq4  <== eq5 * (1 - xor5) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq5_sigIdx_, _sigValue_14, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor5_sigIdx_, _sigValue_15, 1);
    Fr_sub(_tmp_27, (ctx->circuit->constants + 1), _sigValue_15);
    Fr_mul(_tmp_28, _sigValue_14, _tmp_27);
    ctx->setSignal(__cIdx, __cIdx, _eq4_sigIdx_, _tmp_28);
    /* signal xor4 */
    /* xor4 <== xbits[4] + k4 - 2*xbits[4]*k4 */
    _offset_28 = _xbits_sigIdx_ + 4*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_28, _sigValue_16, 1);
    Fr_add(_tmp_29, _sigValue_16, (ctx->circuit->constants + 1));
    _offset_30 = _xbits_sigIdx_ + 4*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_30, _sigValue_17, 1);
    Fr_mul(_tmp_30, (ctx->circuit->constants + 2), _sigValue_17);
    Fr_mul(_tmp_31, _tmp_30, (ctx->circuit->constants + 1));
    Fr_sub(_tmp_32, _tmp_29, _tmp_31);
    ctx->setSignal(__cIdx, __cIdx, _xor4_sigIdx_, _tmp_32);
    /* signal less4 */
    /* less4 <== eq4 * ((1 - xbits[4]) * k4) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq4_sigIdx_, _sigValue_18, 1);
    _offset_32 = _xbits_sigIdx_ + 4*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_32, _sigValue_19, 1);
    Fr_sub(_tmp_33, (ctx->circuit->constants + 1), _sigValue_19);
    Fr_mul(_tmp_34, _tmp_33, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_35, _sigValue_18, _tmp_34);
    ctx->setSignal(__cIdx, __cIdx, _less4_sigIdx_, _tmp_35);
    /* signal eq3 */
    /* eq3  <== eq4 * (1 - xor4) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq4_sigIdx_, _sigValue_20, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor4_sigIdx_, _sigValue_21, 1);
    Fr_sub(_tmp_36, (ctx->circuit->constants + 1), _sigValue_21);
    Fr_mul(_tmp_37, _sigValue_20, _tmp_36);
    ctx->setSignal(__cIdx, __cIdx, _eq3_sigIdx_, _tmp_37);
    /* signal xor3 */
    /* xor3 <== xbits[3] + k3 - 2*xbits[3]*k3 */
    _offset_34 = _xbits_sigIdx_ + 3*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_34, _sigValue_22, 1);
    Fr_add(_tmp_38, _sigValue_22, (ctx->circuit->constants + 0));
    _offset_36 = _xbits_sigIdx_ + 3*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_36, _sigValue_23, 1);
    Fr_mul(_tmp_39, (ctx->circuit->constants + 2), _sigValue_23);
    Fr_mul(_tmp_40, _tmp_39, (ctx->circuit->constants + 0));
    Fr_sub(_tmp_41, _tmp_38, _tmp_40);
    ctx->setSignal(__cIdx, __cIdx, _xor3_sigIdx_, _tmp_41);
    /* signal less3 */
    /* less3 <== eq3 * ((1 - xbits[3]) * k3) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq3_sigIdx_, _sigValue_24, 1);
    _offset_38 = _xbits_sigIdx_ + 3*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_38, _sigValue_25, 1);
    Fr_sub(_tmp_42, (ctx->circuit->constants + 1), _sigValue_25);
    Fr_mul(_tmp_43, _tmp_42, (ctx->circuit->constants + 0));
    Fr_mul(_tmp_44, _sigValue_24, _tmp_43);
    ctx->setSignal(__cIdx, __cIdx, _less3_sigIdx_, _tmp_44);
    /* signal eq2 */
    /* eq2  <== eq3 * (1 - xor3) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq3_sigIdx_, _sigValue_26, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor3_sigIdx_, _sigValue_27, 1);
    Fr_sub(_tmp_45, (ctx->circuit->constants + 1), _sigValue_27);
    Fr_mul(_tmp_46, _sigValue_26, _tmp_45);
    ctx->setSignal(__cIdx, __cIdx, _eq2_sigIdx_, _tmp_46);
    /* signal xor2 */
    /* xor2 <== xbits[2] + k2 - 2*xbits[2]*k2 */
    _offset_40 = _xbits_sigIdx_ + 2*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_40, _sigValue_28, 1);
    Fr_add(_tmp_47, _sigValue_28, (ctx->circuit->constants + 0));
    _offset_42 = _xbits_sigIdx_ + 2*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_42, _sigValue_29, 1);
    Fr_mul(_tmp_48, (ctx->circuit->constants + 2), _sigValue_29);
    Fr_mul(_tmp_49, _tmp_48, (ctx->circuit->constants + 0));
    Fr_sub(_tmp_50, _tmp_47, _tmp_49);
    ctx->setSignal(__cIdx, __cIdx, _xor2_sigIdx_, _tmp_50);
    /* signal less2 */
    /* less2 <== eq2 * ((1 - xbits[2]) * k2) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq2_sigIdx_, _sigValue_30, 1);
    _offset_44 = _xbits_sigIdx_ + 2*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_44, _sigValue_31, 1);
    Fr_sub(_tmp_51, (ctx->circuit->constants + 1), _sigValue_31);
    Fr_mul(_tmp_52, _tmp_51, (ctx->circuit->constants + 0));
    Fr_mul(_tmp_53, _sigValue_30, _tmp_52);
    ctx->setSignal(__cIdx, __cIdx, _less2_sigIdx_, _tmp_53);
    /* signal eq1 */
    /* eq1  <== eq2 * (1 - xor2) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq2_sigIdx_, _sigValue_32, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor2_sigIdx_, _sigValue_33, 1);
    Fr_sub(_tmp_54, (ctx->circuit->constants + 1), _sigValue_33);
    Fr_mul(_tmp_55, _sigValue_32, _tmp_54);
    ctx->setSignal(__cIdx, __cIdx, _eq1_sigIdx_, _tmp_55);
    /* signal xor1 */
    /* xor1 <== xbits[1] + k1 - 2*xbits[1]*k1 */
    _offset_46 = _xbits_sigIdx_ + 1*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_46, _sigValue_34, 1);
    Fr_add(_tmp_56, _sigValue_34, (ctx->circuit->constants + 0));
    _offset_48 = _xbits_sigIdx_ + 1*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_48, _sigValue_35, 1);
    Fr_mul(_tmp_57, (ctx->circuit->constants + 2), _sigValue_35);
    Fr_mul(_tmp_58, _tmp_57, (ctx->circuit->constants + 0));
    Fr_sub(_tmp_59, _tmp_56, _tmp_58);
    ctx->setSignal(__cIdx, __cIdx, _xor1_sigIdx_, _tmp_59);
    /* signal less1 */
    /* less1 <== eq1 * ((1 - xbits[1]) * k1) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq1_sigIdx_, _sigValue_36, 1);
    _offset_50 = _xbits_sigIdx_ + 1*_sigSizes_xbits[1];
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_50, _sigValue_37, 1);
    Fr_sub(_tmp_60, (ctx->circuit->constants + 1), _sigValue_37);
    Fr_mul(_tmp_61, _tmp_60, (ctx->circuit->constants + 0));
    Fr_mul(_tmp_62, _sigValue_36, _tmp_61);
    ctx->setSignal(__cIdx, __cIdx, _less1_sigIdx_, _tmp_62);
    /* signal eq0 */
    /* eq0  <== eq1 * (1 - xor1) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq1_sigIdx_, _sigValue_38, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _xor1_sigIdx_, _sigValue_39, 1);
    Fr_sub(_tmp_63, (ctx->circuit->constants + 1), _sigValue_39);
    Fr_mul(_tmp_64, _sigValue_38, _tmp_63);
    ctx->setSignal(__cIdx, __cIdx, _eq0_sigIdx_, _tmp_64);
    /* signal xor0 */
    /* xor0 <== xbits[0] + k0 - 2*xbits[0]*k0 */
    _offset_52 = _xbits_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_52, _sigValue_40, 1);
    Fr_add(_tmp_65, _sigValue_40, (ctx->circuit->constants + 0));
    _offset_54 = _xbits_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_54, _sigValue_41, 1);
    Fr_mul(_tmp_66, (ctx->circuit->constants + 2), _sigValue_41);
    Fr_mul(_tmp_67, _tmp_66, (ctx->circuit->constants + 0));
    Fr_sub(_tmp_68, _tmp_65, _tmp_67);
    ctx->setSignal(__cIdx, __cIdx, _xor0_sigIdx_, _tmp_68);
    /* signal less0 */
    /* less0 <== eq0 * ((1 - xbits[0]) * k0) */
    ctx->multiGetSignal(__cIdx, __cIdx, _eq0_sigIdx_, _sigValue_42, 1);
    _offset_56 = _xbits_sigIdx_;
    ctx->multiGetSignal(__cIdx, __cIdx, _offset_56, _sigValue_43, 1);
    Fr_sub(_tmp_69, (ctx->circuit->constants + 1), _sigValue_43);
    Fr_mul(_tmp_70, _tmp_69, (ctx->circuit->constants + 0));
    Fr_mul(_tmp_71, _sigValue_42, _tmp_70);
    ctx->setSignal(__cIdx, __cIdx, _less0_sigIdx_, _tmp_71);
    /* lt <== less6 + less5 + less4 + less3 + less2 + less1 + less0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _less6_sigIdx_, _sigValue_44, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _less5_sigIdx_, _sigValue_45, 1);
    Fr_add(_tmp_72, _sigValue_44, _sigValue_45);
    ctx->multiGetSignal(__cIdx, __cIdx, _less4_sigIdx_, _sigValue_46, 1);
    Fr_add(_tmp_73, _tmp_72, _sigValue_46);
    ctx->multiGetSignal(__cIdx, __cIdx, _less3_sigIdx_, _sigValue_47, 1);
    Fr_add(_tmp_74, _tmp_73, _sigValue_47);
    ctx->multiGetSignal(__cIdx, __cIdx, _less2_sigIdx_, _sigValue_48, 1);
    Fr_add(_tmp_75, _tmp_74, _sigValue_48);
    ctx->multiGetSignal(__cIdx, __cIdx, _less1_sigIdx_, _sigValue_49, 1);
    Fr_add(_tmp_76, _tmp_75, _sigValue_49);
    ctx->multiGetSignal(__cIdx, __cIdx, _less0_sigIdx_, _sigValue_50, 1);
    Fr_add(_tmp_77, _tmp_76, _sigValue_50);
    ctx->setSignal(__cIdx, __cIdx, _lt_sigIdx_, _tmp_77);
    /* lt * (lt - 1) === 0 */
    ctx->multiGetSignal(__cIdx, __cIdx, _lt_sigIdx_, _sigValue_51, 1);
    ctx->multiGetSignal(__cIdx, __cIdx, _lt_sigIdx_, _sigValue_52, 1);
    Fr_sub(_tmp_78, _sigValue_52, (ctx->circuit->constants + 1));
    Fr_mul(_tmp_79, _sigValue_51, _tmp_78);
    ctx->checkConstraint(__cIdx, _tmp_79, (ctx->circuit->constants + 0), "/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/circuits/UserTrustScoreLevel.circom:54:4");
    ctx->finished(__cIdx);
}
// Function Table
Circom_ComponentFunction _functionTable[4] = {
     UserTrustScoreLevel_75c5e8ce71c83660
    ,IsZero_0a2b8515b81b5ef3
    ,LessThanConst7_62c13aa59cd33892
    ,LessThanConst7_fd4377c26e549e32
};
