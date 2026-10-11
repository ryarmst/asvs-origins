import { coverage, requirementCards, chapters } from '$lib/server/corpus';

export function load() {
	const report = coverage();
	const reqs = requirementCards();
	const authored = reqs.filter((item) => item.coverage === 'authored');
	const drafted = reqs.filter((item) => item.coverage === 'drafted');
	return {
		coverage: report,
		chapters: chapters(),
		authored,
		drafted
	};
}
