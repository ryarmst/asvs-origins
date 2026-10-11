<script lang="ts">
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import favicon from '$lib/assets/favicon.svg';
	import SearchBox from '$lib/components/SearchBox.svelte';
	import '../app.css';

	let { children, data } = $props();

	function current(href: string) {
		return page.url.pathname === href || page.url.pathname.startsWith(href + '/');
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>asvs-origins</title>
</svelte:head>

<header class="site">
	<div class="wrap">
		<a class="brand" href="{base}/">asvs-origins</a>
		<nav class="site">
			<a href="{base}/requirements" aria-current={current('/requirements') ? 'page' : undefined}>Requirements</a>
			<a href="{base}/issues" aria-current={current('/issues') ? 'page' : undefined}>Issues</a>
			<a href="{base}/chapters" aria-current={current('/chapters') ? 'page' : undefined}>Chapters</a>
			<a href="{base}/lineage" aria-current={current('/lineage') ? 'page' : undefined}>Mapping</a>
		</nav>
		<div class="tools">
			<SearchBox />
		</div>
	</div>
</header>

<main>
	<div class="wrap">
		{@render children()}
	</div>
</main>

<footer class="site">
	<div class="wrap">
		Companion to the OWASP ASVS, not a replacement for
		<a href="https://asvs.dev">asvs.dev</a> or the standard. Corpus
		<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>. Code Apache-2.0.
		{#if data.editMode}
			<span> · local editor on</span>
		{/if}
	</div>
</footer>
