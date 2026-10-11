import { error } from '@sveltejs/kit';
import { base } from '$app/paths';
import { SEASONS, isSeason, seasonBy } from '$lib/seasons';
import { COMPS } from '$lib/comps';
import type { Standings } from '$lib/types';
import type { EntryGenerator, PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	if (!isSeason(params.season)) {
		throw error(404, `Ismeretlen szezon: ${params.season}`);
	}
	const summaries = await Promise.all(
		COMPS.map(async (c) => {
			try {
				const res = await fetch(`${base}/data/${params.season}/standings/${c.id}.json`);
				if (!res.ok) {
					return { comp: c, teamCount: 0, scrapedAt: null as string | null };
				}
				const standings: Standings = await res.json();
				return { comp: c, teamCount: standings.teams.length, scrapedAt: standings.scraped_at };
			} catch {
				return { comp: c, teamCount: 0, scrapedAt: null as string | null };
			}
		})
	);
	return { season: seasonBy(params.season)!, summaries };
};

export const entries: EntryGenerator = async () => {
	return SEASONS.map((s) => ({ season: s.id }));
};
