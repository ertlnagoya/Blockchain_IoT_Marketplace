import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export type VerificationStatus = 'unverified' | 'verifying' | 'verified' | 'error';

export type ProviderVerificationState = {
	status: VerificationStatus;
	level: number;
	providerDID?: string;
	issuerDID?: string;
	vcID?: string;
	updatedAt?: string;
	error?: string;
};

const STORAGE_KEY = 'iot-market::providerVerification';
const defaultState: ProviderVerificationState = {
	status: 'unverified',
	level: 0
};

function loadInitialState(): ProviderVerificationState {
	if (!browser) return defaultState;
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return defaultState;
		const parsed = JSON.parse(raw);
		return { ...defaultState, ...parsed };
	} catch (error) {
		console.warn('[providerVerification] failed to load state', error);
		return defaultState;
	}
}

function persist(state: ProviderVerificationState) {
	if (!browser) return;
	localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function createProviderVerificationStore() {
	const { subscribe, set, update } = writable<ProviderVerificationState>(loadInitialState());

	function setState(next: ProviderVerificationState) {
		persist(next);
		set(next);
	}

	return {
		subscribe,
		reset() {
			setState(defaultState);
		},
		markVerifying() {
			update((current) => {
				const next: ProviderVerificationState = {
					...current,
					status: 'verifying',
					error: undefined
				};
				persist(next);
				return next;
			});
		},
		markVerified(payload: Partial<ProviderVerificationState>) {
			const next: ProviderVerificationState = {
				status: 'verified',
				level: payload.level ?? 0,
				providerDID: payload.providerDID,
				issuerDID: payload.issuerDID,
				vcID: payload.vcID,
				updatedAt: new Date().toISOString(),
				error: undefined
			};
			setState(next);
		},
		markError(message: string) {
			update((current) => {
				const next: ProviderVerificationState = {
					...current,
					status: 'error',
					error: message
				};
				persist(next);
				return next;
			});
		}
	};
}

export const providerVerification = createProviderVerificationStore();
