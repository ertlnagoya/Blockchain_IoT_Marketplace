<script lang="ts">
	 import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	 import { defaultProviderEndpoint, marketHomeUrl } from '$lib/config/providers';
	import {
		parseProviderCredential,
		summarizeProvider,
		buildProviderProfilePayload,
		ProviderVcError
	} from '$lib/provider/verification';
	import type { ProviderProfileSummary } from '$lib/provider/verification';
	 import { providerVerification } from '$lib/stores/providerVerification';
	 import { hasPendingPurchase, flagAutoPurchase } from '$lib/purchase/pending';

	let vcInput = '';
	let endpoint = defaultProviderEndpoint;
	let summary: ProviderProfileSummary | null = null;
	let statusMessage = '';
	let profileResponse: any = null;
	let isSubmitting = false;
	let uploadError = '';

	let fileInput: HTMLInputElement | null = null;

	onMount(() => {
		statusMessage =
			providerVerification ? '等待提交 Provider VC 完成验证。' : '无法初始化 providerVerification store';
	});

	async function handleFileChange(event: Event) {
		uploadError = '';
		const target = event.target as HTMLInputElement;
		if (!target?.files?.length) return;
		const file = target.files[0];
		try {
			const text = await file.text();
			vcInput = text;
		} catch (error) {
			uploadError = '读取文件失败';
		}
	}

	function humanReadableLevel(level: number): string {
		if (level >= 2) return 'FULL ACCESS';
		if (level === 1) return 'LIMITED ACCESS';
		return 'DENIED';
	}

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		uploadError = '';
		profileResponse = null;
		statusMessage = '';

		try {
			isSubmitting = true;
			providerVerification.markVerifying();
			const { credential, source } = parseProviderCredential(vcInput);
			summary = summarizeProvider(credential, undefined, source);
			const payload = buildProviderProfilePayload(summary);

			const res = await fetch(`${endpoint}/provider-profile`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});

			if (!res.ok) {
				const errBody = await res.text();
				throw new Error(`Provider API 返回 ${res.status}: ${errBody}`);
			}

			profileResponse = await res.json();
			providerVerification.markVerified({
				level: summary.level,
				providerDID: summary.providerDID,
				issuerDID: summary.issuerDID,
				vcID: summary.vcID
			});
			statusMessage = `验证完成：${humanReadableLevel(summary.level)}`;
			if (summary.level >= 2) {
				const pendingExists = hasPendingPurchase();
				statusMessage += pendingExists
					? '，正在自动返回市场继续购买...'
					: '，正在返回市场主页...';
				if (pendingExists) {
					flagAutoPurchase();
				}
				setTimeout(() => {
					goto(marketHomeUrl);
				}, 800);
			}
		} catch (error) {
			summary = null;
			const fallbackMessage =
				error instanceof ProviderVcError
					? error.message
					: error instanceof Error && error.message
						? error.message
						: '未知错误';
			uploadError = fallbackMessage;
			providerVerification.markError(fallbackMessage);
		} finally {
			isSubmitting = false;
		}
	}
</script>

<svelte:head>
	<title>Provider 证明中心</title>
</svelte:head>

<section class="max-w-3xl mx-auto py-12 space-y-8 text-black">
	<div class="space-y-2">
		<h1 class="text-3xl font-semibold">Provider 零知识证明</h1>
		<p class="text-gray-600">
			在这里提交 Provider 的 Verifiable Credential (VC)，完成零知识证明后，前端将显示 FULL ACCESS，才能响应购买请求。
		</p>
	</div>

	<div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
		<h2 class="text-lg font-medium text-gray-800">当前状态</h2>
		{#if $providerVerification.status === 'verified'}
			<p class="text-green-600 font-semibold">
				{$providerVerification.providerDID} · {humanReadableLevel($providerVerification.level)}
			</p>
			<p class="text-xs text-gray-500">更新于 {$providerVerification.updatedAt}</p>
		{:else if $providerVerification.status === 'verifying'}
			<p class="text-amber-600">正在验证 VC ...</p>
		{:else if $providerVerification.status === 'error'}
			<p class="text-red-600">{ $providerVerification.error }</p>
		{:else}
			<p class="text-gray-600">尚未提交 VC。</p>
		{/if}
		{#if statusMessage}
			<p class="text-sm text-blue-600">{statusMessage}</p>
		{/if}
	</div>

	<form class="space-y-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm" on:submit|preventDefault={handleSubmit}>
		<div class="space-y-2">
			<label class="text-sm font-medium text-gray-700" for="providerVcInput">Provider VC (JSON 或 JWT)</label>
			<textarea
				id="providerVcInput"
				class="w-full rounded border border-gray-300 p-3 font-mono text-sm"
				rows="8"
				bind:value={vcInput}
				placeholder="粘贴 provider VC JSON 或 JWT"
				required
			></textarea>
		</div>

		<div class="space-y-2">
			<label class="text-sm font-medium text-gray-700" for="providerVcFile">或选择 VC 文件</label>
			<input id="providerVcFile" type="file" accept=".json,.jwt,.txt" bind:this={fileInput} on:change={handleFileChange} class="block w-full text-sm text-gray-600" />
		</div>

		<div class="space-y-2">
			<label class="text-sm font-medium text-gray-700" for="providerEndpointInput">Provider API Endpoint</label>
			<input
				id="providerEndpointInput"
				type="url"
				class="w-full rounded border border-gray-300 p-2"
				bind:value={endpoint}
				placeholder="http://localhost:4002"
				required
			/>
		</div>

		{#if uploadError}
			<p class="text-sm text-red-600">{uploadError}</p>
		{/if}

		<button
			type="submit"
			class="w-full rounded-lg bg-blue-600 py-3 text-white font-semibold hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
			disabled={isSubmitting}
		>
			{#if isSubmitting}
				提交中...
			{:else}
				提交 VC 并生成证明
			{/if}
		</button>
	</form>

	{#if summary}
		<div class="rounded-xl border border-green-200 bg-green-50 p-6 space-y-2">
			<h3 class="text-lg font-semibold text-green-800">验证结果</h3>
			<p class="text-sm text-green-700">Provider DID: {summary.providerDID}</p>
			<p class="text-sm text-green-700">Issuer: {summary.issuerDID || '未知'}</p>
			<p class="text-sm text-green-700">Level: {humanReadableLevel(summary.level)}</p>
			{#if summary.vcID}
				<p class="text-sm text-green-700">VC ID: {summary.vcID}</p>
			{/if}
			{#if summary.purpose}
				<p class="text-sm text-green-700">Purpose: {summary.purpose}</p>
			{/if}
		</div>
	{/if}

	{#if profileResponse}
		<div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
			<h3 class="text-lg font-semibold text-gray-800">Provider API 响应</h3>
			<pre class="mt-2 text-xs bg-gray-50 p-3 rounded overflow-x-auto">{JSON.stringify(profileResponse, null, 2)}</pre>
		</div>
	{/if}
</section>
