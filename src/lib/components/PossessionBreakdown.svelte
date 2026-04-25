<script lang="ts">
	import type { PossessionCounts, PossessionMatch, TeamPossessions } from '$lib/types';

	type Props = {
		data: TeamPossessions;
		selectedGamecodes: Set<string>;
		teamLabel: string;
	};
	let { data, selectedGamecodes, teamLabel }: Props = $props();

	const matches = $derived(
		data.matches.filter((m) => m.has_pbp && selectedGamecodes.has(m.gamecode))
	);

	type Aggregate = {
		games: number;
		c: PossessionCounts;
		pace: number; // standard pace per game
		evTotal: number; // event total used as % denominator
	} | null;

	const agg = $derived.by<Aggregate>(() => {
		if (matches.length === 0) return null;
		const sum: PossessionCounts = {
			close_m: 0, mid_m: 0, three_m: 0, dunk_m: 0, ft: 0,
			close_x: 0, mid_x: 0, three_x: 0, dunk_x: 0, tov: 0,
			fga: 0, fta: 0, oreb: 0, tov_total: 0
		};
		for (const m of matches) {
			if (!m.counts) continue;
			for (const k of Object.keys(sum) as (keyof PossessionCounts)[]) {
				sum[k] += m.counts[k];
			}
		}
		const games = matches.length;
		const pace = (sum.fga + 0.44 * sum.fta + sum.tov_total - sum.oreb) / games;
		const sClose = sum.close_m + sum.dunk_m;
		const fClose = sum.close_x + sum.dunk_x;
		const evTotal =
			sClose + sum.mid_m + sum.three_m + sum.ft +
			fClose + sum.mid_x + sum.three_x + sum.tov;
		return { games, c: sum, pace, evTotal };
	});

	function pg(rawCount: number): string {
		if (!agg || agg.games === 0) return '—';
		const v = rawCount / agg.games;
		// Whole numbers when single game (raw count); 1 decimal for averages
		return agg.games === 1 ? v.toFixed(0) : v.toFixed(1);
	}

	function pct(rawCount: number): string {
		if (!agg || agg.evTotal === 0) return '—';
		return ((rawCount * 100) / agg.evTotal).toFixed(1);
	}

	const sClose = $derived(agg ? agg.c.close_m + agg.c.dunk_m : 0);
	const fClose = $derived(agg ? agg.c.close_x + agg.c.dunk_x : 0);
	const sTotal = $derived(agg ? sClose + agg.c.mid_m + agg.c.three_m + agg.c.ft : 0);
	const fTotal = $derived(agg ? fClose + agg.c.mid_x + agg.c.three_x + agg.c.tov : 0);

	// Shot distribution (ignores FT and TOV)
	const attClose = $derived(agg ? sClose + fClose : 0);
	const attMid = $derived(agg ? agg.c.mid_m + agg.c.mid_x : 0);
	const attThree = $derived(agg ? agg.c.three_m + agg.c.three_x : 0);
	const attTotal = $derived(attClose + attMid + attThree);

	function distPct(att: number): string {
		if (attTotal === 0) return '—';
		return Math.round((att * 100) / attTotal) + '%';
	}
	function fgPct(made: number, att: number): string {
		if (att === 0) return '—';
		return Math.round((made * 100) / att) + '%';
	}
</script>

<div class="rounded-lg border border-border bg-card overflow-hidden">
	<!-- Header -->
	<div class="flex items-baseline justify-between border-b border-border px-4 py-2.5">
		<h3 class="text-sm font-bold tracking-tight">Possession breakdown</h3>
		{#if agg}
			<p class="font-mono text-xs text-muted">
				<span class="font-semibold text-fg">{teamLabel}</span>
				<span class="ml-1 opacity-70">({agg.games}g)</span>
				<span class="ml-2">Possession/meccs:</span>
				<span class="ml-1 font-bold text-fg">{agg.pace.toFixed(1)}</span>
			</p>
		{/if}
	</div>

	{#if !agg}
		<div class="p-6 text-center text-sm text-muted">
			Válassz legalább egy meccset PBP adattal.
		</div>
	{:else}
		<!-- SIKERES group -->
		<div class="grid grid-cols-2 gap-px bg-border">
			<div class="bg-card-hover px-4 py-2 text-xs font-bold uppercase tracking-wider">
				<span class="text-positive">Sikeres</span>
				<span class="ml-2 text-muted">({pct(sTotal)}%)</span>
			</div>
			<div class="bg-card-hover px-4 py-2 text-right font-mono text-xs text-muted">
				eseményenként /g · % event-total
			</div>
		</div>
		{@render row('Közeli FG', agg.c.close_m + agg.c.dunk_m, 'good')}
		{@render row('Közép FG', agg.c.mid_m, 'good')}
		{@render row('Tripla FG', agg.c.three_m, 'good')}
		{@render row('Büntető', agg.c.ft, 'good')}

		<!-- SIKERTELEN group -->
		<div class="grid grid-cols-2 gap-px bg-border">
			<div class="bg-card-hover px-4 py-2 text-xs font-bold uppercase tracking-wider">
				<span class="text-negative">Sikertelen</span>
				<span class="ml-2 text-muted">({pct(fTotal)}%)</span>
			</div>
			<div class="bg-card-hover px-4 py-2"></div>
		</div>
		{@render row('Közeli miss', agg.c.close_x + agg.c.dunk_x, 'bad')}
		{@render row('Közép miss', agg.c.mid_x, 'bad')}
		{@render row('Tripla miss', agg.c.three_x, 'bad')}
		{@render row('Eladás (TOV)', agg.c.tov, 'bad')}

		<!-- Shot distribution -->
		<div class="grid grid-cols-2 gap-px bg-border">
			<div class="bg-card-hover px-4 py-2 text-xs font-bold uppercase tracking-wider text-muted">
				Dobáseloszlás
			</div>
			<div class="bg-card-hover px-4 py-2"></div>
		</div>
		<div class="grid grid-cols-2 gap-px bg-border">
			<div class="bg-card px-4 py-2 text-sm">Közeli</div>
			<div class="bg-card px-4 py-2 text-right font-mono text-sm">
				<span class="font-bold">{distPct(attClose)}</span>
				<span class="text-muted">(FG: {fgPct(sClose, attClose)})</span>
			</div>
		</div>
		<div class="grid grid-cols-2 gap-px bg-border">
			<div class="bg-card px-4 py-2 text-sm">Közép</div>
			<div class="bg-card px-4 py-2 text-right font-mono text-sm">
				<span class="font-bold">{distPct(attMid)}</span>
				<span class="text-muted">(FG: {fgPct(agg.c.mid_m, attMid)})</span>
			</div>
		</div>
		<div class="grid grid-cols-2 gap-px bg-border">
			<div class="bg-card px-4 py-2 text-sm">Tripla</div>
			<div class="bg-card px-4 py-2 text-right font-mono text-sm">
				<span class="font-bold">{distPct(attThree)}</span>
				<span class="text-muted">(FG: {fgPct(agg.c.three_m, attThree)})</span>
			</div>
		</div>
	{/if}
</div>

<p class="mt-3 text-xs text-muted">
	Eseményenkénti possession-számolás (a kihagyott dobás OREB után nem számít sikertelen possession-nek).
	/g normalizálva standard Pace-re (FGA + 0.44·FTA + TOV − OREB).
</p>

{#snippet row(label: string, count: number, kind: 'good' | 'bad')}
	<div class="grid grid-cols-2 gap-px bg-border">
		<div class="bg-card px-4 py-2 text-sm">{label}</div>
		<div
			class="bg-card px-4 py-2 text-right font-mono text-sm"
			class:text-positive={kind === 'good'}
			class:text-negative={kind === 'bad'}
		>
			<span class="font-bold">{pg(count)}/g</span>
			<span class="text-muted">({pct(count)}%)</span>
		</div>
	</div>
{/snippet}
