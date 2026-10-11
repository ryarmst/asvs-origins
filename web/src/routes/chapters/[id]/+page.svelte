<script lang="ts">
	import { base } from '$app/paths';
	import ChapterNav from '$lib/components/ChapterNav.svelte';
	import StatusChips from '$lib/components/StatusChips.svelte';
	let { data } = $props();
</script>

<svelte:head>
	<title>{data.chapter.id} {data.chapter.name} — asvs-origins</title>
</svelte:head>

<ChapterNav chapters={data.chapters} current={data.chapter.id} />
<p class="kicker">Chapter</p>
<h1>{data.chapter.id} {data.chapter.name}</h1>
<p class="meta">
	{data.requirements.length} requirements.
	{#each Object.entries(data.chapter.by_coverage) as [state, count]}
		{state} {count}.
	{/each}
</p>

{#each data.chapter.sections as section}
	<h2>{section.id} {section.name}</h2>
	<ul class="list">
		{#each data.requirements.filter((item) => item.section_id === section.id) as item}
			<li>
				<a href="{base}/requirements/{item.id}">{item.id}</a>
				<StatusChips coverage={item.coverage} enrichment={item.enrichment} blocked={item.blocked_reason} />
				<span class="meta"> L{item.level ?? '—'}</span>
				<div>{item.text}</div>
			</li>
		{/each}
	</ul>
{/each}

{#if data.issues.length}
	<h2>Linked issues</h2>
	<ul class="list">
		{#each data.issues.slice(0, 40) as issue}
			<li>
				<a href="{base}/issues/{issue.number}">#{issue.number}</a>
				{issue.title}
				<span class="meta"> · {issue.coverage}</span>
			</li>
		{/each}
	</ul>
{/if}
