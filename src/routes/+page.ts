import { base } from '$app/paths';
import type { Standings } from '$lib/types';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const res = await fetch(`${base}/data/standings/hun2a.json`);
	const standings: Standings = await res.json();
	return { standings };
};
