import { error } from '@sveltejs/kit';
import { issueExists, loadIssue, loadSourceThread } from '$lib/server/corpus';

export const prerender = false;

export function load({ params }) {
	if (!issueExists(params.number)) error(404, `No issue ${params.number}`);
	const record = loadIssue(params.number);
	const thread = loadSourceThread(Number(params.number));
	return {
		kind: 'issue' as const,
		id: params.number,
		record,
		threads: thread ? [thread] : []
	};
}
