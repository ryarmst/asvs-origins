<script lang="ts">
	import { base } from '$app/paths';
	import { listArtifacts, type Artifact } from '$lib/artifacts';
	import { badgeKind, badgeLabel, chipClass } from '$lib/provenance';
	import { proseHtml } from '$lib/text';
	import type { Citation, SourceComment, SourceThread } from '$lib/types';

	let {
		kind,
		id,
		record,
		threads
	}: {
		kind: 'requirement' | 'issue';
		id: string;
		record: Record<string, unknown>;
		threads: SourceThread[];
	} = $props();

	let live = $state<Record<string, unknown> | null>(null);
	const current = $derived(live ?? record);
	const artifacts = $derived(listArtifacts(current));
	const currentReq = $derived(
		kind === 'requirement' ? (current.current as { id?: string; text?: string } | undefined) : undefined
	);
	let selected = $state(0);
	let draft = $state('');
	let note = $state('');
	let message = $state('');
	let busy = $state(false);
	let writeBody = $state('');
	let writeKind = $state('origin');
	$effect(() => {
		writeKind = kind === 'requirement' ? 'origin' : 'overview';
	});
	let extraCitations = $state<Citation[]>([]);
	let sourceOpen = $state(0);

	$effect(() => {
		const item = artifacts[selected];
		draft = item?.preview ?? '';
	});

	function publicHref() {
		return kind === 'requirement' ? `${base}/requirements/${id}` : `${base}/issues/${id}`;
	}

	async function act(action: string, body?: string) {
		const item = artifacts[selected];
		if (!item && action !== 'write') return;
		busy = true;
		message = '';
		try {
			const payload: Record<string, unknown> = {
				kind,
				id,
				action,
				path: action === 'write' ? 'summaries' : item.path,
				note: note || null,
				body: action === 'write' ? writeBody : body,
				summary_kind: action === 'write' ? writeKind : undefined
			};
			if ((action === 'accept' || action === 'write') && extraCitations.length) {
				payload.citations = extraCitations;
			}
			const response = await fetch(`${base}/api/review`, {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify(payload)
			});
			const result = await response.json();
			if (!response.ok || !result.ok) {
				message = result.error || `Save failed (${response.status})`;
				return;
			}
			message = `Saved ${result.path}`;
			const fresh = await fetch(`${base}/api/record?kind=${kind}&id=${id}`);
			const next = await fresh.json();
			live = next;
			writeBody = '';
			note = '';
			if (action === 'write') extraCitations = [];
		} catch (err) {
			message = err instanceof Error ? err.message : 'save failed';
		} finally {
			busy = false;
		}
	}

	function cite(thread: SourceThread, comment: SourceComment | null) {
		const citation: Citation = comment
			? {
					type: 'issue_comment',
					url: comment.url,
					issue: thread.number,
					comment_id: comment.id,
					author: comment.author,
					date: comment.createdAt
				}
			: {
					type: 'issue_body',
					url: thread.url,
					issue: thread.number,
					author: thread.author
				};
		extraCitations = [...extraCitations, citation];
		message = `Citation queued: ${citation.url}`;
	}

	function selectArtifact(index: number) {
		selected = index;
	}

	function artifactKind(item: Artifact): string {
		return item.kind || item.path.split('/')[0];
	}
</script>

<svelte:head>
	<title>Enrich {id} — asvs-origins</title>
</svelte:head>

<div class="edit-hero">
	<p class="kicker">Local editor · writes JSON under data/</p>
	<h1>{kind === 'requirement' ? id : `Issue #${id}`}</h1>
	<p class="meta">
		<a href={publicHref()}>Public view</a>
		· Click a source comment to attach a citation, then save a human note or accept an existing draft.
	</p>
	{#if currentReq?.text}
		<p class="req-text" style="margin-bottom:0">{currentReq.text}</p>
	{/if}
</div>
{#if message}<div class="banner">{message}</div>{/if}

<div class="editor">
	<section>
		<h2>1. Sources</h2>
		<p class="meta">Read the thread. Click a comment to cite it on the note you are writing.</p>
		{#each threads as thread, index}
			<div class="thread">
				<p class="kicker">#{thread.number} {thread.title}</p>
				<div class="actions">
					<button class="btn secondary" type="button" onclick={() => cite(thread, null)}>Cite issue body</button>
					<button class="btn secondary" type="button" onclick={() => (sourceOpen = index)}
						>Focus</button
					>
				</div>
				<button class="comment" type="button" onclick={() => cite(thread, null)}>
					<p class="meta">{thread.author} · issue body</p>
					<div>{@html proseHtml(thread.body)}</div>
				</button>
				{#if sourceOpen === index || threads.length === 1}
					{#each thread.comments as comment}
						<button class="comment" type="button" onclick={() => cite(thread, comment)}>
							<p class="meta">
								{comment.author} · {comment.createdAt}
								{#if comment.url}<a href={comment.url} rel="noreferrer" onclick={(event) => event.stopPropagation()}>GitHub</a>{/if}
							</p>
							<div>{@html proseHtml(comment.body)}</div>
						</button>
					{/each}
				{:else}
					<p class="meta">{thread.comments.length} comments. Focus to expand.</p>
				{/if}
			</div>
		{/each}
		{#if threads.length === 0}
			<p class="meta">No local issue snapshot for this record. You can still write a human note.</p>
		{/if}
	</section>

	<section>
		<h2>2. Existing notes</h2>
		{#if artifacts.length === 0}
			<p class="meta">Nothing drafted yet.</p>
		{/if}
		{#each artifacts as item, index}
			<button
				type="button"
				class="artifact-card"
				class:active={index === selected}
				onclick={() => selectArtifact(index)}
			>
				<span class="chip {chipClass(badgeKind(item.provenance))}">
					{badgeLabel(badgeKind(item.provenance), item.provenance.review.status)}
				</span>
				<span class="chip chip-muted">{artifactKind(item)}</span>
				<span class="chip chip-muted">{item.provenance.review.status.replace('_', ' ')}</span>
				<div class="preview">{item.preview}</div>
			</button>
		{/each}

		{#if artifacts[selected]}
			<h3>Edit selected</h3>
			<textarea bind:value={draft}></textarea>
			<input type="text" placeholder="Review note (optional)" bind:value={note} />
			{#if extraCitations.length}
				<p class="meta">{extraCitations.length} citation(s) will attach on accept.</p>
			{/if}
			<div class="actions">
				<button class="btn" type="button" disabled={busy} onclick={() => act('accept')}>Keep text</button>
				<button class="btn secondary" type="button" disabled={busy} onclick={() => act('accept', draft)}
					>Save edits</button
				>
				<button class="btn secondary" type="button" disabled={busy} onclick={() => act('flag')}>Flag</button>
				<button class="btn danger" type="button" disabled={busy} onclick={() => act('reject')}>Hide</button>
			</div>
		{/if}

		<h2>3. Add a human note</h2>
		<p class="meta">This is the usual next step after reading the sources. It is stored as human-authored.</p>
		<select bind:value={writeKind}>
			{#if kind === 'requirement'}
				<option value="origin">Origin</option>
				<option value="evolution">Evolution</option>
				<option value="interpretation">Interpretation</option>
				<option value="controversy">Controversy</option>
			{:else}
				<option value="overview">Overview</option>
			{/if}
		</select>
		<textarea bind:value={writeBody} placeholder="What the sources show, in your words"></textarea>
		{#if extraCitations.length}
			<p class="meta">{extraCitations.length} citation(s) will attach.</p>
		{/if}
		<div class="actions">
			<button
				class="btn"
				type="button"
				disabled={busy || !writeBody.trim()}
				onclick={() => act('write')}>Save human note</button
			>
		</div>
	</section>
</div>
