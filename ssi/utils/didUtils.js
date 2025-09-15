import { generateKeyPair } from '@digitalbazaar/did-method-key';
import { exportJWK } from 'jose';

export async function createDID() {
  const { didDocument, keyPair } = await generateKeyPair();
  const publicKeyJwk = await exportJWK(keyPair.publicKey);
  const privateKeyJwk = await exportJWK(keyPair.privateKey);

  return {
    did: didDocument.id,
    publicKeyJwk,
    privateKeyJwk,
  };
}
