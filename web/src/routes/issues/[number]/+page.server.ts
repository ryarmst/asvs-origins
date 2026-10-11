import { error } from '@sveltejs/kit';
import { issueCards, issueExists, loadIssue, uidToId } from '$lib/server/corpus';

export function entries() {
	return issueCards().map((item) => ({ number: String(item.number) }));
}

export function load({ params }) {
	if (!issueExists(params.number)) {
		error(404, `No issue ${params.number}`);
	}
	const record = loadIssue(params.number);
	const map = uidToId();
	const slices = record.requirement_summaries.map((slice) => ({
		...slice,
		requirement_id: map[slice.requirement_uid] ?? slice.requirement_id_at_time
	}));
	return { record, slices };
}
