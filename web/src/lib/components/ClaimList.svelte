<script lang="ts">
	import type { Claim } from '$lib/types';
	import { isPublic, isUnreviewedAi } from '$lib/provenance';
	import ProvenanceBadge from './ProvenanceBadge.svelte';
	import Citations from './Citations.svelte';

	let { claims, title }: { claims: Claim[]; title: string } = $props();
	const visible = $derived(claims.filter((claim) => isPublic(claim.provenance)));
</script>

{#if visible.length}
	<h2>{title}</h2>
	{#each visible as claim}
		<article class="block" class:unreviewed={isUnreviewedAi(claim.provenance)}>
			<ProvenanceBadge provenance={claim.provenance} />
			<p>{claim.statement}</p>
			<p class="meta">
				{claim.kind}
				{#if claim.subkind}· {claim.subkind}{/if}
				· {claim.status}
				{#if claim.actors.length}· {claim.actors.join(', ')}{/if}
				{#if claim.date}· {claim.date}{/if}
			</p>
			<Citations citations={claim.citations} />
		</article>
	{/each}
{/if}
