<script lang="ts">
	import { base } from '$app/paths';
	import StatusChips from '$lib/components/StatusChips.svelte';

	let { data } = $props();
	const req = $derived(data.coverage.requirements);
	const mix = $derived(data.coverage.provenance_mix_published);
</script>

<svelte:head>
	<title>asvs-origins</title>
</svelte:head>

<p class="kicker">OWASP ASVS companion</p>
<h1>Where each requirement came from</h1>
<p class="lede">
	Identify a control, read the mirrored text and the origin story, then open the sources if you want
	to add a human note. This is not a review queue — enrichment state is labeled on every page.
</p>

<div class="grid" style="margin-top: 1.5rem">
	<div class="stat">
		<b>{req.reviewed_or_better_pct}%</b>
		human-reviewed or authored ({req.reviewed_or_better} / {req.total})
	</div>
	<div class="stat">
		<b>{req.lineage_complete_pct}%</b>
		lineage complete
	</div>
	<div class="stat">
		<b>{req.sourced_pct}%</b>
		have key sources
	</div>
	<div class="stat">
		<b>{req.orphans_without_key_sources}</b>
		without key sources
	</div>
</div>

<h2>Find a requirement</h2>
<p class="meta">Search IDs, old numbers, wording, origin notes, and issue threads.</p>
<ul class="list">
	<li><a href="{base}/search">Open search</a></li>
	<li><a href="{base}/requirements">Browse all {req.total} controls</a></li>
	<li><a href="{base}/lineage">4.0.3 → 5.0.0 mapping</a>, aligned with <a href="https://asvs.dev/mapping_v4.0.3_to_v5.0.0.html">asvs.dev</a></li>
</ul>

<h2>Chapters</h2>
<ul class="list">
	{#each data.chapters as chapter}
		<li>
			<a href="{base}/chapters/{chapter.id}">{chapter.id} {chapter.name}</a>
			<span class="meta">
				· {chapter.requirement_ids.length} requirements
				{#each Object.entries(chapter.by_coverage) as [state, count]}
					· {state} {count}
				{/each}
			</span>
		</li>
	{/each}
</ul>

<h2>Provenance mix</h2>
<p class="meta">Published artifacts (rejected drafts omitted).</p>
<ul class="list">
	{#each Object.entries(mix) as [origin, count]}
		<li>{origin}: {count}</li>
	{/each}
</ul>

{#if data.authored.length}
	<h2>Human-authored seed</h2>
	<ul class="list">
		{#each data.authored as item}
			<li>
				<a href="{base}/requirements/{item.id}">{item.id}</a>
				<StatusChips coverage={item.coverage} enrichment={item.enrichment} />
				<div>{item.text}</div>
			</li>
		{/each}
	</ul>
{/if}
