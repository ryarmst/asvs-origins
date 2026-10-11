import { error } from '@sveltejs/kit';
import { loadRequirement, loadSourceThread, requirementExists } from '$lib/server/corpus';

export const prerender = false;

export function load({ params }) {
	if (!requirementExists(params.id)) error(404, `No requirement ${params.id}`);
	const record = loadRequirement(params.id);
	const threads = record.key_sources
		.filter((source) => source.kind === 'issue')
		.map((source) => loadSourceThread(source.number))
		.filter((item) => item !== null);
	return { kind: 'requirement' as const, id: params.id, record, threads };
}
