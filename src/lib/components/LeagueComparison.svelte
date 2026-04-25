<script lang="ts">
	import type { LeagueComparison, LeagueComparisonTeam } from '$lib/types';

	type Props = { data: LeagueComparison; ourTeam: string };
	let { data, ourTeam }: Props = $props();

	type StatKey = keyof Omit<LeagueComparisonTeam, 'team' | 'gp'>;
	type Category = {
		title: string;
		key: StatKey;
		fmt: (v: number) => string;
		ascending: boolean; // true = lower is better
	};

	const categories: Category[] = [
		{ title: 'Net Rating', key: 'nrtg', fmt: (v) => (v > 0 ? '+' : '') + v.toFixed(1), ascending: false },
		{ title: 'Offensive Rtg (PPG)', key: 'ppg', fmt: (v) => v.toFixed(1), ascending: false },
		{ title: 'Defensive Rtg (OPPG)', key: 'oppg', fmt: (v) => v.toFixed(1), ascending: true },
		{ title: 'Pace (Poss/G)', key: 'pace', fmt: (v) => v.toFixed(1), ascending: false },
		{ title: '3PT%', key: 'tp_pct', fmt: (v) => v.toFixed(1) + '%', ascending: false },
		{ title: 'FT%', key: 'ft_pct', fmt: (v) => v.toFixed(1) + '%', ascending: false },
		{ title: 'Rebounds / G', key: 'rpg', fmt: (v) => v.toFixed(1), ascending: false },
		{ title: 'Off. Rebounds / G', key: 'oreb_pg', fmt: (v) => v.toFixed(1), ascending: false },
		{ title: 'Def. Rebounds / G', key: 'dreb_pg', fmt: (v) => v.toFixed(1), ascending: false },
		{ title: 'Assists / G', key: 'apg', fmt: (v) => v.toFixed(1), ascending: false },
		{ title: 'Turnovers / G', key: 'topg', fmt: (v) => v.toFixed(1), ascending: true },
		{ title: 'Steals / G', key: 'spg', fmt: (v) => v.toFixed(1), ascending: false }
	];

	function shortName(tn: string): string {
		const map: Record<string, string> = {
			'Insedo Veszprém Kosárlabda Klub': 'Insedo Veszprém',
			'Tiszaújvárosi Termálfürdő Phoenix KK': 'Tiszaújváros',
			'HÜBNER Nyíregyháza BS': 'Nyíregyháza',
			'BKG PRIMA Akadémia': 'BKG PRIMA',
			'Peka Bau-MEAFC Wolves': 'Peka-MEAFC',
			'Phoenix-MT Fót': 'Phoenix-MT Fót',
			'Jászberényi KSE': 'Jászberényi'
		};
		return map[tn] ?? tn;
	}

	function isOurs(tn: string): boolean {
		return tn === ourTeam;
	}

	function rankedFor(cat: Category): { rank: number; team: LeagueComparisonTeam }[] {
		const sorted = data.teams
			.slice()
			.sort((a, b) => (cat.ascending ? a[cat.key] - b[cat.key] : b[cat.key] - a[cat.key]));
		return sorted.map((team, i) => ({ rank: i + 1, team }));
	}

	const ourRow = $derived(data.teams.find((t) => t.team === ourTeam));

	function ourRankFor(cat: Category): number | null {
		const ranked = rankedFor(cat);
		const found = ranked.find((r) => r.team.team === ourTeam);
		return found?.rank ?? null;
	}

	function rankColor(rank: number, total: number): string {
		// Top tertile green, middle gray, bottom tertile red
		const top = Math.ceil(total / 3);
		const bottom = total - Math.ceil(total / 3);
		if (rank <= top) return 'text-positive';
		if (rank > bottom) return 'text-negative';
		return 'text-muted';
	}
</script>

<div class="mb-4">
	<h2 class="text-xl font-bold tracking-tight">Liga összehasonlítás</h2>
	<p class="mt-1 text-xs text-muted">
		{data.team_count} csapat · 12 statisztikai kategória rangsora · piros sor = {ourTeam}
	</p>
</div>

{#if ourRow}
	<!-- Quick rank summary card -->
	<div class="mb-5 rounded-lg border border-border bg-card p-4">
		<p class="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">
			{ourTeam} — gyors helyezés-összegzés
		</p>
		<div class="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-6">
			{#each categories as cat (cat.key)}
				{@const rank = ourRankFor(cat)}
				{#if rank !== null}
					<div class="rounded border border-border bg-bg px-2 py-2 text-center">
						<p class="text-[9px] font-semibold uppercase tracking-wider text-muted">{cat.title}</p>
						<p class="mt-1 font-mono text-lg font-bold {rankColor(rank, data.team_count)}">
							#{rank}
						</p>
						<p class="font-mono text-[10px] text-muted">{cat.fmt(ourRow[cat.key])}</p>
					</div>
				{/if}
			{/each}
		</div>
	</div>
{/if}

<!-- 12 mini-tables in a responsive grid -->
<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
	{#each categories as cat (cat.key)}
		{@const ranked = rankedFor(cat)}
		<div class="overflow-hidden rounded-lg border border-border bg-card">
			<div class="border-b border-border bg-card-hover px-3 py-1.5">
				<p class="text-xs font-bold uppercase tracking-wider">{cat.title}</p>
			</div>
			<table class="w-full text-xs">
				<tbody>
					{#each ranked as { rank, team } (team.team)}
						{@const ours = isOurs(team.team)}
						<tr
							class="border-b border-border/40"
							class:bg-accent={ours}
							class:text-fg={ours}
							class:font-bold={ours}
						>
							<td class="w-6 px-2 py-1 text-right font-mono text-[10px]" class:text-muted={!ours}>
								{rank}.
							</td>
							<td class="truncate px-1 py-1" title={team.team}>
								{shortName(team.team)}
							</td>
							<td class="w-12 px-2 py-1 text-right font-mono">
								{cat.fmt(team[cat.key])}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/each}
</div>

<p class="mt-4 text-xs text-muted">
	Forrás: PBP események aggregálva (alapszakasz). Pace = FGA + 0.44·FTA + TOV − OREB. PPG/OPPG az
	hivatalos MKOSZ tabellából.
</p>
