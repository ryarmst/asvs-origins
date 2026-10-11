<script lang="ts">
	import { base } from '$app/paths';
	import type { Provenance } from '$lib/types';
	import { badgeKind, badgeLabel, chipClass } from '$lib/provenance';

	let { provenance }: { provenance: Provenance } = $props();
	let open = $state(false);
	const kind = $derived(badgeKind(provenance));
</script>

<button
	type="button"
	class="chip {chipClass(kind)}"
	onclick={() => (open = !open)}
	aria-expanded={open}
>
	{badgeLabel(kind, provenance.review.status)}
	{#if provenance.confidence === 'low'}· low confidence{/if}
</button>
{#if open}
	<div class="provenance-panel">
		<dl>
			<dt>Origin</dt>
			<dd>{provenance.origin.replace('_', ' ')}</dd>
			<dt>Review</dt>
			<dd>{provenance.review.status.replace('_', ' ')}</dd>
			<dt>Confidence</dt>
			<dd>{provenance.confidence}</dd>
			{#if provenance.authors.length}
				<dt>Authors</dt>
				<dd>
					{#each provenance.authors as author, i}
						{i ? ', ' : ''}<a href="{base}/people/{author.github}">{author.github}</a>
					{/each}
				</dd>
			{/if}
			{#if provenance.model}
				<dt>Model</dt>
				<dd>{provenance.model.id} · {provenance.model.prompt_id} {provenance.model.prompt_version}</dd>
			{/if}
			<dt>Created</dt>
			<dd>{provenance.created_at}</dd>
			{#if provenance.review.by.length}
				<dt>Reviewed</dt>
				<dd>
					{provenance.review.by.join(', ')}
					{#if provenance.review.at} · {provenance.review.at}{/if}
				</dd>
			{/if}
			{#if provenance.review.note}
				<dt>Note</dt>
				<dd>{provenance.review.note}</dd>
			{/if}
		</dl>
	</div>
{/if}
