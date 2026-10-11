<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';

	let q = $state('');

	$effect(() => {
		if (page.url.pathname.endsWith('/search')) {
			q = page.url.searchParams.get('q') ?? '';
		}
	});
</script>

<form action="{base}/search" method="GET">
	<input type="search" name="q" placeholder="Search requirements, issues, IDs…" bind:value={q} />
</form>
