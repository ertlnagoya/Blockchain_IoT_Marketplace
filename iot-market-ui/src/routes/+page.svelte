<script lang="ts">
	let queryResult: any = null;
	let startTime: string = '';
	let endTime: string = '';

	async function sendSqlQuery() {
		const response = await fetch('/api/sql-query', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ query: 'SELECT * FROM ipfs_records;' })
		});
		queryResult = await response.json();
	}

	async function searchByTimeRange() {
		if (!startTime || !endTime) {
			alert('開始時刻と終了時刻を両方指定してください。');
			return;
		}

		const query = `SELECT * FROM ipfs_records WHERE start_timestamp >= '${startTime}' AND end_timestamp <= '${endTime}';`;
		const response = await fetch('/api/sql-query', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ query })
		});
		queryResult = await response.json();
	}
</script>

<div class="mt-8 flex flex-col items-center">
	<button class="px-4 py-2 bg-blue-600 text-white rounded" on:click={sendSqlQuery}>
		SQLクエリを送信
	</button>
	
	<!-- 時刻範囲検索セクション -->
	<div class="mt-6 flex flex-col items-center space-y-4">
		<h3 class="text-lg font-semibold">時刻範囲検索</h3>
		<div class="flex space-x-4">
			<div class="flex flex-col">
				<label class="text-sm font-medium">開始時刻</label>
				<input
					type="datetime-local"
					bind:value={startTime}
					class="px-3 py-2 border rounded text-black"
				/>
			</div>
			<div class="flex flex-col">
				<label class="text-sm font-medium">終了時刻</label>
				<input
					type="datetime-local"
					bind:value={endTime}
					class="px-3 py-2 border rounded text-black"
				/>
			</div>
		</div>
		<button class="px-4 py-2 bg-green-600 text-white rounded" on:click={searchByTimeRange}>
			時刻範囲で検索
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
				</tr>
			</thead>
			<tbody>
				{#each queryResult as row}
					<tr>
						<td class="px-2 py-1 text-black">{row.cid}</td>
						<td class="px-2 py-1 text-black">{row.start_timestamp}</td>
						<td class="px-2 py-1 text-black">{row.end_timestamp}</td>
						<td class="px-2 py-1 text-black">{row.location}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{:else if queryResult}
		<pre class="mt-4 bg-gray-100 p-2 rounded text-xs">{JSON.stringify(queryResult, null, 2)}</pre>
	{/if}
</div>
