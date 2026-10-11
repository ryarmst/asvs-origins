<script lang="ts">
	import { coverageLabel, enrichmentClass, enrichmentLabel } from '$lib/provenance';

	let {
		coverage,
		enrichment,
		blocked
	}: {
		coverage?: string | null;
		enrichment?: string | null;
		blocked?: string | null;
	} = $props();
</script>

<span class="chip-row">
	{#if coverage}
		<span class="chip chip-muted">{coverageLabel(coverage)}</span>
	{/if}
	{#if enrichment}
		<span class="chip {enrichmentClass(enrichment)}">{enrichmentLabel(enrichment)}</span>
	{/if}
	{#if blocked}
		<span class="chip chip-blocked">Blocked</span>
	{/if}
</span>
