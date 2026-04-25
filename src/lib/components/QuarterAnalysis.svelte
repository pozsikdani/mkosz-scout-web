<script lang="ts">
	import type { MatchRow } from '$lib/types';

	type Props = { matches: MatchRow[] };
	let { matches }: Props = $props();

	const playedWithQuarters = $derived(
		matches
			.filter((m) => m.result !== null && m.quarter_scores && m.quarter_scores.length > 0)
			.slice()
			.sort((a, b) => (b.date ?? '').localeCompare(a.date ?? ''))
	);

	type Filter =
		| 'last5'
		| 'last8'
		| 'all'
		| 'alap'
		| 'rajatszas'
		| 'home'
		| 'away'
		| 'won'
		| 'lost';
	let filter = $state<Filter>('all');

	const filtered = $derived.by(() => {
		switch (filter) {
			case 'last5':
				return playedWithQuarters.slice(0, 5);
			case 'last8':
				return playedWithQuarters.slice(0, 8);
			case 'alap':
				return playedWithQuarters.filter((m) => m.phase === 'alapszakasz');
			case 'rajatszas':
				return playedWithQuarters.filter((m) => m.phase !== 'alapszakasz');
			case 'home':
				return playedWithQuarters.filter((m) => m.home);
			case 'away':
				return playedWithQuarters.filter((m) => !m.home);
			case 'won':
				return playedWithQuarters.filter((m) => m.result === 'W');
			case 'lost':
				return playedWithQuarters.filter((m) => m.result === 'L');
			default:
				return playedWithQuarters;
		}
	});

	type QStats = {
		quarter: number;
		label: string;
		gp: number;
		pf: number;
		pa: number;
		wins: number;
		losses: number;
		ties: number;
	};

	const quarterStats = $derived.by((): QStats[] => {
		const map = new Map<number, QStats>();
		for (const m of filtered) {
			if (!m.quarter_scores) continue;
			m.quarter_scores.forEach((q, i) => {
				const idx = i + 1;
				const ex = map.get(idx) ?? {
					quarter: idx,
					label: idx <= 4 ? `Q${idx}` : `OT${idx - 4}`,
					gp: 0,
					pf: 0,
					pa: 0,
					wins: 0,
					losses: 0,
					ties: 0
				};
				ex.gp += 1;
				ex.pf += q.our;
				ex.pa += q.their;
				if (q.our > q.their) ex.wins += 1;
				else if (q.our < q.their) ex.losses += 1;
				else ex.ties += 1;
				map.set(idx, ex);
			});
		}
		return Array.from(map.values()).sort((a, b) => a.quarter - b.quarter);
	});

	// Margin sorting only over regulation Q1-Q4 (OT skewed by small samples)
	const regularQuarters = $derived(quarterStats.filter((q) => q.quarter <= 4));
	const bestMargin = $derived(
		regularQuarters.reduce(
			(best, q) => {
				const m = (q.pf - q.pa) / Math.max(q.gp, 1);
				return m > best.margin ? { quarter: q.quarter, margin: m } : best;
			},
			{ quarter: 0, margin: -Infinity }
		)
	);
	const worstMargin = $derived(
		regularQuarters.reduce(
			(worst, q) => {
				const m = (q.pf - q.pa) / Math.max(q.gp, 1);
				return m < worst.margin ? { quarter: q.quarter, margin: m } : worst;
			},
			{ quarter: 0, margin: Infinity }
		)
	);

	function avg(n: number, gp: number): number {
		return gp > 0 ? n / gp : 0;
	}

	function fmtSigned(n: number): string {
		if (n > 0) return '+' + n.toFixed(1);
		return n.toFixed(1);
	}

	function fmtDate(iso: string | null): string {
		if (!iso) return '—';
		const [, m, d] = iso.split('-');
		return `${m}.${d}`;
	}

	const filterCounts = $derived({
		last5: Math.min(5, playedWithQuarters.length),
		last8: Math.min(8, playedWithQuarters.length),
		all: playedWithQuarters.length,
		alap: playedWithQuarters.filter((m) => m.phase === 'alapszakasz').length,
		rajatszas: playedWithQuarters.filter((m) => m.phase !== 'alapszakasz').length,
		home: playedWithQuarters.filter((m) => m.home).length,
		away: playedWithQuarters.filter((m) => !m.home).length,
		won: playedWithQuarters.filter((m) => m.result === 'W').length,
		lost: playedWithQuarters.filter((m) => m.result === 'L').length
	});

	type FilterOpt = { val: Filter; label: string; count: number; cls?: string };
	const filterOpts = $derived<FilterOpt[]>([
		{ val: 'last5', label: 'Utolsó 5', count: filterCounts.last5 },
		{ val: 'last8', label: 'Utolsó 8', count: filterCounts.last8 },
		{ val: 'all', label: 'Teljes szezon', count: filterCounts.all },
		{ val: 'alap', label: 'Alapszakasz', count: filterCounts.alap },
		{ val: 'rajatszas', label: 'Rájátszás', count: filterCounts.rajatszas },
		{ val: 'home', label: 'Hazai', count: filterCounts.home },
		{ val: 'away', label: 'Vendég', count: filterCounts.away },
		{ val: 'won', label: 'Nyert', count: filterCounts.won, cls: 'text-positive' },
		{ val: 'lost', label: 'Vesztett', count: filterCounts.lost, cls: 'text-negative' }
	]);

	function marginCellColor(margin: number): string {
		const intensity = Math.min(Math.abs(margin) / 6, 1);
		if (margin >= 0) {
			return `rgba(0, 184, 148, ${(0.08 + intensity * 0.32).toFixed(3)})`;
		}
		return `rgba(225, 112, 85, ${(0.08 + intensity * 0.32).toFixed(3)})`;
	}
</script>

<div class="mb-4">
	<h2 class="text-xl font-bold tracking-tight">Negyed-elemzés</h2>
	<p class="mt-1 text-xs text-muted">
		Negyedenkénti dobott / kapott / margin · {playedWithQuarters.length} meccs negyed-bontással
	</p>
</div>

<!-- Quick filters -->
<div class="mb-4 flex flex-wrap items-center gap-2 text-xs">
	{#each filterOpts as o (o.val)}
		<button
			type="button"
			onclick={() => (filter = o.val)}
			class="rounded border px-2.5 py-1 font-semibold transition {o.cls ?? ''}"
			class:bg-accent={filter === o.val}
			class:text-fg={filter === o.val}
			class:border-accent={filter === o.val}
			class:border-border={filter !== o.val}
			class:bg-card={filter !== o.val}
			class:hover:bg-card-hover={filter !== o.val}
			disabled={o.count === 0}
		>
			{o.label} {o.count}
		</button>
	{/each}
</div>

{#if filtered.length === 0}
	<div class="rounded-lg border border-border bg-card p-6 text-center text-sm text-muted">
		Nincs meccs a kiválasztott szűrővel.
	</div>
{:else}
	<!-- Best / Worst quarter highlight -->
	{#if regularQuarters.length > 0 && bestMargin.quarter > 0}
		<div class="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
			<div class="rounded-lg border border-positive/40 bg-positive/10 p-4">
				<p class="text-xs font-semibold uppercase tracking-wider text-positive">Legerősebb negyed</p>
				<p class="mt-1 font-mono text-3xl font-bold">Q{bestMargin.quarter}</p>
				<p class="font-mono text-sm text-muted">
					Átlag margin: <span class="text-positive font-bold">{fmtSigned(bestMargin.margin)}</span>
				</p>
			</div>
			<div class="rounded-lg border border-negative/40 bg-negative/10 p-4">
				<p class="text-xs font-semibold uppercase tracking-wider text-negative">Leggyengébb negyed</p>
				<p class="mt-1 font-mono text-3xl font-bold">Q{worstMargin.quarter}</p>
				<p class="font-mono text-sm text-muted">
					Átlag margin: <span class="text-negative font-bold">{fmtSigned(worstMargin.margin)}</span>
				</p>
			</div>
		</div>
	{/if}

	<!-- Per-quarter table -->
	<div class="overflow-x-auto rounded-lg border border-border">
		<table class="w-full text-sm">
			<thead class="bg-card-hover text-[10px] font-semibold uppercase tracking-wider text-muted">
				<tr>
					<th class="px-3 py-2 text-left">Negyed</th>
					<th class="w-14 px-2 py-2 text-right">GP</th>
					<th class="w-16 px-2 py-2 text-right">PF/g</th>
					<th class="w-16 px-2 py-2 text-right">PA/g</th>
					<th class="w-20 px-2 py-2 text-right">Margin/g</th>
					<th class="w-24 px-2 py-2 text-right">Negyed-mérleg</th>
				</tr>
			</thead>
			<tbody>
				{#each quarterStats as q (q.quarter)}
					{@const margin = avg(q.pf - q.pa, q.gp)}
					{@const isBest = q.quarter === bestMargin.quarter && q.quarter <= 4}
					{@const isWorst = q.quarter === worstMargin.quarter && q.quarter <= 4}
					<tr class="border-t border-border" style:background-color={marginCellColor(margin)}>
						<td class="px-3 py-2 font-bold">
							{q.label}
							{#if isBest}
								<span class="ml-2 rounded bg-positive/30 px-1.5 py-0.5 font-mono text-[9px] uppercase text-positive"
									>Best</span
								>
							{/if}
							{#if isWorst}
								<span class="ml-2 rounded bg-negative/30 px-1.5 py-0.5 font-mono text-[9px] uppercase text-negative"
									>Worst</span
								>
							{/if}
						</td>
						<td class="px-2 py-2 text-right font-mono">{q.gp}</td>
						<td class="px-2 py-2 text-right font-mono">{avg(q.pf, q.gp).toFixed(1)}</td>
						<td class="px-2 py-2 text-right font-mono">{avg(q.pa, q.gp).toFixed(1)}</td>
						<td
							class="px-2 py-2 text-right font-mono font-bold"
							class:text-positive={margin > 0}
							class:text-negative={margin < 0}
						>
							{fmtSigned(margin)}
						</td>
						<td class="px-2 py-2 text-right font-mono text-xs">
							<span class="text-positive font-bold">{q.wins}</span>
							<span class="text-muted">–</span>
							<span class="text-negative font-bold">{q.losses}</span>
							{#if q.ties > 0}
								<span class="text-muted">–{q.ties}</span>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<!-- Per-match heatmap -->
	<div class="mt-6">
		<h3 class="mb-2 text-sm font-bold uppercase tracking-wider text-muted">Per-meccs negyed-margin</h3>
		<div class="overflow-x-auto rounded-lg border border-border">
			<table class="w-full text-xs">
				<thead class="bg-card-hover text-[10px] font-semibold uppercase tracking-wider text-muted">
					<tr>
						<th class="w-14 px-2 py-1.5 text-left">Dátum</th>
						<th class="w-5 px-1 py-1.5 text-center"></th>
						<th class="px-2 py-1.5 text-left">Ellenfél</th>
						<th class="w-12 px-1 py-1.5 text-center">Q1</th>
						<th class="w-12 px-1 py-1.5 text-center">Q2</th>
						<th class="w-12 px-1 py-1.5 text-center">Q3</th>
						<th class="w-12 px-1 py-1.5 text-center">Q4</th>
						<th class="w-12 px-1 py-1.5 text-center">OT</th>
						<th class="w-14 px-2 py-1.5 text-right">Végeredmény</th>
					</tr>
				</thead>
				<tbody>
					{#each filtered as m (m.gamecode)}
						{@const qs = m.quarter_scores ?? []}
						<tr class="border-t border-border/40">
							<td class="px-2 py-1 font-mono text-muted">{fmtDate(m.date)}</td>
							<td class="px-1 py-1 text-center font-mono" class:text-accent={!m.home}>
								{m.home ? 'H' : '@'}
							</td>
							<td class="truncate px-2 py-1" title={m.opponent}>{m.opponent}</td>
							{#each [0, 1, 2, 3] as qi}
								{#if qs[qi]}
									{@const margin = qs[qi].our - qs[qi].their}
									<td
										class="px-1 py-1 text-center font-mono"
										style:background-color={marginCellColor(margin)}
										class:font-bold={true}
										class:text-positive={margin > 0}
										class:text-negative={margin < 0}
										title={`${qs[qi].our}-${qs[qi].their}`}
									>
										{margin > 0 ? '+' : ''}{margin}
									</td>
								{:else}
									<td class="px-1 py-1 text-center text-muted">—</td>
								{/if}
							{/each}
							<td class="px-1 py-1 text-center font-mono text-[10px]">
								{#if qs.length > 4}
									{@const otMargin = qs
										.slice(4)
										.reduce((s, q) => s + (q.our - q.their), 0)}
									<span
										class:text-positive={otMargin > 0}
										class:text-negative={otMargin < 0}
									>
										{otMargin > 0 ? '+' : ''}{otMargin}
									</span>
								{:else}
									<span class="text-muted">—</span>
								{/if}
							</td>
							<td class="px-2 py-1 text-right font-mono">
								<span class:text-positive={m.result === 'W'} class:text-negative={m.result === 'L'}>
									{m.our_score}
								</span>
								<span class="text-muted">–</span>
								<span class="text-muted">{m.their_score}</span>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
{/if}

<p class="mt-4 text-xs text-muted">
	Forrás: scoresheet negyedenkénti pontszámok. „Negyed-mérleg" = nyert/vesztett negyedek. Best/Worst
	csak Q1–Q4 alapján (OT a kis minta miatt nincs rangsorolva).
</p>
