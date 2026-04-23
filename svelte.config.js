import adapter from '@sveltejs/adapter-static';

const dev = process.env.NODE_ENV !== 'production';
// If BASE_PATH env is set (eg. CI for GH Pages subpath), use it. Empty for custom domain / dev.
const base = process.env.BASE_PATH ?? '';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	compilerOptions: {
		runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
	},
	kit: {
		adapter: adapter({
			fallback: '404.html'
		}),
		paths: {
			base: dev ? '' : base
		},
		prerender: {
			handleHttpError: 'warn'
		}
	}
};

export default config;
