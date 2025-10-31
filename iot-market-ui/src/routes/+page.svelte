<script lang="ts">
	import { ethers } from 'ethers';
	import { Merchandise__factory } from '../types/typechain-types/index.js';
	
	let queryResult: any = null;
	let startTime: string = '2025-06-30T08:00:00';
	let endTime: string = '2025-06-30T12:20:00';
	let latitude: string = '35.15430131582339';
	let longitude: string = '136.9700924892541';
	let radius: string = '50'; // default 50m
	let filterByTime: boolean = false;
	let filterByLocation: boolean = false;
	let filterByPeople: boolean = false;
	let peopleExist: boolean = true;
	let searchExecutionTime: number | null = null;
	let isSearching: boolean = false;

	// Function to connect to MetaMask
	const connectToMetaMask = async () => {
		const windowProvider = (window as any).ethereum;

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

	// Purchase function
	const purchase = async (merchandiseData: any) => {
		try {
			const { provider, signer } = await connectToMetaMask();
			const merchandise = Merchandise__factory.connect(merchandiseData.address, signer);
			
			if (signer) {
				const transactionResponse = await merchandise.purchase({
					value: ethers.parseEther(merchandiseData.price || '0.01')
				});
				
				alert('Purchase started. Please wait for the transaction confirmation...');
				await transactionResponse.wait(1);
				alert('Purchase completed!');
			} else {
				throw new Error('Please connect to MetaMask');
			}
		} catch (error: any) {
			alert(`Purchase error: ${error.message}`);
			console.error('Purchase error:', error);
		}
	};

	async function executeSearch() {
		isSearching = true;
		searchExecutionTime = null;
		const executionStartTime = performance.now();
		
		// Build base query
		let query = 'SELECT *';
		let conditions: string[] = [];
		
		// When location filter is enabled, also compute distance
		if (filterByLocation) {
			query += `, ST_Distance(location, ST_GeogFromText('POINT(${longitude} ${latitude})')) AS distance`;
		}
		
		query += ' FROM ipfs_records';
		
		// Add time filter
		if (filterByTime) {
			if (!startTime || !endTime) {
				alert('When enabling the time filter, please provide both start and end times.');
				isSearching = false;
				return;
			}
			conditions.push(`start_timestamp >= '${startTime}'`);
			conditions.push(`end_timestamp <= '${endTime}'`);
		}
		
		// Add location filter
		if (filterByLocation) {
			if (!latitude || !longitude) {
				alert('When enabling the location filter, please provide both latitude and longitude.');
				isSearching = false;
				return;
			}
			const radiusMeters = parseFloat(radius);
			conditions.push(`ST_DWithin(location, ST_GeogFromText('POINT(${longitude} ${latitude})'), ${radiusMeters})`);
		}
		
		// Add people-existence filter
		if (filterByPeople) {
			conditions.push(`exist_people = ${peopleExist}`);
		}
		
		// Append WHERE conditions
		if (conditions.length > 0) {
			query += ' WHERE ' + conditions.join(' AND ');
		}
		
		// Order by distance when location filter is enabled
		if (filterByLocation) {
			query += ' ORDER BY distance';
		}
		
		query += ';';
		
		console.log('Executing query:', query);
		
		try {
			const response = await fetch('/api/sql-query', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ query })
			});
			queryResult = await response.json();
			
			const executionEndTime = performance.now();
			searchExecutionTime = Math.round((executionEndTime - executionStartTime) * 100) / 100;
		} catch (error) {
			console.error('Search error:', error);
			const executionEndTime = performance.now();
			searchExecutionTime = Math.round((executionEndTime - executionStartTime) * 100) / 100;
		} finally {
			isSearching = false;
		}
	}
</script>

<div class="mt-8 flex flex-col items-center space-y-6">
	<h2 class="text-2xl font-bold">IoT データ検索</h2>
	
	<!-- Debug info -->
	<div class="text-xs text-gray-600">
		Filter states: time={filterByTime}, location={filterByLocation}, people={filterByPeople}
	</div>
	
	<!-- Search filters -->
	<div class="bg-gray-50 p-6 rounded-lg space-y-4">
		<h3 class="text-lg font-semibold text-black">Search Filters</h3>
		
		<!-- Time filter -->
		<div class="space-y-2">
			<div class="flex items-center space-x-2">
				<input
					id="filterTime"
					type="checkbox"
					bind:checked={filterByTime}
					class="rounded bg-white border-gray-300"
				/>
				<label for="filterTime" class="text-sm font-medium text-black cursor-pointer">Filter by time</label>
			</div>
			
			{#if filterByTime}
				<div class="flex space-x-4 ml-6">
					<div class="flex flex-col">
						<label class="text-sm font-medium text-black">Start time</label>
						<input
							type="datetime-local"
							bind:value={startTime}
							class="px-3 py-2 border rounded text-black"
						/>
					</div>
					<div class="flex flex-col">
						<label class="text-sm font-medium text-black">End time</label>
						<input
							type="datetime-local"
							bind:value={endTime}
							class="px-3 py-2 border rounded text-black"
						/>
					</div>
				</div>
			{/if}
		</div>
		
		<!-- Location filter -->
		<div class="space-y-2">
			<div class="flex items-center space-x-2">
				<input
					id="filterLocation"
					type="checkbox"
					bind:checked={filterByLocation}
					class="rounded bg-white border-gray-300"
				/>
				<label for="filterLocation" class="text-sm font-medium text-black cursor-pointer">Filter by location</label>
			</div>
			
			{#if filterByLocation}
				<div class="flex space-x-4 ml-6">
					<div class="flex flex-col">
						<label class="text-sm font-medium text-black">Latitude</label>
						<input
							type="number"
							step="0.000001"
							bind:value={latitude}
							placeholder="e.g.: 35.6762"
							class="px-3 py-2 border rounded text-black"
						/>
					</div>
					<div class="flex flex-col">
						<label class="text-sm font-medium text-black">Longitude</label>
						<input
							type="number"
							step="0.000001"
							bind:value={longitude}
							placeholder="e.g.: 139.6503"
							class="px-3 py-2 border rounded text-black"
						/>
					</div>
					<div class="flex flex-col">
						<label class="text-sm font-medium text-black">Radius (m)</label>
						<input
							type="number"
							step="1"
							bind:value={radius}
							class="px-3 py-2 border rounded text-black"
						/>
					</div>
				</div>
			{/if}
		</div>
		
		<!-- People existence filter -->
		<div class="space-y-2">
			<div class="flex items-center space-x-2">
				<input
					id="filterPeople"
					type="checkbox"
					bind:checked={filterByPeople}
					class="rounded bg-white border-gray-300"
				/>
				<label for="filterPeople" class="text-sm font-medium text-black cursor-pointer">Filter by people existence</label>
			</div>
			
			{#if filterByPeople}
				<div class="flex space-x-4 ml-6">
					<label class="flex items-center space-x-2">
						<input
							type="radio"
							bind:group={peopleExist}
							value={true}
							name="peopleExist"
						/>
						<span class="text-sm text-black">People present</span>
					</label>
					<label class="flex items-center space-x-2">
						<input
							type="radio"
							bind:group={peopleExist}
							value={false}
							name="peopleExist"
						/>
						<span class="text-sm text-black">No people</span>
					</label>
				</div>
			{/if}
		</div>
		
		<!-- Search button -->
		<button 
			class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
			on:click={executeSearch}
			disabled={isSearching}
		>
			{#if isSearching}
				Searching...
			{:else}
				Run Search
			{/if}
		</button>
		
		<!-- Search execution status -->
		{#if isSearching}
			<div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
				<p class="text-blue-800 text-sm">
					<span class="font-semibold">🔍 Searching...</span>
				</p>
			</div>
		{:else if searchExecutionTime !== null}
			<div class="bg-green-50 border border-green-200 rounded-lg p-3">
				<p class="text-green-800 text-sm">
					<span class="font-semibold">Execution time:</span> 
					<span class="font-mono font-bold">{searchExecutionTime}ms</span>
				</p>
			</div>
		{/if}
	</div>
	
	{#if queryResult && Array.isArray(queryResult)}
		<table class="mt-4 bg-gray-100 p-2 rounded text-xs text-black">
			<thead>
				<tr>
					<th class="px-2 py-1 text-black">CID</th>
					<th class="px-2 py-1 text-black">Start time</th>
					<th class="px-2 py-1 text-black">End time</th>
					<th class="px-2 py-1 text-black">Location</th>
					<th class="px-2 py-1 text-black">Prople</th>
					{#if filterByLocation}
						<th class="px-2 py-1 text-black">Distance (m)</th>
					{/if}
					<th class="px-2 py-1 text-black">IPFS Data</th>
					<th class="px-2 py-1 text-black">Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each queryResult as row}
					<tr>
						<td class="px-2 py-1 text-black">{row.cid}</td>
						<td class="px-2 py-1 text-black">{row.start_timestamp}</td>
						<td class="px-2 py-1 text-black">{row.end_timestamp}</td>
						<td class="px-2 py-1 text-black">{row.location}</td>
						<td class="px-2 py-1 text-black">{row.exist_people ? 'Yes' : 'No'}</td>
						{#if filterByLocation}
							<td class="px-2 py-1 text-black">
								{row.distance ? Math.round(row.distance) : 'N/A'}
							</td>
						{/if}
						<td class="px-2 py-1 text-black">
							{#if row.ipfs_data}
								{#if row.ipfs_data.error}
									<span class="text-red-600">Error: {row.ipfs_data.error}</span>
								{:else if row.ipfs_data.type === 'text'}
									<details>
										<summary class="cursor-pointer text-blue-600">Text data</summary>
										<pre class="mt-2 text-xs">{row.ipfs_data.content}</pre>
									</details>
								{:else}
									<details>
										<summary class="cursor-pointer text-blue-600">JSON data</summary>
										<pre class="mt-2 text-xs">{JSON.stringify(row.ipfs_data, null, 2)}</pre>
									</details>
								{/if}
							{:else}
								<span class="text-gray-500">No data</span>
							{/if}
						</td>
						<td class="px-2 py-1 text-black">
							{#if row.ipfs_data && row.ipfs_data.address && !row.ipfs_data.error}
								<button 
									class="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 transition-colors"
									on:click={() => purchase(row.ipfs_data)}
								>
									Purchase
								</button>
								<div class="text-xs mt-1">
									{row.ipfs_data.price || '0.01'} ETH
								</div>
							{:else}
								<span class="text-gray-500 text-xs">Not purchasable</span>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{:else if queryResult}
		<pre class="mt-4 bg-gray-100 p-2 rounded text-xs">{JSON.stringify(queryResult, null, 2)}</pre>
	{/if}
</div>
