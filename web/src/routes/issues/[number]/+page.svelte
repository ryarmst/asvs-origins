<script lang="ts">
	import { base } from '$app/paths';
	import ClaimList from '$lib/components/ClaimList.svelte';
	import ProvenanceBadge from '$lib/components/ProvenanceBadge.svelte';
	import StatusChips from '$lib/components/StatusChips.svelte';
	import SummaryBlock from '$lib/components/SummaryBlock.svelte';
	import { page } from '$app/state';
	import { isPublic, isUnreviewedAi, pickSummary } from '$lib/provenance';

	let { data } = $props();
	const record = $derived(data.record);
	const overview = $derived(
		pickSummary(record.summaries.filter((item) => isPublic(item.provenance)), 'overview')
	);
	const publicSlices = $derived(data.slices.filter((item) => isPublic(item.provenance)));
</script>

<svelte:head>
	<title>#{record.number} — asvs-origins</title>
</svelte:head>

<div class="page-head">
	<div>
		<p class="kicker">Issue · {record.state}</p>
		<h1>#{record.number} {record.title}</h1>
		<StatusChips coverage={record.status.coverage} />
	</div>
	<div class="actions">
		<a class="btn secondary" href={record.url} rel="noreferrer">GitHub</a>
		{#if page.data.editMode}
			<a class="btn" href="{base}/edit/issues/{record.number}">Enrich from sources</a>
		{/if}
	</div>
</div>
<p class="meta">
	Opened {record.created_at} by
	<a href="{base}/people/{record.author}">{record.author}</a>
</p>
{#if record.participants.length}
	<p class="meta">
		Participants:
		{#each record.participants as login, i}
			{i ? ', ' : ''}<a href="{base}/people/{login}">{login}</a>
		{/each}
	</p>
{/if}

{#if record.triage && isPublic(record.triage.provenance)}
	<h2>Triage</h2>
	<article class="block" class:unreviewed={isUnreviewedAi(record.triage.provenance)}>
		<ProvenanceBadge provenance={record.triage.provenance} />
		<p>{record.triage.relevance} · {record.triage.class} · ~{record.triage.estimated_requirement_count} requirements</p>
		<p>{record.triage.reason}</p>
	</article>
{/if}

{#if overview}
	<h2>Overview</h2>
	<SummaryBlock summary={overview} />
{/if}

{#if record.outcome && isPublic(record.outcome.provenance)}
	<h2>Outcome</h2>
	<article class="block" class:unreviewed={isUnreviewedAi(record.outcome.provenance)}>
		<ProvenanceBadge provenance={record.outcome.provenance} />
		<p>{record.outcome.state}</p>
		{#if record.outcome.resulting_changes.length}
			<ul>
				{#each record.outcome.resulting_changes as change}
					<li>{change}</li>
				{/each}
			</ul>
		{/if}
	</article>
{/if}

{#if publicSlices.length}
	<h2>Per-requirement slices</h2>
	{#each publicSlices as slice}
		<article class="block" class:unreviewed={isUnreviewedAi(slice.provenance)}>
			<h3>
				{#if slice.requirement_id}
					<a href="{base}/requirements/{slice.requirement_id}">{slice.requirement_id}</a>
				{:else}
					{slice.requirement_uid}
				{/if}
				<span class="meta">· {slice.relevance} · {slice.outcome}</span>
			</h3>
			<ProvenanceBadge provenance={slice.provenance} />
			<p>{slice.body}</p>
			<ClaimList claims={slice.arguments} title="Arguments" />
			<ClaimList claims={slice.decisions} title="Decisions" />
			<ClaimList claims={slice.terminology} title="Terminology" />
			<ClaimList claims={slice.open_questions} title="Open questions" />
		</article>
	{/each}
{/if}
