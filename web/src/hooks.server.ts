import { error, type Handle } from '@sveltejs/kit';

function editEnabled(): boolean {
	return process.env.DEV_EDIT === '1' || process.env.PUBLIC_DEV_EDIT === 'true';
}

export const handle: Handle = async ({ event, resolve }) => {
	event.locals.editMode = editEnabled();
	const path = event.url.pathname;
	const gated = path.startsWith('/edit') || path.startsWith('/api');
	if (gated && !event.locals.editMode) {
		error(404, 'Not found');
	}
	return resolve(event);
};
