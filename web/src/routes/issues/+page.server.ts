import { issueCards } from '$lib/server/corpus';

export function load() {
	return { issues: issueCards() };
}
