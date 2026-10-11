<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import type { Chapter } from '$lib/types';

	let {
		chapters,
		current
	}: {
		chapters: Chapter[];
		current?: string | null;
	} = $props();

	const index = $derived(chapters.findIndex((item) => item.id === current));
	const prev = $derived(index > 0 ? chapters[index - 1] : null);
	const next = $derived(index >= 0 && index < chapters.length - 1 ? chapters[index + 1] : null);

	function onChange(event: Event) {
		const value = (event.currentTarget as HTMLSelectElement).value;
		goto(`${base}/chapters/${value}`);
	}
</script>

<div class="chapter-switch">
	{#if prev}
		<a class="btn secondary" href="{base}/chapters/{prev.id}">{prev.id}</a>
	{/if}
	<select onchange={onChange} value={current ?? chapters[0]?.id}>
		{#each chapters as chapter}
			<option value={chapter.id}>{chapter.id} {chapter.name}</option>
		{/each}
	</select>
	{#if next}
		<a class="btn secondary" href="{base}/chapters/{next.id}">{next.id}</a>
	{/if}
</div>
