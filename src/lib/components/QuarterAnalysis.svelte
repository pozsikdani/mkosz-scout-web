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

	const selectableGamecodes = $derived(playedWithQuarters.map((m) => m.gamecode));

	let selectedSet = $state<Set<string>>(new Set());
	let selectorOpen = $state(false);
	let initialized = $state(false);

	// Initialize selection to "all" once on first data load
	$effect(() => {
		if (playedWithQuarters.length > 0 && !initialized) {
			selectedSet = new Set(selectableGamecodes);
			initialized = true;
		}
	});

	const filtered = $derived(
		playedWithQuarters.filter((m) => selectedSet.has(m.gamecode))
	);
	const selectedCount = $derived(selectedSet.size);

	function toggleMatch(m: MatchRow) {
		const next = new Set(selectedSet);
		if (next.has(m.gamecode)) next.delete(m.gamecode);
		else next.add(m.gamecode);
		selectedSet = next;
	}
	function selectAll() {
		selectedSet = new Set(selectableGamecodes);
	}
	function selectNone() {
		selectedSet = new Set();
	}
	function selectLastN(n: number) {
		selectedSet = new Set(playedWithQuarters.slice(0, n).map((m) => m.gamecode));
	}
	function selectAlap() {
		selectedSet = new Set(
			playedWithQuarters.filter((m) => m.phase === 'alapszakasz').map((m) => m.gamecode)
		);
	}
	function selectRajatszas() {
		selectedSet = new Set(
			playedWithQuarters.filter((m) => m.phase !== 'alapszakasz').map((m) => m.gamecode)
		);
	}
	function selectHome() {
		selectedSet = new Set(playedWithQuarters.filter((m) => m.home).map((m) => m.gamecode));
	}
	function selectAway() {
		selectedSet = new Set(playedWithQuarters.filter((m) => !m.home).map((m) => m.gamecode));
	}
	function selectWon() {
		selectedSet = new Set(
			playedWithQuarters.filter((m) => m.result === 'W').map((m) => m.gamecode)
		);
	}
	function selectLost() {
		selectedSet = new Set(
			playedWithQuarters.filter((m) => m.result === 'L').map((m) => m.gamecode)
		);
	}

	const counts = $derived({
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
	const hasPlayoff = $derived(counts.rajatszas > 0);

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
	function fmtDateLong(iso: string | null): string {
		if (!iso) return '—';
		const [y, m, d] = iso.split('-');
		if (!y || !m || !d) return iso;
		return `${y}.${m}.${d}`;
	}
	function phaseLabel(phase: MatchRow['phase']): string {
		if (phase === 'alapszakasz') return 'Alapszakasz';
		if (phase === 'rajatszas_felso') return 'Felső házi';
		if (phase === 'rajatszas_also') return 'Alsó házi';
		return phase;
	}
	function phaseChipClass(phase: MatchRow['phase']): string {
		if (phase === 'alapszakasz') return 'bg-border text-muted';
		return 'bg-accent/20 text-accent';
	}

	function marginCellColor(margin: number): string {
		const intensity = Math.min(Math.abs(margin) / 6, 1);
		if (margin >= 0) {
			return `rgba(0, 184, 148, ${(0.08 + intensity * 0.32).toFixed(3)})`;
		}
		return `rgba(225, 112, 85, ${(0.08 + intensity * 0.32).toFixed(3)})`;
	}
</script>

<div class="mb-4 flex flex-wrap items-center justify-between gap-3">
	<div>
		<h2 class="text-xl font-bold tracking-tight">Negyed-elemzés</h2>
		<p class="mt-1 text-xs text-muted">
			Negyedenkénti dobott / kapott / margin · {playedWithQuarters.length} meccs negyed-bontással
		</p>
	</div>
	<button
		type="button"
		onclick={() => (selectorOpen = !selectorOpen)}
		class="inline-flex items-center gap-2 rounded border border-border bg-card px-3 py-2 text-sm font-semibold transition hover:bg-card-hover"
	>
		<span>
			{selectedCount}
			<span class="text-muted">/ {playedWithQuarters.length} meccs</span>
		</span>
		<span aria-hidden="true">{selectorOpen ? '▲' : '▼'}</span>
	</button>
</div>

{#if selectorOpen}
	<div class="mb-4 rounded-lg border border-border bg-card">
		<div class="flex flex-wrap gap-2 border-b border-border p-3 text-xs">
			<button
				type="button"
				onclick={selectAll}
				class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
			>
				Mind
			</button>
			<button
				type="button"
				onclick={selectNone}
				class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
			>
				Egyik sem
			</button>
			<span class="text-muted">|</span>
			<button
				type="button"
				onclick={() => selectLastN(5)}
				class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
				disabled={counts.last5 === 0}
			>
				Utolsó 5 <span class="opacity-60">{counts.last5}</span>
			</button>
			<button
				type="button"
				onclick={() => selectLastN(8)}
				class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
				disabled={counts.last8 === 0}
			>
				Utolsó 8 <span class="opacity-60">{counts.last8}</span>
			</button>
			<span class="text-muted">|</span>
			<button
				type="button"
				onclick={selectAlap}
				class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
				disabled={counts.alap === 0}
			>
				Csak alapszakasz <span class="opacity-60">{counts.alap}</span>
			</button>
			{#if hasPlayoff}
				<button
					type="button"
					onclick={selectRajatszas}
					class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
				>
					Csak rájátszás <span class="opacity-60">{counts.rajatszas}</span>
				</button>
			{/if}
			<span class="text-muted">|</span>
			<button
				type="button"
				onclick={selectHome}
				class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
				disabled={counts.home === 0}
			>
				Csak hazai <span class="opacity-60">{counts.home}</span>
			</button>
			<button
				type="button"
				onclick={selectAway}
				class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
				disabled={counts.away === 0}
			>
				Csak vendég <span class="opacity-60">{counts.away}</span>
			</button>
			<span class="text-muted">|</span>
			<button
				type="button"
				onclick={selectWon}
				class="rounded border border-border px-2.5 py-1 font-semibold text-positive hover:bg-card-hover"
				disabled={counts.won === 0}
			>
				Csak nyert <span class="opacity-60">{counts.won}</span>
			</button>
			<button
				type="button"
				onclick={selectLost}
				class="rounded border border-border px-2.5 py-1 font-semibold text-negative hover:bg-card-hover"
				disabled={counts.lost === 0}
			>
				Csak vesztett <span class="opacity-60">{counts.lost}</span>
			</button>
		</div>
		<ul class="max-h-96 divide-y divide-border overflow-y-auto">
			{#each playedWithQuarters as m (m.gamecode)}
				{@const checked = selectedSet.has(m.gamecode)}
				<li>
					<label
						class="flex flex-wrap items-center gap-3 px-4 py-2 text-sm cursor-pointer hover:bg-card-hover"
					>
						<input
							type="checkbox"
							{checked}
							onchange={() => toggleMatch(m)}
							class="h-4 w-4 accent-accent"
						/>
						<span class="w-20 font-mono text-xs text-muted">{fmtDateLong(m.date)}</span>
						<span
							class="rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider {phaseChipClass(
								m.phase
							)}"
						>
							{phaseLabel(m.phase)}
						</span>
						<span
							class="w-5 text-center font-mono text-xs"
							class:text-muted={m.home}
							class:text-accent={!m.home}
						>
							{m.home ? 'H' : '@'}
						</span>
						<span class="flex-1 truncate">{m.opponent}</span>
						{#if m.result}
							<span class="font-mono text-xs">
								<span
									class:text-positive={m.result === 'W'}
									class:text-negative={m.result === 'L'}
								>
									{m.our_score}
								</span>
								<span class="text-muted">–</span>
								<span class="text-muted">{m.their_score}</span>
							</span>
							<span
								class="w-5 rounded px-1 py-0.5 text-center font-mono text-[10px] font-bold"
								class:bg-positive={m.result === 'W'}
								class:bg-negative={m.result === 'L'}
								class:text-bg={m.result !== null}
							>
								{m.result}
							</span>
						{/if}
					</label>
				</li>
			{/each}
		</ul>
	</div>
{/if}

{#if filtered.length === 0}
	<div class="rounded-lg border border-border bg-card p-6 text-center text-sm text-muted">
		Nincs kiválasztott meccs. Nyisd meg a fenti meccs-választót és válassz legalább egyet.
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
	Forrás: scoresheet negyedenkénti pontszámok. „Negyed-mérleg" = nyert/vesztett negyedek.
	Best/Worst csak Q1–Q4 alapján (OT a kis minta miatt nincs rangsorolva). A meccs-választóban
	gyors-szűrőkkel beállíthatsz egy halmazt, vagy kattintással bármelyik meccset egyenként.
</p>
