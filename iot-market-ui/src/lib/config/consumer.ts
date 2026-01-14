import { debugDidKey } from '$lib/crypto/didKeyDebug';
export const consumerDID = 'did:key:z6Mkn12GycgAuTxB4njR7BsJhtHqijSa5L127NdXhccBR1ey';           // 你的 did:key
// 32 字节 Ed25519 seed，标准 base64 或 base64url 都可（我们会规范化）
export const consumerSeedB64 = 'LPY7u0SMk_fGbiaHaF47ZJRFTC-WpGpaVYnTbCojwgI';
debugDidKey(consumerDID);

//lyhl@lyhdeMacBook-Air ssi % node -e "const n=require('tweetnacl');const bs58=require('bs58');const kp=n.sign.keyPair();const seed=kp.secretKey.slice(0,32);const b64u=str=>Buffer.from(str).toString('base64url');const did='did:key:'+'z'+bs58.default.encode(Buffer.concat([Buffer.from([0xed,0x01]),Buffer.from(kp.publicKey)]));console.log('consumerDID=',did);console.log('consumerSeedB64=',Buffer.from(seed).toString('base64url'));"
//consumerDID= did:key:z6Mkn12GycgAuTxB4njR7BsJhtHqijSa5L127NdXhccBR1ey
//consumerSeedB64= LPY7u0SMk_fGbiaHaF47ZJRFTC-WpGpaVYnTbCojwgI