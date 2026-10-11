import { error } from '@sveltejs/kit';
import { people } from '$lib/server/corpus';

export function entries() {
	return Object.values(people())
		.filter(
			(person) =>
				person.authored_issues.length > 0 ||
				person.requirement_ids.length > 0 ||
				person.reviewed_artifacts > 0
		)
		.filter((person) => /^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/.test(person.login))
		.map((person) => ({ login: person.login }));
}

export function load({ params }) {
	const person = people()[params.login];
	if (!person) error(404, `No recorded footprint for ${params.login}`);
	return { person };
}
