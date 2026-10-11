import { spawn } from 'node:child_process';
import { error, json } from '@sveltejs/kit';
import { pythonBin, REPO_ROOT } from '$lib/server/corpus';

export const prerender = false;

function runReview(payload: unknown): Promise<Record<string, unknown>> {
	return new Promise((resolve, reject) => {
		const child = spawn(pythonBin(), ['-m', 'pipeline.review', '--json'], {
			cwd: REPO_ROOT,
			env: process.env
		});
		let out = '';
		let err = '';
		child.stdout.on('data', (chunk: Buffer) => {
			out += String(chunk);
		});
		child.stderr.on('data', (chunk: Buffer) => {
			err += String(chunk);
		});
		child.on('error', reject);
		child.on('close', () => {
			try {
				resolve(JSON.parse(out));
			} catch {
				reject(new Error(err || out || 'review process failed'));
			}
		});
		child.stdin.write(JSON.stringify(payload));
		child.stdin.end();
	});
}

export async function POST({ request, locals }) {
	if (!locals.editMode) error(404, 'Not found');
	const body = await request.json();
	try {
		const result = await runReview(body);
		if (!result.ok) {
			return json(result, { status: 400 });
		}
		return json(result);
	} catch (err) {
		error(500, err instanceof Error ? err.message : 'review failed');
	}
}
