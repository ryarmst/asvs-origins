<script lang="ts">
	import { base } from '$app/paths';
	import StatusChips from '$lib/components/StatusChips.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>Chapters — asvs-origins</title>
</svelte:head>

<h1>Chapters</h1>
<p class="lede">Pick a chapter, then a requirement. Enrichment is labeled on each control.</p>
<ul class="list">
	{#each data.chapters as chapter}
		<li>
			<a href="{base}/chapters/{chapter.id}">{chapter.id} {chapter.name}</a>
			<span class="meta"> · {chapter.requirement_ids.length}</span>
			<div class="meta">
				{#each Object.entries(chapter.by_coverage) as [state, count]}
					{state} {count}.
				{/each}
			</div>
		</li>
	{/each}
</ul>
