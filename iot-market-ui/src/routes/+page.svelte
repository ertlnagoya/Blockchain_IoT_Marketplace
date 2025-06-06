<script lang="ts">
	import Card from '$lib/components/Card.svelte';
	const { data } = $props();
</script>

<section id="merchandises" class="container mx-auto mt-4">
	<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
		{#each data.clientData as merchandise}
			<a href="/merchandise/{merchandise.address}" class="lg:w-3/1">
				<Card title={merchandise.address} price={merchandise.price}></Card>
			</a>
		{/each}
	</div>
</section>
