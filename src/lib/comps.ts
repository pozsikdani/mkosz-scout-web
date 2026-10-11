// NB1 B comp registry. Add new leagues here; routes, loaders, landing and
// export scripts pick them up via SEASONS × COMPS matrix.

export type CompId = 'hun2a' | 'hun2b';

export interface Comp {
	id: CompId;
	displayName: string; // "NB1 B Piros"
	shortName: string; // "Piros"
	accentClass: string; // Tailwind text color token for landing cards
}

export const COMPS: Comp[] = [
	{
		id: 'hun2a',
		displayName: 'NB1 B Piros',
		shortName: 'Piros',
		accentClass: 'text-accent'
	},
	{
		id: 'hun2b',
		displayName: 'NB1 B Zöld',
		shortName: 'Zöld',
		accentClass: 'text-positive'
	}
];

export function isComp(x: string | undefined): x is CompId {
	return COMPS.some((c) => c.id === x);
}

export function compBy(id: string | undefined): Comp | undefined {
	return COMPS.find((c) => c.id === id);
}
