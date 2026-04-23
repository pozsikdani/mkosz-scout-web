import type { Standings } from '$lib/types';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const res = await fetch('/data/standings/hun2a.json');
	const standings: Standings = await res.json();
	return { standings };
};
