<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.png';
	import { ethers } from 'ethers';
	let provider: ethers.BrowserProvider | undefined = $state();
	let signer: ethers.JsonRpcSigner | undefined = $state();

	const connectToMetaMask = async () => {
		const windowProvider = window.ethereum;

		if (windowProvider == null) {
			throw new Error('MetaMask not found');
		}
		try {
			const provider = await new ethers.BrowserProvider(windowProvider);
			const signer = await provider.getSigner();
			return { provider, signer };
		} catch (error) {
			throw new Error('Error while connecting to MetaMask');
		}
	};

	const toggleMenu = () => {
		const menu = document.getElementById('menu')!;
		menu.classList.toggle('hidden');
	};
</script>

<svelte:head>
	<meta charset="utf-8" />
	<link rel="shortcut icon" href={favicon} type="image/x-icon" />
	<title>IoT Data Market Place</title>
</svelte:head>

<header class="px-4 py-2 shadow-sm shadow-indigo-500/50">
	<div class="flex items-center justify-between">
		<a href="/" class="flex items-center">
			<img src={favicon} alt="" class="h-8 w-8" />
			<h1 class="ml-3 text-xl">IoT Marketplace</h1>
		</a>
		<div id="icons" class="flex items-center">
			<!-- sm: hamburger menu　-->
			<button class="block md:hidden" on:click={toggleMenu}>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="h-8 w-8"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M4 6h16M4 12h16m-7 6h7"
					/>
				</svg>
			</button>
			<!-- md: connect button -->
			{#if signer}
				<p class="my-2 mr-2 hidden md:block">
					Welcome! <span class="text-blue-500">{signer.address}</span>
				</p>
			{:else}
				<button
					on:click={() => {
						connectToMetaMask()
							.then((res) => {
								provider = res.provider;
								signer = res.signer;
							})
							.catch((error) => {
								alert(`Error: ${error.message}\nPlease install MetaMask and try again.`);
							});
					}}
					class="gradiant hidden rounded-lg px-4 py-2 text-white shadow-lg md:block"
				>
					Connect your wallet!</button
				>
			{/if}
		</div>
	</div>
</header>
<!-- toggle menu -->
<div class="hidden text-lg text-gray-300 shadow-sm shadow-indigo-500/50 md:hidden" id="menu">
	{#if signer}
		<div class=" border-y border-gray-700 py-2 pl-4">
			Accout: <span class="text-sm text-blue-500">{signer.address}</span>
		</div>
	{:else}
		<button
			class="block border-y border-gray-700 py-2 pl-4 hover:cursor-pointer hover:text-purple-400"
			on:click={() => {
				connectToMetaMask()
					.then((res) => {
						provider = res.provider;
						signer = res.signer;
					})
					.catch((error) => {
						alert(`Error: ${error.message}\nPlease install MetaMask and try again.`);
					});
			}}
		>
			Connect your Wallet
		</button>
	{/if}
	<a
		class="block border-y border-gray-700 py-2 pl-4 hover:cursor-pointer hover:text-purple-400"
		href="/"
	>
		Purchase History
	</a>
</div>
<slot />

<style lang="postcss">
	:global(body) {
		@apply bg-gray-900;
		@apply text-white;
	}
</style>
