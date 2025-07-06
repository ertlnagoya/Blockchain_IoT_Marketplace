<script lang="ts">
	import { ethers } from 'ethers';
	import { Merchandise__factory } from '../types/typechain-types/index.js';
	
	let queryResult: any = null;
	let startTime: string = '2025-06-30T08:00:00';
	let endTime: string = '2025-06-30T12:20:00';
	let latitude: string = '35.15430131582339';
	let longitude: string = '136.9700924892541';
	let radius: string = '50'; // デフォルト50m
	let filterByTime: boolean = false;
	let filterByLocation: boolean = false;
	let filterByPeople: boolean = false;
	let peopleExist: boolean = true;

	// MetaMaskに接続する関数
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

	// 購入機能
	const purchase = async (merchandiseData: any) => {
		try {
			const { provider, signer } = await connectToMetaMask();
			const merchandise = Merchandise__factory.connect(merchandiseData.address, signer);
			
			if (signer) {
				const transactionResponse = await merchandise.purchase({
					value: ethers.parseEther(merchandiseData.price || '0.01')
				});
				
				alert('購入処理を開始しました。トランザクションの確認をお待ちください...');
				await transactionResponse.wait(1);
				alert('購入が完了しました！');
			} else {
				throw new Error('MetaMaskに接続してください');
			}
		} catch (error: any) {
			alert(`購入エラー: ${error.message}`);
			console.error('Purchase error:', error);
		}
	};

	async function executeSearch() {
		// ベースクエリを構築
		let query = 'SELECT *';
		let conditions: string[] = [];
		
		// 場所フィルタが有効な場合は距離も取得
		if (filterByLocation) {
			query += `, ST_Distance(location, ST_GeogFromText('POINT(${longitude} ${latitude})')) AS distance`;
		}
		
		query += ' FROM ipfs_records';
		
		// 時間フィルタを追加
		if (filterByTime) {
			if (!startTime || !endTime) {
				alert('時間フィルタを有効にする場合は開始時刻と終了時刻を両方指定してください。');
				return;
			}
			conditions.push(`start_timestamp >= '${startTime}'`);
			conditions.push(`end_timestamp <= '${endTime}'`);
		}
		
		// 場所フィルタを追加
		if (filterByLocation) {
			if (!latitude || !longitude) {
				alert('場所フィルタを有効にする場合は緯度と経度を両方指定してください。');
				return;
			}
			const radiusMeters = parseFloat(radius);
			conditions.push(`ST_DWithin(location, ST_GeogFromText('POINT(${longitude} ${latitude})'), ${radiusMeters})`);
		}
		
		// 人の存在フィルタを追加
		if (filterByPeople) {
			conditions.push(`exist_people = ${peopleExist}`);
		}
		
		// 条件を追加
		if (conditions.length > 0) {
			query += ' WHERE ' + conditions.join(' AND ');
		}
		
		// 場所フィルタが有効な場合は距離順にソート
		if (filterByLocation) {
			query += ' ORDER BY distance';
		}
		
		query += ';';
		
		console.log('Executing query:', query);
		
		const response = await fetch('/api/sql-query', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ query })
		});
		queryResult = await response.json();
	}
</script>

<div class="mt-8 flex flex-col items-center space-y-6">
	<h2 class="text-2xl font-bold">IoT データ検索</h2>
	
	<!-- デバッグ情報 -->
	<div class="text-xs text-gray-600">
		フィルタ状態: 時間={filterByTime}, 場所={filterByLocation}, 人={filterByPeople}
	</div>
	
	<!-- 検索条件設定 -->
	<div class="bg-gray-50 p-6 rounded-lg space-y-4">
		<h3 class="text-lg font-semibold text-black">検索条件</h3>
		
		<!-- 時間フィルタ -->
		<div class="space-y-2">
			<div class="flex items-center space-x-2">
				<input
					id="filterTime"
					type="checkbox"
					bind:checked={filterByTime}
					class="rounded bg-white border-gray-300"
				/>
				<label for="filterTime" class="text-sm font-medium text-black cursor-pointer">時間で絞り込む</label>
			</div>
			
			{#if filterByTime}
				<div class="flex space-x-4 ml-6">
					<div class="flex flex-col">
						<label class="text-sm font-medium text-black">開始時刻</label>
						<input
							type="datetime-local"
							bind:value={startTime}
							class="px-3 py-2 border rounded text-black"
						/>
					</div>
					<div class="flex flex-col">
						<label class="text-sm font-medium text-black">終了時刻</label>
						<input
							type="datetime-local"
							bind:value={endTime}
							class="px-3 py-2 border rounded text-black"
						/>
					</div>
				</div>
			{/if}
		</div>
		
		<!-- 場所フィルタ -->
		<div class="space-y-2">
			<div class="flex items-center space-x-2">
				<input
					id="filterLocation"
					type="checkbox"
					bind:checked={filterByLocation}
					class="rounded bg-white border-gray-300"
				/>
				<label for="filterLocation" class="text-sm font-medium text-black cursor-pointer">場所で絞り込む</label>
			</div>
			
			{#if filterByLocation}
				<div class="flex space-x-4 ml-6">
					<div class="flex flex-col">
						<label class="text-sm font-medium text-black">緯度</label>
						<input
							type="number"
							step="0.000001"
							bind:value={latitude}
							placeholder="例: 35.6762"
							class="px-3 py-2 border rounded text-black"
						/>
					</div>
					<div class="flex flex-col">
						<label class="text-sm font-medium text-black">経度</label>
						<input
							type="number"
							step="0.000001"
							bind:value={longitude}
							placeholder="例: 139.6503"
							class="px-3 py-2 border rounded text-black"
						/>
					</div>
					<div class="flex flex-col">
						<label class="text-sm font-medium text-black">半径 (m)</label>
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
		
		<!-- 人の存在フィルタ -->
		<div class="space-y-2">
			<div class="flex items-center space-x-2">
				<input
					id="filterPeople"
					type="checkbox"
					bind:checked={filterByPeople}
					class="rounded bg-white border-gray-300"
				/>
				<label for="filterPeople" class="text-sm font-medium text-black cursor-pointer">人の存在で絞り込む</label>
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
						<span class="text-sm text-black">人がいる</span>
					</label>
					<label class="flex items-center space-x-2">
						<input
							type="radio"
							bind:group={peopleExist}
							value={false}
							name="peopleExist"
						/>
						<span class="text-sm text-black">人がいない</span>
					</label>
				</div>
			{/if}
		</div>
		
		<!-- 検索ボタン -->
		<button 
			class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
			on:click={executeSearch}
		>
			検索実行
		</button>
	</div>
	
	{#if queryResult && Array.isArray(queryResult)}
		<table class="mt-4 bg-gray-100 p-2 rounded text-xs text-black">
			<thead>
				<tr>
					<th class="px-2 py-1 text-black">CID</th>
					<th class="px-2 py-1 text-black">開始時刻</th>
					<th class="px-2 py-1 text-black">終了時刻</th>
					<th class="px-2 py-1 text-black">位置情報</th>
					<th class="px-2 py-1 text-black">人の存在</th>
					{#if filterByLocation}
						<th class="px-2 py-1 text-black">距離 (m)</th>
					{/if}
					<th class="px-2 py-1 text-black">IPFSデータ</th>
					<th class="px-2 py-1 text-black">アクション</th>
				</tr>
			</thead>
			<tbody>
				{#each queryResult as row}
					<tr>
						<td class="px-2 py-1 text-black">{row.cid}</td>
						<td class="px-2 py-1 text-black">{row.start_timestamp}</td>
						<td class="px-2 py-1 text-black">{row.end_timestamp}</td>
						<td class="px-2 py-1 text-black">{row.location}</td>
						<td class="px-2 py-1 text-black">{row.exist_people ? 'あり' : 'なし'}</td>
						{#if filterByLocation}
							<td class="px-2 py-1 text-black">
								{row.distance ? Math.round(row.distance) : 'N/A'}
							</td>
						{/if}
						<td class="px-2 py-1 text-black">
							{#if row.ipfs_data}
								{#if row.ipfs_data.error}
									<span class="text-red-600">エラー: {row.ipfs_data.error}</span>
								{:else if row.ipfs_data.type === 'text'}
									<details>
										<summary class="cursor-pointer text-blue-600">テキストデータ</summary>
										<pre class="mt-2 text-xs">{row.ipfs_data.content}</pre>
									</details>
								{:else}
									<details>
										<summary class="cursor-pointer text-blue-600">JSONデータ</summary>
										<pre class="mt-2 text-xs">{JSON.stringify(row.ipfs_data, null, 2)}</pre>
									</details>
								{/if}
							{:else}
								<span class="text-gray-500">データなし</span>
							{/if}
						</td>
						<td class="px-2 py-1 text-black">
							{#if row.ipfs_data && row.ipfs_data.address && !row.ipfs_data.error}
								<button 
									class="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 transition-colors"
									on:click={() => purchase(row.ipfs_data)}
								>
									購入
								</button>
								<div class="text-xs mt-1">
									{row.ipfs_data.price || '0.01'} ETH
								</div>
							{:else}
								<span class="text-gray-500 text-xs">購入不可</span>
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
