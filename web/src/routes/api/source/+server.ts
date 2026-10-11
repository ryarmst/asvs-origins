import { error, json } from '@sveltejs/kit';
import { loadSourceThread } from '$lib/server/corpus';

export const prerender = false;

export function GET({ url }) {
	const number = Number(url.searchParams.get('issue'));
	if (!Number.isFinite(number) || number < 1) error(400, 'issue required');
	const thread = loadSourceThread(number);
	if (!thread) error(404, `no snapshot for issue ${number}`);
	return json(thread);
}
