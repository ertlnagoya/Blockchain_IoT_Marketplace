import type { JWK } from 'jose';
import bs58 from 'bs58';

function bytesToB64(bytes: Uint8Array): string {
  let bin=''; for (let i=0;i<bytes.length;i++) bin+=String.fromCharCode(bytes[i]); return btoa(bin);
}
function toB64u(bytes: Uint8Array): string {
  return bytesToB64(bytes).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
}

export function extractEd25519PublicKeyFromDidKey(didOrMb: string) {
  const mb = didOrMb.startsWith('did:key:') ? didOrMb.slice(8) : didOrMb;
  const decoded = bs58.decode(mb.slice(1));
  if (decoded[0] !== 0xed || decoded[1] !== 0x01) {
    throw new Error(`Not Ed25519 prefix: 0x${decoded[0].toString(16)} 0x${decoded[1].toString(16)}`);
  }
  return decoded.slice(2);
}

export function didKeyToPublicJwk(didOrMb: string): JWK {
  const pk = extractEd25519PublicKeyFromDidKey(didOrMb);
  if (pk.length !== 32) throw new Error('Invalid Ed25519 public key length');
  return { kty:'OKP', crv:'Ed25519', alg:'EdDSA', x: toB64u(pk) };
}