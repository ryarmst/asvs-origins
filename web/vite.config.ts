import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import path from 'node:path';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter({
				pages: 'build',
				assets: 'build',
				strict: false
			}),
			paths: {
				relative: true,
				base: (process.env.BASE_PATH || '') as '' | `/${string}`
			},
			prerender: {
				entries: ['*'],
				handleHttpError: 'warn',
				handleMissingId: 'warn'
			}
		})
	],
	server: {
		host: '127.0.0.1',
		fs: {
			allow: [path.resolve('..')]
		}
	}
});
