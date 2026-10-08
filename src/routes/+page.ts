import { base } from '$app/paths';
import { SEASONS } from '$lib/seasons';
import type { Standings } from '$lib/types';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const summaries = await Promise.all(
		SEASONS.map(async (s) => {
			try {
				const res = await fetch(`${base}/data/${s.id}/standings/hun2a.json`);
				if (!res.ok) return { season: s, teamCount: 0, scrapedAt: null as string | null };
				const standings: Standings = await res.json();
				return { season: s, teamCount: standings.teams.length, scrapedAt: standings.scraped_at };
			} catch {
				return { season: s, teamCount: 0, scrapedAt: null as string | null };
			}
		})
	);
	return { summaries };
};
