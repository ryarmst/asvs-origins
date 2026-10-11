<script lang="ts">
	import type { Summary } from '$lib/types';
	import { isUnreviewedAi } from '$lib/provenance';
	import { proseHtml } from '$lib/text';
	import ProvenanceBadge from './ProvenanceBadge.svelte';
	import Citations from './Citations.svelte';

	let {
		summary,
		title
	}: {
		summary: Summary;
		title?: string;
	} = $props();
</script>

<article class="block" class:unreviewed={isUnreviewedAi(summary.provenance)}>
	{#if title}
		<h3>{title}</h3>
	{/if}
	<ProvenanceBadge provenance={summary.provenance} />
	<div>{@html proseHtml(summary.body)}</div>
	<Citations citations={summary.citations} />
</article>
