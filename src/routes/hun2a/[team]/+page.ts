import { error } from '@sveltejs/kit';
import { base } from '$app/paths';
import { teamToSlug } from '$lib/slug';
import type { Standings, TeamMatches, TeamShots } from '$lib/types';
import type { EntryGenerator, PageLoad } from './$types';

async function loadStandings(fetchFn: typeof fetch): Promise<Standings> {
	const res = await fetchFn(`${base}/data/standings/hun2a.json`);
	return res.json();
}

async function loadJson<T>(fetchFn: typeof fetch, path: string): Promise<T | null> {
	const res = await fetchFn(path);
	if (!res.ok) return null;
	return res.json();
}

export const load: PageLoad = async ({ params, fetch }) => {
	const standings = await loadStandings(fetch);
	const team = standings.teams.find((t) => teamToSlug(t.team) === params.team);
	if (!team) {
		throw error(404, `Ismeretlen csapat: ${params.team}`);
	}
	const matches = await loadJson<TeamMatches>(fetch, `${base}/data/team-matches/${params.team}.json`);
	const shots = await loadJson<TeamShots>(fetch, `${base}/data/team-shots/${params.team}.json`);
	return { team, standings, matches, shots };
};

export const entries: EntryGenerator = async () => {
	const path = `${process.cwd()}/static/data/standings/hun2a.json`;
	const { readFile } = await import('node:fs/promises');
	const raw = await readFile(path, 'utf-8');
	const standings: Standings = JSON.parse(raw);
	return standings.teams.map((t) => ({ team: teamToSlug(t.team) }));
};
