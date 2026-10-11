<script lang="ts">
	import { base } from '$app/paths';
	let { data } = $props();
	let query = $state('');
	let showDeleted = $state(true);
	const filtered = $derived(
		data.rows.filter((row) => {
			if (!showDeleted && row.deleted) return false;
			if (!query.trim()) return true;
			const q = query.toLowerCase();
			return (
				row.from_id.toLowerCase().includes(q) ||
				row.raw.toLowerCase().includes(q) ||
				row.to_ids.some((id) => id.toLowerCase().includes(q)) ||
				(row.from_text ?? '').toLowerCase().includes(q)
			);
		})
	);
</script>

<svelte:head>
	<title>Mapping 4.0.3 → 5.0.0 — asvs-origins</title>
</svelte:head>

<h1>4.0.3 → 5.0.0</h1>
<p class="lede">
	Same orientation as
	<a href="https://asvs.dev/mapping_v4.0.3_to_v5.0.0.html">asvs.dev</a>: every v4 control, including
	deletions. Old IDs also resolve at <code>/legacy/v4.0.3/&lt;id&gt;</code>.
</p>

<div class="grid">
	<div class="stat">
		<b>{data.report.counts.v4_entries}</b>
		v4 mapping rows
	</div>
	<div class="stat">
		<b>{data.report.counts.v4_deleted}</b>
		deleted in 5.0.0
	</div>
	<div class="stat">
		<b>{data.report.counts.yaml_mismatches}</b>
		YAML asymmetries
	</div>
	<div class="stat">
		<b>{data.report.counts.stale_slots ?? data.report.counts.git_disagreements}</b>
		stale mapping slots
	</div>
</div>

{#if (data.report.stale_slots ?? data.report.git_disagreements).length}
	<h2>Git wins over the published mapping</h2>
	<p class="meta">
		The two official YAML files agree with each other and with
		<a href="https://asvs.dev/mapping_v4.0.3_to_v5.0.0.html">asvs.dev</a>. These slots reused an ID
		after the old text was replaced. The corpus follows git. See
		<a href="https://github.com/OWASP/ASVS/pull/3373">OWASP/ASVS#3373</a> for V13.2.4.
	</p>
	<ul class="list">
		{#each data.report.stale_slots ?? data.report.git_disagreements as item}
			<li>
				<a href="{base}/requirements/{item.id}">{item.id}</a>
				<span class="meta"> · {item.raw}</span>
				{#if item.note}<div>{item.note}</div>{/if}
			</li>
		{/each}
	</ul>
{/if}

{#if data.report.git_disagreements.length}
	<details>
		<summary>
			{data.report.counts.git_disagreements} records where mapping predecessor text or IDs diverge from git
		</summary>
		<ul class="list">
			{#each data.report.git_disagreements as item}
				<li>
					<a href="{base}/requirements/{item.id}">{item.id}</a>
					<span class="meta"> · {item.kind} · {item.raw}</span>
				</li>
			{/each}
		</ul>
	</details>
{/if}

{#if data.report.yaml_mismatches.length}
	<h2>Official YAML mismatches</h2>
	<ul class="list">
		{#each data.report.yaml_mismatches as item}
			<li>
				<span class="meta">{item.kind}</span>
				{item.detail}
			</li>
		{/each}
	</ul>
{/if}

<div class="filter-row">
	<input type="search" placeholder="V5.2.6, DELETED, 13.2.4…" bind:value={query} />
	<label class="meta">
		<input type="checkbox" bind:checked={showDeleted} />
		Show deleted v4 controls
	</label>
</div>
<p class="meta">{filtered.length} rows.</p>

<ul class="list">
	{#each filtered as row}
		<li>
			<strong>{row.from_id}</strong>
			{#if row.deleted}
				<span class="chip chip-muted">deleted</span>
			{/if}
			{#if row.to_ids.length}
				→
				{#each row.to_ids as id, i}
					{i ? ', ' : ''}
					<a href="{base}/requirements/{id}">{id}</a>
				{/each}
			{/if}
			<div class="meta">{row.raw}</div>
			{#if row.from_text}<div>{row.from_text}</div>{/if}
		</li>
	{/each}
</ul>
