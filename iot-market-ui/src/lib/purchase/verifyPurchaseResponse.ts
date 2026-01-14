import { jwtVerify, importJWK } from 'jose';
import { didKeyToPublicJwk } from '../crypto/didKeyToJwk'; // 若前端单独复制一个 util

export async function verifyProviderResponse(resp: any, expectRequestID?: string) {
  const kid: string = resp?.proof?.kid;
  const jws: string = resp?.proof?.jws;
  if (!kid || !jws) throw new Error('missing provider proof');
  if (expectRequestID && resp?.requestID !== expectRequestID) throw new Error('requestID mismatch');

  const did = kid.split('#')[0];
  const jwk = didKeyToPublicJwk(did);
  const pub = await importJWK(jwk, 'EdDSA');
  await jwtVerify(jws, pub);
  return true;
}