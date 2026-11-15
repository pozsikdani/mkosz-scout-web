import { error } from '@sveltejs/kit';
import { base } from '$app/paths';
import { SEASONS, isSeason, seasonBy } from '$lib/seasons';
import { COMPS, isComp, compBy } from '$lib/comps';
import type { TeamPlayers } from '$lib/types';
import type { EntryGenerator, PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	if (!isSeason(params.season)) throw error(404, `Ismeretlen szezon: ${params.season}`);
	if (!isComp(params.comp)) throw error(404, `Ismeretlen bajnokság: ${params.comp}`);
	const res = await fetch(`${base}/data/${params.season}/league-players/${params.comp}.json`);
	if (!res.ok) throw error(404, `Nincs játékos-ranglista a(z) ${params.season}/${params.comp} alatt`);
	const players = (await res.json()) as TeamPlayers;
	return { season: seasonBy(params.season)!, comp: compBy(params.comp)!, players };
};

// Csak ott generálunk oldalt, ahol a liga-szintű lista létezik (archívban nincs)
export const entries: EntryGenerator = async () => {
	const { readFile } = await import('node:fs/promises');
	const out: Array<{ season: string; comp: string }> = [];
	for (const season of SEASONS) {
		for (const comp of COMPS) {
			try {
				await readFile(`${process.cwd()}/static/data/${season.id}/league-players/${comp.id}.json`, 'utf-8');
				out.push({ season: season.id, comp: comp.id });
			} catch {
				// nincs liga-lista ehhez a (szezon, bajnokság) párhoz
			}
		}
	}
	return out;
};
