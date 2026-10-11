import { redirect } from '@sveltejs/kit';
import { legacyMap, lineagePairs } from '$lib/server/corpus';

export function entries() {
	const seen = new Set<string>();
	const out: { release: string; id: string }[] = [];
	for (const pair of lineagePairs()) {
		if (!pair.from_release || !pair.from_id) continue;
		const release = `v${pair.from_release}`;
		for (const id of [pair.from_id, pair.from_id.replace(/^V/i, '')]) {
			const key = `${release}/${id}`;
			if (seen.has(key)) continue;
			seen.add(key);
			out.push({ release, id });
		}
	}
	return out;
}

export function load({ params }) {
	const release = params.release.replace(/^v/i, '');
	const needle = params.id;
	const table = legacyMap()[release] ?? {};
	const hit = table[needle] ?? table[`V${needle}`] ?? table[needle.replace(/^V/i, '')];
	if (!hit) {
		redirect(308, '/');
	}
	redirect(308, `/requirements/${hit.id}`);
}
