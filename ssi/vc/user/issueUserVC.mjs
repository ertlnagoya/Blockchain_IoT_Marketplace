import fs from 'fs';
import { EdDSASigner } from 'did-jwt';
import { createVerifiableCredentialJwt } from 'did-jwt-vc';

// 1. 发行者信息（keyPair.json的信息）
const issuer = {
  did: 'did:key:z6Mkn5a1ayMRkLoTJaZiwtPWj8bMagvR5dkdodztLvRedSHp',
  privateKeyMultibase: 'zrv2ZCebu91oBq38TL6qSpRGwhSGoKB2CEZVqyeFPTq813VrjLU92oTRRrPqPdKwebbCeZwZN5vjjA8gVq73tiNnFdk'
};

// 2. 被签发者 DID（Data User DID）
const subjectDID = 'did:key:z6MkmQ4mXnSJGhMKSS4SNfaNCmSVLKngB8YM3nZc9cXQyhwM';

// 3. Multibase 私钥转成 Uint8Array
function multibaseToBytes(multibase) {
  // 用 base58 解码
  import('bs58').then(bs58 => {
    const decoded = bs58.decode(multibase.slice(1));
    return decoded;
  });
}

async function getSignerFromMultibase(multibaseKey) {
  const bs58 = await import('bs58');
  let decoded = bs58.default.decode(multibaseKey.slice(1));
  if (decoded.length === 66) {
    decoded = decoded.slice(2);
  }
  return EdDSASigner(decoded);
}
async function issueVC() {
  try {

    const signer = await getSignerFromMultibase(issuer.privateKeyMultibase);

    // VC的Payload
    const vcPayload = {
      iss: issuer.did,
      sub: subjectDID,
      nbf: Math.floor(Date.now() / 1000), // 生效时间
      vc: {
        '@context': [
          'https://www.w3.org/2018/credentials/v1',
          {
            entityType: 'https://schema.org/organizationType',
            purpose: 'https://schema.org/purpose',
            legalCompliance: 'https://schema.org/legalStatus',
            dataHandlingPolicy: 'https://schema.org/description',
            misuseRecord: 'https://schema.org/Boolean'
          }
        ],
        type: ['VerifiableCredential'],
        credentialSubject: {
          id: subjectDID,
          entityType: 'GovernmentOrganization',
          purpose: 'research',
          legalCompliance: true,
          dataHandlingPolicy: 'ISO27001',
          misuseRecord: false
        }
      }
    };

    // 签发JWT格式VC
    const jwt = await createVerifiableCredentialJwt(vcPayload, {
      issuer: issuer.did,
      signer,
      alg: 'EdDSA'
    });

    // 保存到文件
    fs.writeFileSync('/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/vc/user/dataUserVC.jwt', jwt, 'utf-8');
    console.log('✅ JWT格式VC签发成功，保存路径: ./vc/user/dataUserVC.jwt');
  } catch (error) {
    console.error('❌ 签发VC失败:', error);
  }
}

issueVC();
