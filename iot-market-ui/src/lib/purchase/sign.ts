import { SignJWT, importJWK, type JWK } from 'jose';
import { didKeyToPublicJwk } from '$lib/crypto/didKeyToJwk';

// base64 <-> Uint8Array（浏览器版）
function bytesToB64(bytes: Uint8Array): string {
  let bin = ''; for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]); return btoa(bin);
}
function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64); const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out;
}
function toB64u(bytes: Uint8Array): string {
  return bytesToB64(bytes).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
}
function parseSeed(anyStr: string): Uint8Array {
  const s = anyStr.trim();
  // 支持 0x 前缀或纯 hex（64个十六进制字符=32字节）
  if (/^(0x)?[0-9a-fA-F]{64}$/.test(s)) {
    const hex = s.startsWith('0x') ? s.slice(2) : s;
    const out = new Uint8Array(32);
    for (let i = 0; i < 32; i++) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
    return out;
  }
  // base64/base64url
  const norm = s.replace(/-/g, '+').replace(/_/g, '/').replace(/\s/g, '');
  const pad = norm.length % 4 ? '='.repeat(4 - (norm.length % 4)) : '';
  return b64ToBytes(norm + pad); // 若仍非法会抛错，请检查输入
}
function b64uToBytes(s: string): Uint8Array {
  const norm = s.replace(/-/g, '+').replace(/_/g, '/');
  const pad = norm.length % 4 ? '='.repeat(4 - (norm.length % 4)) : '';
  return b64ToBytes(norm + pad);
}

export async function signPurchasePayloadJWS(payload: any, did: string, seedStr: string) {
  const pub = didKeyToPublicJwk(did);
  const xBytes = b64uToBytes(pub.x!);
  console.log('[sign] x.len =', xBytes.length); // 32

  const seed = parseSeed(seedStr);
  console.log('[sign] d.len =', seed.length);   // 32
  if (seed.length !== 32) throw new Error(`Invalid Ed25519 seed length=${seed.length}, expect 32`);

  const jwk: JWK = { kty: 'OKP', crv: 'Ed25519', x: pub.x!, d: toB64u(seed) };
  const key = await importJWK(jwk, 'EdDSA');
  const kid = `${did}#key-1`;
  const jws = await new SignJWT(payload).setProtectedHeader({ alg: 'EdDSA', kid }).sign(key);
  return { type: 'JWS', alg: 'EdDSA', kid, keyData: pub, jws };
}