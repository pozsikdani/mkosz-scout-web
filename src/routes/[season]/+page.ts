import { error } from '@sveltejs/kit';
import { base } from '$app/paths';
import { SEASONS, isSeason, seasonBy } from '$lib/seasons';
import type { Standings } from '$lib/types';
import type { EntryGenerator, PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	if (!isSeason(params.season)) {
		throw error(404, `Ismeretlen szezon: ${params.season}`);
	}
	const res = await fetch(`${base}/data/${params.season}/standings/hun2a.json`);
	if (!res.ok) {
		throw error(404, `Nincs standings adat a(z) ${params.season} szezonhoz`);
	}
	const standings: Standings = await res.json();
	return { season: seasonBy(params.season)!, standings };
};

export const entries: EntryGenerator = async () => {
	return SEASONS.map((s) => ({ season: s.id }));
};
