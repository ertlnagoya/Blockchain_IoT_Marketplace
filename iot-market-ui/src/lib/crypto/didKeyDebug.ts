import bs58 from 'bs58';

export function debugDidKey(did: string) {
  const mb = did.startsWith('did:key:') ? did.slice(8) : did;
  const decoded = bs58.decode(mb.slice(1));
  console.log('[debugDidKey] bytes[0]=', decoded[0].toString(16), 'bytes[1]=', decoded[1].toString(16), 'totalLen=', decoded.length);
}