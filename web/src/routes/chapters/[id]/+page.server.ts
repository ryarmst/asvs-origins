import { error } from '@sveltejs/kit';
import { chapters, issueCards, requirementCards } from '$lib/server/corpus';

export function entries() {
	return chapters().map((item) => ({ id: item.id }));
}

export function load({ params }) {
	const chapter = chapters().find((item) => item.id === params.id);
	if (!chapter) error(404, `No chapter ${params.id}`);
	const reqs = requirementCards().filter((item) => item.chapter_id === params.id);
	const issues = issueCards()
		.filter((item) => item.chapter_ids.includes(params.id))
		.sort((a, b) => b.requirement_ids.length - a.requirement_ids.length);
	return { chapter, chapters: chapters(), requirements: reqs, issues };
}
