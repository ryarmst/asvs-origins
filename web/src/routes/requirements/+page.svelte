<script lang="ts">
	import { base } from '$app/paths';
	import StatusChips from '$lib/components/StatusChips.svelte';

	let { data } = $props();
	let query = $state('');
	let chapter = $state('all');
	let enrichment = $state('all');
	const filtered = $derived(
		data.requirements.filter((item) => {
			if (chapter !== 'all' && item.chapter_id !== chapter) return false;
			if (enrichment !== 'all' && item.enrichment !== enrichment) return false;
			if (!query.trim()) return true;
			const q = query.toLowerCase();
			return (
				item.id.toLowerCase().includes(q) ||
				item.slug.includes(q) ||
				item.text.toLowerCase().includes(q)
			);
		})
	);
</script>

<svelte:head>
	<title>Requirements — asvs-origins</title>
</svelte:head>

<h1>Requirements</h1>
<p class="lede">ASVS 5.0.0, {data.requirements.length} controls. File paths use the current ID; permalinks use a stable uid.</p>

<div class="filter-row">
	<input type="search" placeholder="Filter by ID or text" bind:value={query} />
	<select bind:value={chapter}>
		<option value="all">All chapters</option>
		{#each data.chapters as item}
			<option value={item.id}>{item.id} {item.name}</option>
		{/each}
	</select>
	<select bind:value={enrichment}>
		<option value="all">Any enrichment</option>
		<option value="human">Human</option>
		<option value="ai_reviewed">AI · reviewed</option>
		<option value="ai_draft">AI draft</option>
		<option value="extracted">Extracted</option>
		<option value="none">Not enriched</option>
	</select>
</div>
<p class="meta">{filtered.length} shown.</p>

<ul class="list">
	{#each filtered as item}
		<li>
			<a href="{base}/requirements/{item.id}">{item.id}</a>
			<StatusChips coverage={item.coverage} enrichment={item.enrichment} blocked={item.blocked_reason} />
			<span class="meta"> L{item.level ?? '—'} · {item.chapter_name}</span>
			<div>{item.text}</div>
		</li>
	{/each}
</ul>
