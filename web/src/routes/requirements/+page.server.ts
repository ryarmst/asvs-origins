import { chapters, requirementCards } from '$lib/server/corpus';

export function load() {
	return { chapters: chapters(), requirements: requirementCards() };
}
