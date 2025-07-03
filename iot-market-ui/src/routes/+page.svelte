<script lang="ts">
	let queryResult: any = null;
	let startTime: string = '2025-06-30T08:00:00';
	let endTime: string = '2025-06-30T12:20:00';
	let latitude: string = '35.15430131582339';
	let longitude: string = '136.9700924892541';
	let radius: string = '50'; // デフォルト50m
	let filterByPeople: boolean = false;
	let peopleExist: boolean = true;

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

		let query = `SELECT * FROM ipfs_records WHERE start_timestamp >= '${startTime}' AND end_timestamp <= '${endTime}'`;
		
		if (filterByPeople) {
			query += ` AND exist_people = ${peopleExist}`;
		}
		
		query += ';';
		
		const response = await fetch('/api/sql-query', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ query })
		});
		queryResult = await response.json();
	}

	async function searchByTimeAndLocation() {
		if (!startTime || !endTime) {
			alert('開始時刻と終了時刻を両方指定してください。');
			return;
		}
		if (!latitude || !longitude) {
			alert('緯度と経度を両方指定してください。');
			return;
		}

		// PostGIS GEOGRAPHY型を使用したシンプルなクエリ
		const radiusMeters = parseFloat(radius);
		let query = `
			SELECT *, 
				ST_Distance(location, ST_GeogFromText('POINT(${longitude} ${latitude})')) AS distance
			FROM ipfs_records 
			WHERE start_timestamp >= '${startTime}' 
				AND end_timestamp <= '${endTime}'
				AND ST_DWithin(location, ST_GeogFromText('POINT(${longitude} ${latitude})'), ${radiusMeters})
		`;
		
		if (filterByPeople) {
			query += ` AND exist_people = ${peopleExist}`;
		}
		
		query += ' ORDER BY distance;';
		
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
		<div class="flex items-center space-x-4">
			<label class="flex items-center space-x-2">
				<input
					type="checkbox"
					bind:checked={filterByPeople}
					class="rounded"
				/>
				<span class="text-sm">人の存在で絞り込む</span>
			</label>
			{#if filterByPeople}
				<label class="flex items-center space-x-2">
					<input
						type="radio"
						bind:group={peopleExist}
						value={true}
						name="peopleExist"
					/>
					<span class="text-sm">人がいる</span>
				</label>
				<label class="flex items-center space-x-2">
					<input
						type="radio"
						bind:group={peopleExist}
						value={false}
						name="peopleExist"
					/>
					<span class="text-sm">人がいない</span>
				</label>
			{/if}
		</div>
		<button class="px-4 py-2 bg-green-600 text-white rounded" on:click={searchByTimeRange}>
			時刻範囲で検索
		</button>
	</div>
	
	<!-- 時刻と場所の複合検索セクション -->
	<div class="mt-6 flex flex-col items-center space-y-4">
		<h3 class="text-lg font-semibold">時刻と場所の複合検索</h3>
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
		<div class="flex space-x-4">
			<div class="flex flex-col">
				<label class="text-sm font-medium">緯度</label>
				<input
					type="number"
					step="0.000001"
					bind:value={latitude}
					placeholder="例: 35.6762"
					class="px-3 py-2 border rounded text-black"
				/>
			</div>
			<div class="flex flex-col">
				<label class="text-sm font-medium">経度</label>
				<input
					type="number"
					step="0.000001"
					bind:value={longitude}
					placeholder="例: 139.6503"
					class="px-3 py-2 border rounded text-black"
				/>
			</div>
			<div class="flex flex-col">
				<label class="text-sm font-medium">半径 (m)</label>
				<input
					type="number"
					step="1"
					bind:value={radius}
					class="px-3 py-2 border rounded text-black"
				/>
			</div>
		</div>
		<div class="flex items-center space-x-4">
			<label class="flex items-center space-x-2">
				<input
					type="checkbox"
					bind:checked={filterByPeople}
					class="rounded"
				/>
				<span class="text-sm">人の存在で絞り込む</span>
			</label>
			{#if filterByPeople}
				<label class="flex items-center space-x-2">
					<input
						type="radio"
						bind:group={peopleExist}
						value={true}
						name="peopleExist"
					/>
					<span class="text-sm">人がいる</span>
				</label>
				<label class="flex items-center space-x-2">
					<input
						type="radio"
						bind:group={peopleExist}
						value={false}
						name="peopleExist"
					/>
					<span class="text-sm">人がいない</span>
				</label>
			{/if}
		</div>
		<button class="px-4 py-2 bg-purple-600 text-white rounded" on:click={searchByTimeAndLocation}>
			時刻と場所で検索
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
					</tr>
				{/each}
			</tbody>
		</table>
	{:else if queryResult}
		<pre class="mt-4 bg-gray-100 p-2 rounded text-xs">{JSON.stringify(queryResult, null, 2)}</pre>
	{/if}
</div>
