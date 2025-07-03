<script lang="ts">
	let queryResult: any = null;

	async function sendSqlQuery() {
		const response = await fetch('/api/sql-query', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ query: 'SELECT * FROM ipfs_records;' })
		});
		queryResult = await response.json();
	}
</script>

<div class="mt-8 flex flex-col items-center">
	<button class="px-4 py-2 bg-blue-600 text-white rounded" on:click={sendSqlQuery}>
		SQLクエリを送信
	</button>
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
