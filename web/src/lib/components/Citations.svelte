<script lang="ts">
	import type { Citation } from '$lib/types';
	import { citationLabel } from '$lib/provenance';

	let { citations }: { citations: Citation[] } = $props();
</script>

{#if citations.length === 0}
	<span class="uncited">uncited</span>
{:else}
	<p class="citations">
		{#each citations as citation, i}
			{i > 0 ? ' · ' : ''}
			<a href={citation.url} rel="noreferrer">{citationLabel(citation)}</a>
			{#if citation.quote}
				<span> “{citation.quote}”</span>
			{/if}
		{/each}
	</p>
{/if}
