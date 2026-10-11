<script lang="ts">
	import { base } from '$app/paths';
	let { data } = $props();
	const person = $derived(data.person);
</script>

<svelte:head>
	<title>{person.login} — asvs-origins</title>
</svelte:head>

<p class="kicker">People</p>
<h1>{person.login}</h1>
<p class="meta">
	GitHub logins only.
	<a href="https://github.com/{person.login}" rel="noreferrer">github.com/{person.login}</a>
</p>
<p>
	Authored {person.authored_issues.length} issues, participated in {person.participated_issues.length},
	named in {person.claim_mentions} claims, reviewed {person.reviewed_artifacts} artifacts.
</p>

{#if person.requirement_ids.length}
	<h2>Requirements</h2>
	<ul class="list">
		{#each person.requirement_ids as id}
			<li><a href="{base}/requirements/{id}">{id}</a></li>
		{/each}
	</ul>
{/if}

{#if person.authored_issues.length}
	<h2>Issues opened</h2>
	<ul class="list">
		{#each person.authored_issues as number}
			<li><a href="{base}/issues/{number}">#{number}</a></li>
		{/each}
	</ul>
{/if}

{#if person.participated_issues.length}
	<h2>Issues participated</h2>
	<ul class="list">
		{#each person.participated_issues.slice(0, 80) as number}
			<li><a href="{base}/issues/{number}">#{number}</a></li>
		{/each}
	</ul>
{/if}
