import { error } from '@sveltejs/kit';
import { base } from '$app/paths';
import { teamToSlug } from '$lib/slug';
import { SEASONS, isSeason } from '$lib/seasons';
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
	const dataBase = `${base}/data/${params.season}`;
	const standings = await loadJson<Standings>(fetch, `${dataBase}/standings/hun2a.json`);
	if (!standings) {
		throw error(404, `Hiányzó standings a(z) ${params.season} szezonhoz`);
	}
	const team = standings.teams.find((t) => teamToSlug(t.team) === params.team);
	if (!team) {
		throw error(404, `Ismeretlen csapat: ${params.team}`);
	}
	const matches = await loadJson<TeamMatches>(fetch, `${dataBase}/team-matches/${params.team}.json`);
	const shots = await loadJson<TeamShots>(fetch, `${dataBase}/team-shots/${params.team}.json`);
	const players = await loadJson<TeamPlayers>(fetch, `${dataBase}/team-players/${params.team}.json`);
	const playerShots = await loadJson<TeamPlayerShots>(
		fetch,
		`${dataBase}/team-player-shots/${params.team}.json`
	);
	const lineups = await loadJson<TeamLineups>(fetch, `${dataBase}/team-lineups/${params.team}.json`);
	const possessions = await loadJson<TeamPossessions>(
		fetch,
		`${dataBase}/team-possessions/${params.team}.json`
	);
	const lineupNRtg = await loadJson<TeamLineupNRtg>(
		fetch,
		`${dataBase}/team-lineup-nrtg/${params.team}.json`
	);
	const leagueComparison = await loadJson<LeagueComparison>(
		fetch,
		`${dataBase}/league-comparison/hun2a.json`
	);
	return {
		season: params.season,
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
	const out: Array<{ season: string; team: string }> = [];
	for (const season of SEASONS) {
		const path = `${process.cwd()}/static/data/${season.id}/standings/hun2a.json`;
		try {
			const raw = await readFile(path, 'utf-8');
			const standings: Standings = JSON.parse(raw);
			for (const t of standings.teams) {
				out.push({ season: season.id, team: teamToSlug(t.team) });
			}
		} catch {
			// no data for this season — skip
		}
	}
	return out;
};
