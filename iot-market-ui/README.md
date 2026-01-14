# IoT Marketplace UI

SvelteKit frontend for browsing IoT datasets, requesting purchases through the SSI provider handshake, and kicking off on-chain transactions against the `Merchandise` contracts.

## Prerequisites

- Node.js 18+
- Local Hardhat node (for contract interactions)
- Provider mock API running on `http://localhost:4002` (see `../provider-mock`)

## Setup

```bash
cd iot-market-ui
npm install
```

## Running the UI

```bash
npm run dev -- --open
```

This starts SvelteKit on `http://localhost:5173`. The default provider endpoint is derived from `$lib/config/providers.ts`; update that file if you run the mock API elsewhere.

## Purchase flow tips

1. Start the provider mock: `cd ../provider-mock && npm run dev`.
2. Use the search filters to locate a dataset.
3. 在 `http://localhost:5173/provider` 页面提交 Provider VC，完成零知识证明并确保状态显示 **FULL ACCESS** (Level 2)。
4. Click **Purchase** to send the off-chain request, verify the provider response, and finally invoke the on-chain `purchase()` call via MetaMask. If you are not yet verified, the UI now remembers the dataset you attempted to buy, sends you to `/provider`, and after the VC is accepted it automatically redirects back to `/` and resumes the pending purchase.

## Testing & linting

```bash
npm run lint
npm run test
```

Vitest covers unit tests such as the schema validators. Linting uses the default SvelteKit ESLint config.

## Building for production

```bash
npm run build
npm run preview
```

Deploy the generated build with your preferred adapter (static, Node, Cloudflare Workers, etc.).

## Provider 证明页面

- 路径：`/provider`
- 功能：上传或粘贴 Provider Verifiable Credential，推导出权限等级，并调用 `provider-mock` 的 `/provider-profile` 接口登记真实的 `providerDID`。
- 只有当页面显示 **FULL ACCESS** 时，购买流程才允许继续执行。

### 外部 SSI Portal 如何回传认证结果？

如果零知识证明流程在另一个域名或 VS Code 工作区中运行（例如 React/Next.js Portal），可以在认证完成后跳转到新的桥接页：

```
http://localhost:5173/provider/bridge?level=2&providerDID=did:example:123&issuerDID=did:issuer:abc&vcID=vc123&auto=1&redirect=/
```

- `level`：必填，≥ 2 视为 FULL ACCESS，会直接写入 `iot-market::providerVerification`。
- `providerDID` / `issuerDID` / `vcID`：可选，用于 UI 显示。
- `auto`：`1` 或 `true` 时，如果本地存在 `pendingPurchase`，会设置自动续购标志。
- `pending`：可选，用 base64(JSON) 形式传递 `datasetCID` 和 `ipfsData`，例如 `pending=eyJkYXRhc2V0Q0lEIjoiQ0lEMTIzIn0=`。
- `redirect`：认证同步后跳转的地址，默认 `/`。

外部 Portal 只需在成功时 `window.location.href = "http://localhost:5173/provider/bridge?..."`，即可避免重复跑验证页面，回到市场后会立即进入已验证状态并自动恢复挂起订单。
