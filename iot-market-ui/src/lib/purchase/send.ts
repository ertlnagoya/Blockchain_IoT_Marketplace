import { validatePurchaseRequest } from './schema';

export async function sendPurchaseRequest(providerEndpoint: string, body: any) {
  const res = await fetch(`${providerEndpoint}/purchase-request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    mode: 'cors',
    body: JSON.stringify(body)
  });
  const text = await res.text();
  let json: any = {};
  try { json = text ? JSON.parse(text) : {}; } catch {}
  if (!res.ok) throw new Error(`HTTP ${res.status} ${JSON.stringify(json)}`);
  return json;
}