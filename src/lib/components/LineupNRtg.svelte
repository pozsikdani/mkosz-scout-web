<script lang="ts">
	import type { LineupNRtgMatch, TeamLineupNRtg } from '$lib/types';

	type Props = { data: TeamLineupNRtg };
	let { data }: Props = $props();

	const matches = $derived(data.matches);
	const allGamecodes = $derived(matches.map((m) => m.gamecode));

	let selectedSet = $state<Set<string>>(new Set());
	let initialized = $state(false);
	let selectorOpen = $state(false);
	let minMinutes = $state(5);

	// Default = last 8 (matches scout PDF default)
	$effect(() => {
		if (!initialized && matches.length > 0) {
			selectedSet = new Set(matches.slice(0, 8).map((m) => m.gamecode));
			initialized = true;
		}
	});

	const selectedMatches = $derived(matches.filter((m) => selectedSet.has(m.gamecode)));
	const selectedCount = $derived(selectedSet.size);
	const isAll = $derived(selectedCount === matches.length);
	const isLast8 = $derived(
		selectedCount === Math.min(8, matches.length) &&
			matches.slice(0, Math.min(8, matches.length)).every((m) => selectedSet.has(m.gamecode))
	);

	// Opponent context: how many opponent starters were on court during the stint
	type OppFilter = 'all' | 'starters' | 'mixed' | 'bench';
	let oppFilter = $state<OppFilter>('all');
	const OPP_BUCKETS: Record<Exclude<OppFilter, 'all'>, number[]> = {
		starters: [4, 5],
		mixed: [3],
		bench: [0, 1, 2]
	};
	const OPP_LABELS: Record<OppFilter, string> = {
		all: 'Mind',
		starters: 'Kezdők ellen (4–5)',
		mixed: 'Vegyes (3)',
		bench: 'Cserék ellen (0–2)'
	};

	type Agg = {
		players: string[];
		min: number;
		pf: number;
		pa: number;
		gp: number;
		is_starter: boolean;
		oppMin: number; // minutes with known opponent context
		oppStarterMin: number; // Σ (opponent starters × minutes) → weighted average
	};

	const aggregated = $derived.by((): Agg[] => {
		const map = new Map<string, Agg>();
		const buckets = oppFilter === 'all' ? null : OPP_BUCKETS[oppFilter];
		for (const m of selectedMatches) {
			for (const lu of m.lineups) {
				let min = lu.min;
				let pf = lu.pf;
				let pa = lu.pa;
				if (buckets) {
					if (!lu.opp) continue;
					min = pf = pa = 0;
					for (const b of buckets) {
						min += lu.opp[b][0];
						pf += lu.opp[b][1];
						pa += lu.opp[b][2];
					}
					if (min <= 0 && pf === 0 && pa === 0) continue;
				}
				let oppMin = 0;
				let oppStarterMin = 0;
				if (lu.opp) {
					lu.opp.forEach(([bm], i) => {
						if (buckets && !buckets.includes(i)) return;
						oppMin += bm;
						oppStarterMin += bm * i;
					});
				}
				const key = lu.players.slice().sort().join('|');
				const existing = map.get(key);
				if (existing) {
					existing.min += min;
					existing.pf += pf;
					existing.pa += pa;
					existing.gp += 1;
					existing.oppMin += oppMin;
					existing.oppStarterMin += oppStarterMin;
					if (lu.is_starter) existing.is_starter = true;
				} else {
					map.set(key, {
						players: lu.players,
						min,
						pf,
						pa,
						gp: 1,
						is_starter: lu.is_starter,
						oppMin,
						oppStarterMin
					});
				}
			}
		}
		return Array.from(map.values()).sort((a, b) => b.min - a.min);
	});

	function avgOppStarters(lu: Agg): string {
		return lu.oppMin > 0 ? (lu.oppStarterMin / lu.oppMin).toFixed(1) : '—';
	}

	const filteredLineups = $derived(aggregated.filter((a) => a.min >= minMinutes));
	const topLineups = $derived(filteredLineups.slice(0, 12));

	function nrtgColor(nrtg: number): string {
		const intensity = Math.min(Math.abs(nrtg) / 50, 1);
		if (nrtg >= 0) {
			const a = 0.08 + intensity * 0.32;
			return `rgba(0, 184, 148, ${a.toFixed(3)})`;
		} else {
			const a = 0.08 + intensity * 0.32;
			return `rgba(225, 112, 85, ${a.toFixed(3)})`;
		}
	}

	function lastName(n: string): string {
		return n.split(' ')[0];
	}

	function fmtDate(iso: string | null): string {
		if (!iso) return '—';
		const [, m, d] = iso.split('-');
		return `${m}.${d}`;
	}

	function selectAll() {
		selectedSet = new Set(allGamecodes);
	}
	function selectLast8() {
		selectedSet = new Set(matches.slice(0, 8).map((m) => m.gamecode));
	}
	function selectLast5() {
		selectedSet = new Set(matches.slice(0, 5).map((m) => m.gamecode));
	}
	function selectOnlyAlap() {
		selectedSet = new Set(matches.filter((m) => m.phase === 'alapszakasz').map((m) => m.gamecode));
	}
	function selectOnlyRaj() {
		selectedSet = new Set(matches.filter((m) => m.phase !== 'alapszakasz').map((m) => m.gamecode));
	}
	function selectOnlyHome() {
		selectedSet = new Set(matches.filter((m) => m.home).map((m) => m.gamecode));
	}
	function selectOnlyAway() {
		selectedSet = new Set(matches.filter((m) => !m.home).map((m) => m.gamecode));
	}
	function selectOnlyWon() {
		selectedSet = new Set(matches.filter((m) => m.result === 'W').map((m) => m.gamecode));
	}
	function selectOnlyLost() {
		selectedSet = new Set(matches.filter((m) => m.result === 'L').map((m) => m.gamecode));
	}
	function toggle(gc: string) {
		const next = new Set(selectedSet);
		if (next.has(gc)) next.delete(gc);
		else next.add(gc);
		selectedSet = next;
	}

	const hasRajatszas = $derived(matches.some((m) => m.phase !== 'alapszakasz'));
	const homeCount = $derived(matches.filter((m) => m.home).length);
	const awayCount = $derived(matches.filter((m) => !m.home).length);
	const wonCount = $derived(matches.filter((m) => m.result === 'W').length);
	const lostCount = $derived(matches.filter((m) => m.result === 'L').length);

	const singleMatch = $derived<LineupNRtgMatch | null>(
		selectedCount === 1 ? selectedMatches[0] : null
	);
</script>

<div class="mb-4">
	<h2 class="text-xl font-bold tracking-tight">Lineup Net Rating</h2>
	<p class="mt-1 text-xs text-muted">
		Ötösök perceken, dobott/kapott pontokon és NRTG/40-en számolva · PBP esemény-követéssel
	</p>
</div>

<!-- Selector toolbar -->
<div class="mb-4 flex flex-wrap items-center justify-between gap-3">
	<div class="flex flex-wrap items-center gap-2 text-xs">
		<button
			type="button"
			onclick={selectLast5}
			class="rounded border border-border bg-card px-2.5 py-1 font-semibold hover:bg-card-hover"
		>
			Utolsó 5
		</button>
		<button
			type="button"
			onclick={selectLast8}
			class="rounded border px-2.5 py-1 font-semibold transition"
			class:bg-accent={isLast8}
			class:text-fg={isLast8}
			class:border-accent={isLast8}
			class:border-border={!isLast8}
			class:bg-card={!isLast8}
			class:hover:bg-card-hover={!isLast8}
		>
			Utolsó 8 (alap)
		</button>
		<button
			type="button"
			onclick={selectAll}
			class="rounded border px-2.5 py-1 font-semibold transition"
			class:bg-accent={isAll}
			class:text-fg={isAll}
			class:border-accent={isAll}
			class:border-border={!isAll}
			class:bg-card={!isAll}
			class:hover:bg-card-hover={!isAll}
		>
			Teljes szezon ({matches.length})
		</button>
		<span class="text-muted">|</span>
		<button
			type="button"
			onclick={selectOnlyAlap}
			class="rounded border border-border bg-card px-2.5 py-1 font-semibold hover:bg-card-hover"
		>
			Alapszakasz
		</button>
		{#if hasRajatszas}
			<button
				type="button"
				onclick={selectOnlyRaj}
				class="rounded border border-border bg-card px-2.5 py-1 font-semibold hover:bg-card-hover"
			>
				Rájátszás
			</button>
		{/if}
		<span class="text-muted">|</span>
		<button
			type="button"
			onclick={selectOnlyHome}
			class="rounded border border-border bg-card px-2.5 py-1 font-semibold hover:bg-card-hover"
			disabled={homeCount === 0}>Hazai {homeCount}</button
		>
		<button
			type="button"
			onclick={selectOnlyAway}
			class="rounded border border-border bg-card px-2.5 py-1 font-semibold hover:bg-card-hover"
			disabled={awayCount === 0}>Vendég {awayCount}</button
		>
		<button
			type="button"
			onclick={selectOnlyWon}
			class="rounded border border-border bg-card px-2.5 py-1 font-semibold text-positive hover:bg-card-hover"
			disabled={wonCount === 0}>Nyert {wonCount}</button
		>
		<button
			type="button"
			onclick={selectOnlyLost}
			class="rounded border border-border bg-card px-2.5 py-1 font-semibold text-negative hover:bg-card-hover"
			disabled={lostCount === 0}>Vesztett {lostCount}</button
		>
	</div>
	<button
		type="button"
		onclick={() => (selectorOpen = !selectorOpen)}
		class="inline-flex items-center gap-2 rounded border border-border bg-card px-3 py-2 text-sm font-semibold transition hover:bg-card-hover"
	>
		<span>{selectedCount} <span class="text-muted">/ {matches.length} meccs</span></span>
		<span aria-hidden="true">{selectorOpen ? '▲' : '▼'}</span>
	</button>
</div>

{#if selectorOpen}
	<div class="mb-4 rounded-lg border border-border bg-card max-h-80 overflow-y-auto">
		<ul class="divide-y divide-border">
			{#each matches as m (m.gamecode)}
				{@const checked = selectedSet.has(m.gamecode)}
				<li>
					<label class="flex items-center gap-3 px-4 py-2 text-sm cursor-pointer hover:bg-card-hover">
						<input
							type="checkbox"
							{checked}
							onchange={() => toggle(m.gamecode)}
							class="h-4 w-4 accent-accent"
						/>
						<span class="w-14 font-mono text-xs text-muted">{fmtDate(m.date)}</span>
						<span class="w-5 font-mono text-xs" class:text-accent={!m.home}>
							{m.home ? 'H' : '@'}
						</span>
						<span class="flex-1 truncate">{m.opponent}</span>
						<span class="font-mono text-xs">
							<span class:text-positive={m.result === 'W'} class:text-negative={m.result === 'L'}
								>{m.our_score}</span
							>
							<span class="text-muted">–</span>
							<span class="text-muted">{m.their_score}</span>
						</span>
						<span class="w-10 text-right font-mono text-[10px] text-muted">{m.lineups.length} lu</span>
					</label>
				</li>
			{/each}
		</ul>
	</div>
{/if}

{#if singleMatch}
	<div class="mb-3 flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-4 py-2 text-sm">
		<span class="font-mono text-xs text-muted">{fmtDate(singleMatch.date)}</span>
		<span class="flex-1 font-medium">{singleMatch.home ? 'vs' : '@'} {singleMatch.opponent}</span>
		<span class="font-mono">
			<span class:text-positive={singleMatch.result === 'W'} class:text-negative={singleMatch.result === 'L'}
				>{singleMatch.our_score}</span
			>
			<span class="text-muted">–</span>
			<span class="text-muted">{singleMatch.their_score}</span>
		</span>
	</div>
{/if}

<!-- Opponent context filter -->
<div class="mb-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-muted">
	<span title="Hány ellenfél-kezdő volt a pályán az adott percekben">Ellenfél a pályán:</span>
	{#each ['all', 'starters', 'mixed', 'bench'] as f (f)}
		{@const key = f as OppFilter}
		<button
			type="button"
			onclick={() => (oppFilter = key)}
			class="rounded border px-2.5 py-1 font-semibold"
			class:bg-accent={oppFilter === key}
			class:text-fg={oppFilter === key}
			class:border-accent={oppFilter === key}
			class:border-border={oppFilter !== key}
		>
			{OPP_LABELS[key]}
		</button>
	{/each}
</div>

<!-- Min minutes filter -->
<div class="mb-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-muted">
	<span>Minimum perc:</span>
	{#each [3, 5, 10, 20] as m}
		<button
			type="button"
			onclick={() => (minMinutes = m)}
			class="rounded border px-2.5 py-1 font-mono"
			class:bg-accent={minMinutes === m}
			class:text-fg={minMinutes === m}
			class:border-accent={minMinutes === m}
			class:border-border={minMinutes !== m}
		>
			{m}+
		</button>
	{/each}
	<span class="ml-auto">{filteredLineups.length} ötös ≥ {minMinutes} perc · top 12 megjelenítve</span>
</div>

{#if selectedCount === 0}
	<div class="rounded-lg border border-border bg-card p-6 text-center text-sm text-muted">
		Válassz meccs(ek)et a lineup elemzéshez.
	</div>
{:else if topLineups.length === 0}
	<div class="rounded-lg border border-border bg-card p-6 text-center text-sm text-muted">
		Nincs ötös {minMinutes}+ perccel a kiválasztott meccseken{oppFilter !== 'all'
			? ` (${OPP_LABELS[oppFilter].toLowerCase()})`
			: ''}.
	</div>
{:else}
	<div class="overflow-x-auto rounded-lg border border-border">
		<table class="w-full text-sm">
			<thead class="bg-card-hover text-[10px] font-semibold uppercase tracking-wider text-muted">
				<tr>
					<th class="px-3 py-2 text-left">Lineup</th>
					<th class="w-14 px-2 py-2 text-right">MIN</th>
					<th class="w-10 px-2 py-2 text-right">GP</th>
					<th class="w-12 px-2 py-2 text-right">PTS+</th>
					<th class="w-12 px-2 py-2 text-right">PTS-</th>
					<th class="w-12 px-2 py-2 text-right">NET</th>
					<th class="w-16 px-2 py-2 text-right">NRTG/40</th>
					<th
						class="w-16 whitespace-nowrap px-2 py-2 text-right"
						title="Átlagosan hány ellenfél-kezdő volt a pályán (percekkel súlyozva)"
					>
						Ø ELL. K
					</th>
				</tr>
			</thead>
			<tbody>
				{#each topLineups as lu (lu.players.join('|'))}
					{@const net = lu.pf - lu.pa}
					{@const nrtg = lu.min > 0 ? (net / lu.min) * 40 : 0}
					<tr style:background-color={nrtgColor(nrtg)} class:font-bold={lu.is_starter}>
						<td class="px-3 py-2">
							<span class:font-bold={lu.is_starter} class="text-xs">
								{lu.players.map(lastName).join(', ')}
							</span>
							{#if lu.is_starter}
								<span class="ml-2 rounded bg-fg/10 px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase"
									>S5</span
								>
							{/if}
						</td>
						<td class="px-2 py-2 text-right font-mono">{lu.min.toFixed(0)}</td>
						<td class="px-2 py-2 text-right font-mono">{lu.gp}</td>
						<td class="px-2 py-2 text-right font-mono">{lu.pf}</td>
						<td class="px-2 py-2 text-right font-mono">{lu.pa}</td>
						<td
							class="px-2 py-2 text-right font-mono"
							class:text-positive={net > 0}
							class:text-negative={net < 0}
						>
							{net > 0 ? '+' : ''}{net}
						</td>
						<td
							class="px-2 py-2 text-right font-mono font-bold"
							class:text-positive={nrtg > 0}
							class:text-negative={nrtg < 0}
						>
							{nrtg > 0 ? '+' : ''}{nrtg.toFixed(1)}
						</td>
						<td class="px-2 py-2 text-right font-mono text-muted">{avgOppStarters(lu)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

<p class="mt-4 text-xs text-muted">
	[S5] = projected starting five (kezdőötös) · NRTG/40 = net pontkülönbség 40 perces vetítésben ·
	Ø ELL. K = átlagosan hány ellenfél-kezdő volt a pályán (0–5, percekkel súlyozva); a „Kezdők
	ellen / Cserék ellen" szűrő csak az adott ellenfél-összetétel melletti perceket és pontokat
	számolja · Forrás: PBP események (csere + scoring) lineup-szintű attribúcióval
</p>
