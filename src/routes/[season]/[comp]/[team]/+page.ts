import { error } from '@sveltejs/kit';
import { base } from '$app/paths';
import { teamToSlug } from '$lib/slug';
import { SEASONS, isSeason } from '$lib/seasons';
import { COMPS, isComp } from '$lib/comps';
import type {
	Standings,
	LeagueComparison,
	TeamLineupNRtg,
	TeamLineups,
	TeamMatches,
	TeamPlayers,
	TeamPlayerShots,
	TeamPossessions,
	TeamShots
} from '$lib/types';
import type { EntryGenerator, PageLoad } from './$types';

async function loadJson<T>(fetchFn: typeof fetch, path: string): Promise<T | null> {
	const res = await fetchFn(path);
	if (!res.ok) return null;
	return res.json();
}

export const load: PageLoad = async ({ params, fetch }) => {
	if (!isSeason(params.season)) {
		throw error(404, `Ismeretlen szezon: ${params.season}`);
	}
	if (!isComp(params.comp)) {
		throw error(404, `Ismeretlen bajnokság: ${params.comp}`);
	}
	const comp = params.comp;
	const dataBase = `${base}/data/${params.season}`;
	const standings = await loadJson<Standings>(fetch, `${dataBase}/standings/${comp}.json`);
	if (!standings) {
		throw error(404, `Hiányzó standings a(z) ${params.season}/${comp} alatt`);
	}
	const team = standings.teams.find((t) => teamToSlug(t.team) === params.team);
	if (!team) {
		throw error(404, `Ismeretlen csapat: ${params.team}`);
	}
	const matches = await loadJson<TeamMatches>(
		fetch,
		`${dataBase}/team-matches/${comp}/${params.team}.json`
	);
	const shots = await loadJson<TeamShots>(
		fetch,
		`${dataBase}/team-shots/${comp}/${params.team}.json`
	);
	const players = await loadJson<TeamPlayers>(
		fetch,
		`${dataBase}/team-players/${comp}/${params.team}.json`
	);
	const playerShots = await loadJson<TeamPlayerShots>(
		fetch,
		`${dataBase}/team-player-shots/${comp}/${params.team}.json`
	);
	const lineups = await loadJson<TeamLineups>(
		fetch,
		`${dataBase}/team-lineups/${comp}/${params.team}.json`
	);
	const possessions = await loadJson<TeamPossessions>(
		fetch,
		`${dataBase}/team-possessions/${comp}/${params.team}.json`
	);
	const lineupNRtg = await loadJson<TeamLineupNRtg>(
		fetch,
		`${dataBase}/team-lineup-nrtg/${comp}/${params.team}.json`
	);
	const leagueComparison = await loadJson<LeagueComparison>(
		fetch,
		`${dataBase}/league-comparison/${comp}.json`
	);
	return {
		season: params.season,
		comp,
		team,
		standings,
		matches,
		shots,
		players,
		playerShots,
		lineups,
		possessions,
		lineupNRtg,
		leagueComparison
	};
};

export const entries: EntryGenerator = async () => {
	const { readFile } = await import('node:fs/promises');
	const out: Array<{ season: string; comp: string; team: string }> = [];
	for (const season of SEASONS) {
		for (const comp of COMPS) {
			const path = `${process.cwd()}/static/data/${season.id}/standings/${comp.id}.json`;
			try {
				const raw = await readFile(path, 'utf-8');
				const standings: Standings = JSON.parse(raw);
				for (const t of standings.teams) {
					out.push({ season: season.id, comp: comp.id, team: teamToSlug(t.team) });
				}
			} catch {
				// no data for this (season, comp) — skip
			}
		}
	}
	return out;
};
