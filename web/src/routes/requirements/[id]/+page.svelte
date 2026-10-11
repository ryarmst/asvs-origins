<script lang="ts">
	import { base } from '$app/paths';
	import ClaimList from '$lib/components/ClaimList.svelte';
	import ProvenanceBadge from '$lib/components/ProvenanceBadge.svelte';
	import StatusChips from '$lib/components/StatusChips.svelte';
	import SummaryBlock from '$lib/components/SummaryBlock.svelte';
	import TextDiff from '$lib/components/TextDiff.svelte';
	import Timeline from '$lib/components/Timeline.svelte';
	import { alternateSummary, isPublic, isUnreviewedAi, pickSummary } from '$lib/provenance';
	import { githubCorrectionUrl, proseHtml } from '$lib/text';
	import { page } from '$app/state';

	let { data } = $props();
	const record = $derived(data.record);
	const origin = $derived(pickSummary(record.summaries.filter((item) => isPublic(item.provenance)), 'origin'));
	const alt = $derived(alternateSummary(record.summaries, origin, 'origin'));
	const evolution = $derived(
		pickSummary(record.summaries.filter((item) => isPublic(item.provenance)), 'evolution')
	);
	const predecessor = $derived(record.lineage.predecessors[0]);
	const primaryMentions = $derived(data.mentions.filter((item) => item.relevance !== 'mentioned'));
	const tailMentions = $derived(data.mentions.filter((item) => item.relevance === 'mentioned'));
	const suggest = $derived(githubCorrectionUrl(record.current.id, page.url.pathname));
	const enrichment = $derived(
		origin
			? origin.provenance.origin === 'human'
				? 'human'
				: origin.provenance.origin === 'llm_reviewed'
					? 'ai_reviewed'
					: origin.provenance.origin === 'llm'
						? 'ai_draft'
						: 'extracted'
			: 'none'
	);
</script>

<svelte:head>
	<title>{record.current.id} — asvs-origins</title>
</svelte:head>

<div class="page-head">
	<div>
		<p class="kicker">
			<a href="{base}/chapters/{record.current.chapter_id}">{record.current.chapter_id} {record.current.chapter_name}</a>
			· {record.current.section_id} {record.current.section_name}
		</p>
		<h1>{record.current.id}</h1>
		<StatusChips
			coverage={record.status.coverage}
			enrichment={enrichment}
			blocked={record.status.blocked_reason}
		/>
	</div>
	<div class="actions">
		<a class="btn secondary" href="{base}/r/{record.uid}">Permalink</a>
		{#if page.data.editMode}
			<a class="btn" href="{base}/edit/requirements/{record.current.id}">Enrich from sources</a>
		{/if}
	</div>
</div>

<p class="meta">
	Level {record.current.level ?? '—'} · uid <code>{record.uid}</code>
	· <a href={suggest}>Suggest a correction</a>
</p>
<p class="req-text">{record.current.text}</p>

{#if record.master.differs_from_release}
	<div class="banner warn">
		Master branch text differs from the {record.current.release} release.
		{#if record.master.text}<div>{@html proseHtml(record.master.text)}</div>{/if}
	</div>
{/if}

{#if record.status.blocked_reason}
	<div class="banner warn">{record.status.blocked_reason}</div>
{/if}

{#if origin}
	<h2>Origin</h2>
	<SummaryBlock summary={origin} />
	{#if alt}
		<details class="alt">
			<summary>Other origin note</summary>
			<SummaryBlock summary={alt} />
		</details>
	{/if}
{:else}
	<div class="banner">No origin note yet. Lineage events below are still available.</div>
{/if}

{#if evolution}
	<h2>Evolution</h2>
	<SummaryBlock summary={evolution} />
{/if}

{#if predecessor?.text}
	<h2>4.0.3 predecessor</h2>
	<p class="meta">
		{predecessor.release} {predecessor.id} · {predecessor.relation}
		{#if record.lineage.mapping_entry}
			· mapping {record.lineage.mapping_entry.status}
			{#if !record.lineage.mapping_entry.agrees_with_git}· disagrees with git{/if}
		{/if}
		· <a href="{base}/lineage">full mapping</a>
	</p>
	<TextDiff
		left={predecessor.text}
		right={record.current.text}
		leftLabel="{predecessor.release} {predecessor.id}"
		rightLabel="{record.current.release} {record.current.id}"
	/>
	{#if predecessor.note}<p>{predecessor.note}</p>{/if}
{/if}

<h2>Timeline</h2>
<p class="meta">{record.lineage.events.length} git events. Numbering noise is collapsed.</p>
<Timeline events={record.lineage.events} />

{#if data.keySources.length}
	<h2>Sources</h2>
	<p class="meta">Issue snapshots behind this control. Open one to read the thread, or enrich from them in the editor.</p>
	{#each data.keySources as source}
		<article class="block" class:unreviewed={source.slice && isUnreviewedAi(source.slice.provenance)}>
			<p class="kicker">#{source.rank} {source.role}</p>
			<h3>
				{#if source.kind === 'issue'}
					<a href="{base}/issues/{source.number}">#{source.number}</a>
				{:else}
					PR {source.number}
				{/if}
				{source.title}
			</h3>
			{#if source.slice}
				<ProvenanceBadge provenance={source.slice.provenance} />
				<p>{source.slice.body}</p>
			{:else}
				<p class="meta">No per-requirement slice on this issue yet.</p>
			{/if}
			{#if page.data.editMode && source.kind === 'issue'}
				<p><a href="{base}/edit/issues/{source.number}">Open source in editor</a></p>
			{/if}
		</article>
	{/each}
{/if}

<ClaimList claims={record.decisions} title="Decisions" />
<ClaimList claims={record.open_questions} title="Open questions" />
<ClaimList claims={record.terminology} title="Terminology" />

{#if record.related_requirements.length}
	<h2>Related requirements</h2>
	<ul class="list">
		{#each record.related_requirements as related}
			<li>
				<a href="{base}/requirements/{related.id}">{related.id}</a>
				· {related.relation}
				{#if related.note} — {related.note}{/if}
			</li>
		{/each}
	</ul>
{/if}

{#if primaryMentions.length}
	<h2>Discussed in</h2>
	<ul class="list">
		{#each primaryMentions as item}
			<li>
				<a href="{base}/issues/{item.issue}">#{item.issue}</a>
				· {item.relevance} — {item.body}
			</li>
		{/each}
	</ul>
{/if}

{#if tailMentions.length}
	<details>
		<summary>All mentions ({tailMentions.length})</summary>
		<ul class="list">
			{#each tailMentions as item}
				<li><a href="{base}/issues/{item.issue}">#{item.issue}</a> — {item.body}</li>
			{/each}
		</ul>
	</details>
{/if}
