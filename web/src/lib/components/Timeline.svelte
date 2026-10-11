<script lang="ts">
	import type { LineageEvent } from '$lib/types';
	import { collapseKind } from '$lib/provenance';
	import Citations from './Citations.svelte';

	let { events }: { events: LineageEvent[] } = $props();
	let showCollapsed = $state(false);
	const collapsed = $derived(events.filter((event) => collapseKind(event.kind)));
	const visible = $derived(
		showCollapsed ? events : events.filter((event) => !collapseKind(event.kind))
	);
</script>

{#if collapsed.length}
	<p class="meta">
		<button class="btn secondary" type="button" onclick={() => (showCollapsed = !showCollapsed)}>
			{showCollapsed ? 'Hide' : 'Show'} {collapsed.length} numbering / cleanup events
		</button>
	</p>
{/if}
<ol class="timeline">
	{#each visible as event}
		<li>
			<p class="meta">{event.date} · {event.kind}{#if event.id_at_time} · {event.id_at_time}{/if}{#if event.actor} · {event.actor}{/if}</p>
			<p>{event.summary}</p>
			<Citations citations={event.citations} />
		</li>
	{/each}
</ol>
