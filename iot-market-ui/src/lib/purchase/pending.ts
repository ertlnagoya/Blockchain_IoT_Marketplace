import { browser } from '$app/environment';

const PENDING_KEY = 'iot-market::pendingPurchase';
const AUTO_FLAG_KEY = 'iot-market::autoPurchaseFlag';

export type PendingPurchasePayload = {
	datasetCID: string;
	ipfsData?: Record<string, any> | null;
	source?: 'search' | 'detail' | 'unknown';
	savedAt: string;
};

function readLocalStorage(key: string) {
	if (!browser) return null;
	try {
		return localStorage.getItem(key);
	} catch (error) {
		console.warn('[pendingPurchase] failed to read', key, error);
		return null;
	}
}

function writeLocalStorage(key: string, value: string | null) {
	if (!browser) return;
	try {
		if (value === null) {
			localStorage.removeItem(key);
		} else {
			localStorage.setItem(key, value);
		}
	} catch (error) {
		console.warn('[pendingPurchase] failed to write', key, error);
	}
}

export function setPendingPurchase(payload: {
	datasetCID: string;
	ipfsData?: Record<string, any> | null;
	source?: 'search' | 'detail' | 'unknown';
}) {
	if (!payload?.datasetCID) return;
	const record: PendingPurchasePayload = {
		datasetCID: payload.datasetCID,
		ipfsData: payload.ipfsData ?? null,
		source: payload.source ?? 'unknown',
		savedAt: new Date().toISOString()
	};
	writeLocalStorage(PENDING_KEY, JSON.stringify(record));
}

export function getPendingPurchase(): PendingPurchasePayload | null {
	const raw = readLocalStorage(PENDING_KEY);
	if (!raw) return null;
	try {
		return JSON.parse(raw) as PendingPurchasePayload;
	} catch (error) {
		console.warn('[pendingPurchase] failed to parse record', error);
		return null;
	}
}

export function clearPendingPurchase() {
	writeLocalStorage(PENDING_KEY, null);
}

export function hasPendingPurchase() {
	return Boolean(getPendingPurchase());
}

export function flagAutoPurchase() {
	writeLocalStorage(AUTO_FLAG_KEY, '1');
}

export function isAutoPurchaseFlagSet() {
	return readLocalStorage(AUTO_FLAG_KEY) === '1';
}

export function clearAutoPurchaseFlag() {
	writeLocalStorage(AUTO_FLAG_KEY, null);
}
