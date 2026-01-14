const SERVER_RPC_URL =
	import.meta.env.VITE_RPC_URL_SERVER ||
	import.meta.env.VITE_RPC_URL ||
	'http://host.docker.internal:8545';

const BROWSER_RPC_URL =
	import.meta.env.VITE_RPC_URL_BROWSER ||
	import.meta.env.VITE_RPC_URL ||
	'http://127.0.0.1:8545';

export const RPC_URL = typeof window === 'undefined' ? SERVER_RPC_URL : BROWSER_RPC_URL;
export const NETWORK = { chainId: 31337, name: 'hardhat' } as const;