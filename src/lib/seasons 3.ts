// Central season registry. Add a new entry here when the season rolls over —
// everything else (route params, loaders, landing, footer) picks it up.
//
// `displayName` is shown on landing cards and footer; `label` is the chip chip
// on team pages. `active=true` means the daily pipeline still writes to it.

export type SeasonId = 'x2526' | 'x2627';

export interface Season {
	id: SeasonId;
	displayName: string; // "2025/26", "2026/27"
	label: string; // "Archív" | "Aktív"
	active: boolean;
}

export const SEASONS: Season[] = [
	{ id: 'x2627', displayName: '2026/27', label: 'Aktív', active: true },
	{ id: 'x2526', displayName: '2025/26', label: 'Archív', active: false }
];

export const CURRENT_SEASON: Season = SEASONS[0];

export function isSeason(x: string | undefined): x is SeasonId {
	return SEASONS.some((s) => s.id === x);
}

export function seasonBy(id: string | undefined): Season | undefined {
	return SEASONS.find((s) => s.id === id);
}

export function seasonDisplay(id: string | undefined): string {
	return seasonBy(id)?.displayName ?? id ?? '';
}
