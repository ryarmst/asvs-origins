import { error, json } from '@sveltejs/kit';
import { issueExists, loadIssue, loadRequirement, requirementExists } from '$lib/server/corpus';

export const prerender = false;

export function GET({ url }) {
	const kind = url.searchParams.get('kind');
	const id = url.searchParams.get('id');
	if (!kind || !id) error(400, 'kind and id required');
	if (kind === 'requirement') {
		if (!requirementExists(id)) error(404, `no requirement ${id}`);
		return json(loadRequirement(id));
	}
	if (kind === 'issue') {
		if (!issueExists(id)) error(404, `no issue ${id}`);
		return json(loadIssue(id));
	}
	error(400, 'unsupported kind');
}
