import { redirect } from '@sveltejs/kit';
import { uidToId } from '$lib/server/corpus';

export function entries() {
	return Object.keys(uidToId()).map((uid) => ({ uid }));
}

export function load({ params }) {
	const id = uidToId()[params.uid];
	if (!id) {
		redirect(308, '/');
	}
	redirect(308, `/requirements/${id}`);
}
