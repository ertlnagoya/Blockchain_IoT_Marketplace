import {writeFile} from 'node:fs/promises';  // Node.js 16+ 支持的Promise版fs写入
import {Ed25519VerificationKey2020} from '@digitalbazaar/ed25519-verification-key-2020';
import {DidKeyDriver} from '@digitalbazaar/did-method-key';

async function main() {
  const keyPair = await Ed25519VerificationKey2020.generate();

  const driver = new DidKeyDriver();

  const didDocument = await driver.generate({keyPair});

  console.log('DID Document:', JSON.stringify(didDocument, null, 2));
  console.log('Key Pair:', keyPair);

  await writeFile('/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/did/user/didDocument.json', JSON.stringify(didDocument, null, 2), 'utf8');
  await writeFile('/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/did/user/keyPair.json', JSON.stringify(keyPair, null, 2), 'utf8');

  console.log('✅ DID Document 和 Key Pair 已保存到 didDocument.json 和 keyPair.json');
}

main().catch(console.error);
