import { mappingAlignment, mappingV4 } from '$lib/server/corpus';

export function load() {
	return { rows: mappingV4(), report: mappingAlignment() };
}
