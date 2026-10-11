<script lang="ts">
	import { base } from '$app/paths';
	import StatusChips from '$lib/components/StatusChips.svelte';

	let { data } = $props();
	let query = $state('');
	let coverage = $state('all');
	let relevance = $state('all');
	const filtered = $derived(
		data.issues.filter((item) => {
			if (coverage !== 'all' && item.coverage !== coverage) return false;
			if (relevance !== 'all' && item.relevance !== relevance) return false;
			if (!query.trim()) return true;
			const q = query.toLowerCase();
			return (
				String(item.number).includes(q) ||
				item.title.toLowerCase().includes(q) ||
				(item.author ?? '').toLowerCase().includes(q)
			);
		})
	);
</script>

<svelte:head>
	<title>Issues — asvs-origins</title>
</svelte:head>

<h1>Issues</h1>
<p class="lede">{data.issues.length} mirrored OWASP/ASVS issues.</p>

<div class="filter-row">
	<input type="text" placeholder="Number, title, or author" bind:value={query} />
	<select bind:value={coverage}>
		<option value="all">All coverage</option>
		<option value="authored">authored</option>
		<option value="drafted">drafted</option>
		<option value="linked">linked</option>
		<option value="empty">empty</option>
	</select>
	<select bind:value={relevance}>
		<option value="all">All triage</option>
		<option value="requirement_bearing">requirement-bearing</option>
		<option value="chapter_bearing">chapter-bearing</option>
		<option value="no_requirement">no requirement</option>
	</select>
</div>
<p class="meta">{filtered.length} shown.</p>
<ul class="list">
	{#each filtered as item}
		<li>
			<a href="{base}/issues/{item.number}">#{item.number}</a>
			{item.title}
			<StatusChips coverage={item.coverage} />
			<span class="meta">
				· {item.state}
				{#if item.relevance} · {item.relevance}{/if}
			</span>
		</li>
	{/each}
</ul>
