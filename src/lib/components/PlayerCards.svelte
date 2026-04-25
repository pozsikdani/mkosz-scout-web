<script lang="ts">
	import { base } from '$app/paths';
	import type { PercentileStat, PlayerSeason, TeamPlayers } from '$lib/types';

	type PosCat = 'PG' | 'SG' | 'SF' | 'PF' | 'C';

	function posCategory(pos: string | undefined): PosCat | null {
		if (!pos) return null;
		const p = pos.replace(/\s/g, '');
		if (p === '1' || p === '1-2') return 'PG';
		if (p === '2' || p === '2-3') return 'SG';
		if (p === '3' || p === '3-4') return 'SF';
		if (p === '4' || p === '4-5') return 'PF';
		if (p === '5') return 'C';
		// Highest digit fallback
		const digits = (p.match(/\d/g) ?? []).map(Number);
		if (!digits.length) return null;
		const hi = Math.max(...digits);
		return (['PG', 'SG', 'SF', 'PF', 'C'][hi - 1] ?? null) as PosCat | null;
	}

	const POS_CLS: Record<PosCat, string> = {
		PG: 'bg-blue-500/25 text-blue-300',
		SG: 'bg-emerald-500/25 text-emerald-300',
		SF: 'bg-orange-500/25 text-orange-300',
		PF: 'bg-red-500/25 text-red-300',
		C: 'bg-purple-500/25 text-purple-300'
	};

	type Props = {
		data: TeamPlayers;
	};
	let { data }: Props = $props();

	type Group = 'starter' | 'rotation' | 'bench';

	function classify(p: PlayerSeason, teamMaxGp: number): Group {
		// Played in at least ~30% of team's games — hides 1-2 game cameos
		const minGp = Math.max(2, Math.round(teamMaxGp * 0.3));
		if (p.gp < minGp) return 'bench';
		if (p.gs_rate >= 0.5) return 'starter';
		if (p.mpg >= 10) return 'rotation';
		return 'bench';
	}

	const grouped = $derived.by(() => {
		const out: Record<Group, PlayerSeason[]> = { starter: [], rotation: [], bench: [] };
		for (const p of data.players) out[classify(p, data.team_max_gp)].push(p);
		return out;
	});

	let groupFilter = $state<'all' | Group>('all');

	const visiblePlayers = $derived(
		groupFilter === 'all'
			? [...grouped.starter, ...grouped.rotation, ...grouped.bench]
			: grouped[groupFilter]
	);

	function fmt(n: number | null | undefined, digits = 1): string {
		if (n === null || n === undefined) return '—';
		return n.toLocaleString('hu-HU', {
			minimumFractionDigits: digits,
			maximumFractionDigits: digits
		});
	}

	function pct(n: number | null | undefined): string {
		if (n === null || n === undefined) return '—';
		return n.toFixed(1);
	}

	// Inverted stats: lower = better (displayed pct = 100 - raw)
	const INVERTED: PercentileStat[] = ['tpg', 'fpg'];

	type BadgeKind = 'good' | 'bad' | null;
	function badge(p: PlayerSeason, key: PercentileStat): BadgeKind {
		const raw = p.percentiles[key];
		if (raw === undefined) return null;
		const v = INVERTED.includes(key) ? 100 - raw : raw;
		if (v >= 80) return 'good';
		if (v <= 20) return 'bad';
		return null;
	}

	function badgeText(p: PlayerSeason, key: PercentileStat): string | null {
		const raw = p.percentiles[key];
		if (raw === undefined) return null;
		const v = INVERTED.includes(key) ? 100 - raw : raw;
		if (v >= 80) return `top ${100 - v}%`;
		if (v <= 20) return `top ${100 - v}%`;
		return null;
	}

	const groupLabel: Record<Group, string> = {
		starter: 'Kezdők',
		rotation: 'Rotáció',
		bench: 'Cserepad'
	};
</script>

<div class="mb-4 flex flex-wrap items-center justify-between gap-3">
	<div>
		<h2 class="text-xl font-bold tracking-tight">Játékosok</h2>
		<p class="mt-1 text-xs text-muted">
			{data.players.length} játékos · szezonbeli átlagok (alapszakasz + rájátszás) · liga-percentile
			min. {data.thresholds.min_gp_for_percentile} meccs
		</p>
	</div>
	<div class="flex gap-1 rounded-lg border border-border bg-card p-1 text-xs font-semibold">
		<button
			type="button"
			onclick={() => (groupFilter = 'all')}
			class="rounded px-3 py-1.5 transition"
			class:bg-accent={groupFilter === 'all'}
			class:text-fg={groupFilter === 'all'}
			class:text-muted={groupFilter !== 'all'}
		>
			Összes <span class="ml-1 opacity-60">{data.players.length}</span>
		</button>
		{#each ['starter', 'rotation', 'bench'] as g (g)}
			{@const gKey = g as Group}
			<button
				type="button"
				onclick={() => (groupFilter = gKey)}
				class="rounded px-3 py-1.5 transition"
				class:bg-accent={groupFilter === gKey}
				class:text-fg={groupFilter === gKey}
				class:text-muted={groupFilter !== gKey}
				disabled={grouped[gKey].length === 0}
			>
				{groupLabel[gKey]}
				<span class="ml-1 opacity-60">{grouped[gKey].length}</span>
			</button>
		{/each}
	</div>
</div>

<div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
	{#each visiblePlayers as p (p.name)}
		{@const group = classify(p, data.team_max_gp)}
		<div
			class="overflow-hidden rounded-lg border border-border bg-card"
			class:opacity-90={group === 'bench'}
		>
			<!-- Header: photo, jersey, name, GP/GS, group chip -->
			<div class="flex items-center gap-3 border-b border-border px-4 py-3">
				{#if p.photo_filename}
					<img
						src={`${base}/players/${p.photo_filename}`}
						alt={p.name}
						loading="lazy"
						class="h-14 w-14 shrink-0 rounded-lg object-cover"
					/>
				{/if}
				<div
					class="flex h-10 w-10 shrink-0 items-center justify-center rounded font-mono text-base font-bold"
					class:bg-accent={group === 'starter'}
					class:text-fg={group === 'starter'}
					class:bg-border={group !== 'starter'}
					class:text-muted={group !== 'starter'}
				>
					{p.jersey ?? '—'}
				</div>
				<div class="min-w-0 flex-1">
					<p class="truncate font-semibold leading-tight">{p.name}</p>
					<p class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-xs text-muted">
						{#if posCategory(p.position)}
							{@const pc = posCategory(p.position)!}
							<span class="rounded px-1.5 py-0.5 text-[10px] font-bold {POS_CLS[pc]}">
								{pc}
							</span>
						{/if}
						{#if p.height_cm}
							<span>{p.height_cm}cm</span>
						{/if}
						<span>GP {p.gp} · GS {p.starts}{p.gs_rate > 0 ? ` (${Math.round(p.gs_rate * 100)}%)` : ''}</span>
					</p>
				</div>
				<span
					class="rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
					class:bg-accent={group === 'starter'}
					class:text-fg={group === 'starter'}
					class:bg-border={group !== 'starter'}
					class:text-muted={group !== 'starter'}
				>
					{groupLabel[group]}
				</span>
			</div>

			<!-- Stat row: 9 columns split into [MPG] [DREB OREB RPG] [APG TOV A/TO] [PF FD] -->
			<div class="grid grid-cols-9 gap-px bg-border text-center">
				{@render statCell('MPG', fmt(p.mpg), p, 'mpg')}
				{@render statCell('DREB', fmt(p.dreb_pg), p, 'dreb_pg')}
				{@render statCell('OREB', fmt(p.oreb_pg), p, 'oreb_pg')}
				{@render statCell('RPG', fmt(p.rpg), p, 'rpg')}
				{@render statCell('APG', fmt(p.apg), p, 'apg')}
				{@render statCell('TOV', fmt(p.tpg), p, 'tpg')}
				{@render statCell('A/TO', p.ato === null ? '—' : p.ato.toFixed(1))}
				{@render statCell('PF', fmt(p.fpg), p, 'fpg')}
				{@render statCell('FD', fmt(p.fdpg), p, 'fdpg')}
			</div>

			<!-- Defensive extras + scoring panel -->
			<div class="grid grid-cols-2 gap-px bg-border text-center">
				<div class="grid grid-cols-2 gap-px bg-border">
					{@render statCell('STL', fmt(p.spg), p, 'spg')}
					{@render statCell('BLK', fmt(p.bpg), p, 'bpg')}
				</div>
				<!-- Scoring panel: PPG | FG% | 3P% | FT% -->
				<div class="grid grid-cols-4 gap-px bg-border">
					{@render statCell('PPG', fmt(p.ppg), p, 'ppg', 'ppg')}
					{@render shotCell('FG%', pct(p.fg_pct), `${p.fg_made}/${p.fg_att}`, p, 'fg_pct')}
					{@render shotCell(
						'3P%',
						pct(p.three_pct),
						`${p.three_made}/${p.three_att}`,
						p,
						'three_pct'
					)}
					{@render shotCell('FT%', pct(p.ft_pct), `${p.ft_made}/${p.ft_att}`, p, 'ft_pct')}
				</div>
			</div>
		</div>
	{/each}
</div>

{#if visiblePlayers.length === 0}
	<p class="rounded border border-border bg-card p-6 text-center text-sm text-muted">
		Nincs játékos ebben a kategóriában.
	</p>
{/if}

<p class="mt-4 text-xs text-muted">
	Forrás: scoresheet (mkosz-stats DB) · Liga-percentile a hun2a alapszakaszában legalább {data
		.thresholds.min_gp_for_percentile} meccset játszó játékosok között · Lövés-százalékokhoz volume küszöb:
	FG≥{data.thresholds.min_fga}, 3P≥{data.thresholds.min_3pa}, FT≥{data.thresholds.min_fta}
</p>

{#snippet statCell(label: string, value: string, p?: PlayerSeason, pctKey?: PercentileStat, emphasis?: 'ppg')}
	{@const kind = p && pctKey ? badge(p, pctKey) : null}
	{@const txt = p && pctKey ? badgeText(p, pctKey) : null}
	<div
		class="relative bg-card px-2 py-2"
		class:bg-card-hover={emphasis === 'ppg'}
	>
		<p class="text-[9px] font-semibold uppercase tracking-wider text-muted">{label}</p>
		<p
			class="font-mono font-bold leading-tight"
			class:text-base={emphasis === 'ppg'}
			class:text-sm={emphasis !== 'ppg'}
			class:text-positive={kind === 'good'}
			class:text-negative={kind === 'bad'}
		>
			{value}
		</p>
		{#if txt}
			<span
				class="mt-0.5 inline-block rounded px-1 py-px text-[8px] font-bold uppercase leading-none"
				class:bg-positive={kind === 'good'}
				class:bg-negative={kind === 'bad'}
				class:text-bg={kind !== null}
			>
				{txt}
			</span>
		{/if}
	</div>
{/snippet}

{#snippet shotCell(
	label: string,
	value: string,
	sub: string,
	p: PlayerSeason,
	pctKey: PercentileStat
)}
	{@const kind = badge(p, pctKey)}
	{@const txt = badgeText(p, pctKey)}
	<div class="bg-card px-2 py-2">
		<p class="text-[9px] font-semibold uppercase tracking-wider text-muted">{label}</p>
		<p
			class="font-mono text-sm font-bold leading-tight"
			class:text-positive={kind === 'good'}
			class:text-negative={kind === 'bad'}
		>
			{value}
		</p>
		<p class="font-mono text-[9px] text-muted">{sub}</p>
		{#if txt}
			<span
				class="mt-0.5 inline-block rounded px-1 py-px text-[8px] font-bold uppercase leading-none"
				class:bg-positive={kind === 'good'}
				class:bg-negative={kind === 'bad'}
				class:text-bg={kind !== null}
			>
				{txt}
			</span>
		{/if}
	</div>
{/snippet}
