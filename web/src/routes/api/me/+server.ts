import { json } from '@sveltejs/kit';

export const prerender = false;

export function GET() {
	return json({
		github: process.env.ASVS_ORIGINS_GITHUB || process.env.ASVS_ORIGINS_REVIEWER || '',
		name: process.env.ASVS_ORIGINS_NAME || process.env.ASVS_ORIGINS_GITHUB || ''
	});
}
