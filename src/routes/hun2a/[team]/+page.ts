import { error } from '@sveltejs/kit';
import { teamToSlug } from '$lib/slug';
import type { Standings, TeamMatches } from '$lib/types';
import type { EntryGenerator, PageLoad } from './$types';

async function loadStandings(fetchFn: typeof fetch): Promise<Standings> {
	const res = await fetchFn('/data/standings/hun2a.json');
	return res.json();
}

async function loadMatches(fetchFn: typeof fetch, slug: string): Promise<TeamMatches | null> {
	const res = await fetchFn(`/data/team-matches/${slug}.json`);
	if (!res.ok) return null;
	return res.json();
}

export const load: PageLoad = async ({ params, fetch }) => {
	const standings = await loadStandings(fetch);
	const team = standings.teams.find((t) => teamToSlug(t.team) === params.team);
	if (!team) {
		throw error(404, `Ismeretlen csapat: ${params.team}`);
	}
	const matches = await loadMatches(fetch, params.team);
	return { team, standings, matches };
};

export const entries: EntryGenerator = async () => {
	const path = `${process.cwd()}/static/data/standings/hun2a.json`;
	const { readFile } = await import('node:fs/promises');
	const raw = await readFile(path, 'utf-8');
	const standings: Standings = JSON.parse(raw);
	return standings.teams.map((t) => ({ team: teamToSlug(t.team) }));
};
