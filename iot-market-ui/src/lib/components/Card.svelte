<script lang="ts">
	let { title, price } = $props();
</script>

<div class="rounded-lg border border-indigo-500/50 text-white">
	<div class="bg-gray-800 p-4">
		<h2 class="">{title}</h2>
	</div>
	<div class="p-4">Price: {price} ETH</div>
</div>
