// 先跑通为主：用默认端点，不依赖 provider 地址
// 在前端直接给个兜底端点即可先联调成功
export const defaultProviderEndpoint = 'http://localhost:4002';
export const providerEndpoints: Record<string, string> = {};
export const providerPortalUrl = 'http://127.0.0.1:5174/provider';
export const marketHomeUrl = '/';