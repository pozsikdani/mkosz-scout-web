import { error } from '@sveltejs/kit';
import { base } from '$app/paths';
import { SEASONS, isSeason, seasonBy } from '$lib/seasons';
import { COMPS, isComp, compBy } from '$lib/comps';
import type { Standings } from '$lib/types';
import type { EntryGenerator, PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	if (!isSeason(params.season)) {
		throw error(404, `Ismeretlen szezon: ${params.season}`);
	}
	if (!isComp(params.comp)) {
		throw error(404, `Ismeretlen bajnokság: ${params.comp}`);
	}
	const res = await fetch(`${base}/data/${params.season}/standings/${params.comp}.json`);
	if (!res.ok) {
		throw error(404, `Nincs standings adat a(z) ${params.season}/${params.comp} alatt`);
	}
	const standings: Standings = await res.json();
	return {
		season: seasonBy(params.season)!,
		comp: compBy(params.comp)!,
		standings
	};
};

export const entries: EntryGenerator = async () => {
	const { readFile } = await import('node:fs/promises');
	const out: Array<{ season: string; comp: string }> = [];
	for (const season of SEASONS) {
		for (const comp of COMPS) {
			const path = `${process.cwd()}/static/data/${season.id}/standings/${comp.id}.json`;
			try {
				await readFile(path, 'utf-8');
				out.push({ season: season.id, comp: comp.id });
			} catch {
				// no data for this (season, comp) — skip (comp picker will show it as empty)
			}
		}
	}
	return out;
};
