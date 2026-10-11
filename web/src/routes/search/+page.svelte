<script lang="ts">
	import { base } from '$app/paths';
	import MiniSearch from 'minisearch';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import type { SearchDoc } from '$lib/types';
	import StatusChips from '$lib/components/StatusChips.svelte';

	let query = $state('');
	let kind = $state('all');
	let results = $state<{ title: string; href: string; kind: string; coverage: string }[]>([]);
	let ready = $state(false);
	let error = $state('');
	let engine = $state<MiniSearch<SearchDoc> | null>(null);

	function tokenize(text: string): string[] {
		return (text.toLowerCase().match(/[v]?\d+(?:\.\d+)+|[a-z0-9]+/g) ?? []).filter(Boolean);
	}

	$effect(() => {
		const urlQ = page.url.searchParams.get('q');
		if (urlQ != null) query = urlQ;
	});

	onMount(async () => {
		const urls = [`${base}/generated/search.json`.replace(/\/{2,}/g, '/'), '/generated/search.json'];
		try {
			let docs: SearchDoc[] | null = null;
			let lastError = 'search index missing';
			for (const url of urls) {
				try {
					const response = await fetch(url);
					if (!response.ok) {
						lastError = `search index ${response.status}`;
						continue;
					}
					docs = (await response.json()) as SearchDoc[];
					break;
				} catch (err) {
					lastError = err instanceof Error ? err.message : 'search failed';
				}
			}
			if (!docs) throw new Error(lastError);
			const search = new MiniSearch<SearchDoc>({
				fields: ['title', 'text', 'id'],
				storeFields: ['title', 'href', 'kind', 'coverage'],
				idField: 'id',
				tokenize,
				searchOptions: { prefix: true, fuzzy: 0.15, combineWith: 'AND', tokenize }
			});
			search.addAll(docs);
			engine = search;
			ready = true;
		} catch (err) {
			error = err instanceof Error ? err.message : 'search failed';
		}
	});

	$effect(() => {
		const current = engine;
		if (!current || !ready) {
			results = [];
			return;
		}
		if (!query.trim()) {
			results = [];
			return;
		}
		results = current
			.search(query, { prefix: true, fuzzy: 0.15, combineWith: 'AND' })
			.filter((hit) => kind === 'all' || hit.kind === kind)
			.slice(0, 50)
			.map((hit) => ({
				title: String(hit.title ?? ''),
				href: String(hit.href ?? ''),
				kind: String(hit.kind ?? ''),
				coverage: String(hit.coverage ?? '')
			}));
	});
</script>

<svelte:head>
	<title>Search — asvs-origins</title>
</svelte:head>

<h1>Search</h1>
<p class="lede">
	Client-side search over requirement text, old IDs, origin notes, issue titles, and triage.
</p>
{#if error}
	<p class="banner warn">{error}. Rebuild indexes so <code>web/static/generated/search.json</code> exists.</p>
{:else if !ready}
	<p class="meta">Loading index…</p>
{/if}

<div class="filter-row">
	<input type="search" placeholder="SSRF, V5.2.6, JWT, elarlang…" bind:value={query} />
	<select bind:value={kind}>
		<option value="all">All kinds</option>
		<option value="requirement">Requirements</option>
		<option value="issue">Issues</option>
	</select>
</div>
<p class="meta">{results.length} hits.</p>

<ul class="list">
	{#each results as hit}
		<li>
			<a href="{base}{hit.href}">{hit.title}</a>
			<StatusChips coverage={hit.coverage} />
			<span class="meta"> · {hit.kind}</span>
		</li>
	{/each}
</ul>
