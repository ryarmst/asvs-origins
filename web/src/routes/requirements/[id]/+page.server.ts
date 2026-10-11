import { error } from '@sveltejs/kit';
import {
	issueExists,
	loadIssue,
	loadRequirement,
	mentions,
	requirementCards,
	requirementExists
} from '$lib/server/corpus';
import { isPublic } from '$lib/provenance';
import type { IssueSlice } from '$lib/types';

export function entries() {
	return requirementCards().map((item) => ({ id: item.id }));
}

export function load({ params }) {
	if (!requirementExists(params.id)) {
		error(404, `No requirement ${params.id}`);
	}
	const record = loadRequirement(params.id);
	const mentionList = (mentions()[record.uid] ?? []).filter((item) => item.relevance);
	const keySources = record.key_sources.map((source) => {
		const issue = source.kind === 'issue' && issueExists(source.number) ? loadIssue(source.number) : null;
		const slice: IssueSlice | null =
			issue?.requirement_summaries.find((item) => item.requirement_uid === record.uid && isPublic(item.provenance)) ??
			null;
		return { ...source, title: issue?.title ?? `Issue ${source.number}`, slice };
	});
	return { record, mentions: mentionList, keySources };
}
