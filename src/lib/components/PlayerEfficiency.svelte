<script lang="ts">
	import type { PercentileStat, PlayerSeason, TeamPlayers } from '$lib/types';

	type Props = { data: TeamPlayers };
	let { data }: Props = $props();

	type Mode = 'liga' | 'poz';
	type Scope = 'rotation' | 'all';
	let mode = $state<Mode>('liga');
	let scope = $state<Scope>('rotation');

	const minFga = $derived(data.thresholds.min_fga_eff ?? 30);
	const minGp = $derived(data.thresholds.min_gp_for_percentile);

	const GRP_LABEL: Record<string, string> = { G: 'hátvéd', F: 'bedobó/erőcsatár', C: 'center' };

	type Col = {
		key: string;
		label: string;
		title: string;
		formula?: string;
		value: (p: PlayerSeason) => number | null | undefined;
		digits?: number;
		pct?: PercentileStat;
		neutral?: boolean;
		group?: boolean;
	};

	const COLS: Col[] = [
		{ key: 'gp', label: 'GP', title: 'Lejátszott meccsek.', value: (p) => p.gp, digits: 0 },
		{ key: 'mpg', label: 'MIN', title: 'Átlagos játékperc meccsenként.', value: (p) => p.mpg },
		{ key: 'ppg', label: 'PTS', title: 'Pont meccsenként.', value: (p) => p.ppg, pct: 'ppg' },
		{
			key: 'ts_pct',
			label: 'TS%',
			title: 'Valódi dobószázalék: a tripla többletértékét és a büntetőket is számolja. A pontszerzés hatékonyságának legjobb egyszámos mutatója.',
			formula: 'PTS / (2 · (FGA + 0,44 · FTA))',
			value: (p) => p.ts_pct,
			pct: 'ts_pct',
			group: true
		},
		{
			key: 'efg_pct',
			label: 'eFG%',
			title: 'Effektív mezőnyszázalék: a tripla 1,5 dobásnak számít. A büntetőket nem nézi.',
			formula: '(FGM + 0,5 · 3PM) / FGA',
			value: (p) => p.efg_pct,
			pct: 'efg_pct'
		},
		{
			key: 'ft_rate',
			label: 'FT-arány',
			title: 'Mennyi büntetőt harcol ki mezőnydobásonként, vagyis mennyire támad a gyűrű felé.',
			formula: 'FTA / FGA',
			value: (p) => p.ft_rate,
			pct: 'ft_rate'
		},
		{
			key: 'three_rate',
			label: '3PA arány',
			title: 'A mezőnydobások hány %-a tripla. Játékstílust mutat, ezért nincs jó/rossz színezése.',
			formula: '3PA / FGA',
			value: (p) => p.three_rate,
			pct: 'three_rate',
			neutral: true
		},
		{
			key: 'ato',
			label: 'AST/TO',
			title: 'Gólpassz és eladott labda aránya.',
			formula: 'AST / TOV',
			value: (p) => p.ato,
			digits: 2,
			pct: 'ato',
			group: true
		},
		{
			key: 'fg_att',
			label: 'FGA',
			title: 'A minta nagysága: összes mezőnydobás-kísérlet a szezonban. Ez alatt a küszöb alatt nincs percentilis-színezés.',
			value: (p) => p.fg_att,
			digits: 0,
			group: true
		}
	];

	let sortKey = $state<string>('mpg');
	let sortDesc = $state(true);

	function setSort(key: string) {
		if (sortKey === key) sortDesc = !sortDesc;
		else {
			sortKey = key;
			sortDesc = true;
		}
	}

	const small = (p: PlayerSeason) => p.gp < minGp || p.fg_att < minFga;

	const rows = $derived.by(() => {
		const col = COLS.find((c) => c.key === sortKey)!;
		const base = data.players.filter((p) => scope === 'all' || (p.mpg >= 10 && p.gp >= 2));
		return base.slice().sort((a, b) => {
			const va = col.value(a) ?? -Infinity;
			const vb = col.value(b) ?? -Infinity;
			return sortDesc ? vb - va : va - vb;
		});
	});

	/** Percentilis a választott alapon; pozíciós módban hiány esetén liga + jelölés. */
	function pctOf(p: PlayerSeason, key: PercentileStat): { v: number; fallback: boolean } | null {
		const liga = p.percentiles[key];
		if (mode === 'poz') {
			const pos = p.percentiles_pos?.[key];
			if (pos !== undefined) return { v: pos, fallback: false };
			return liga !== undefined ? { v: liga, fallback: true } : null;
		}
		return liga !== undefined ? { v: liga, fallback: false } : null;
	}

	function shade(v: number): string {
		if (v >= 75) return 'bg-positive/45 text-fg';
		if (v >= 50) return 'bg-positive/15';
		if (v >= 25) return 'bg-negative/15';
		return 'bg-negative/45 text-fg';
	}

	function fmt(v: number | null | undefined, digits = 1): string {
		if (v === null || v === undefined || !isFinite(v)) return '—';
		return v.toLocaleString('hu-HU', { minimumFractionDigits: digits, maximumFractionDigits: digits });
	}

	// Képlet-tooltip: hover / fókusz / koppintás
	let tipCol = $state<Col | null>(null);
	let tipX = $state(0);
	let tipY = $state(0);
	function showTip(c: Col, el: HTMLElement) {
		const r = el.getBoundingClientRect();
		tipCol = c;
		tipX = Math.min(Math.max(8, r.left), window.innerWidth - 288);
		tipY = r.bottom + 6;
	}
	function hideTip() {
		tipCol = null;
	}
</script>

<svelte:window onscroll={hideTip} />

<div class="mb-4 flex flex-wrap items-end justify-between gap-3">
	<div>
		<h2 class="text-xl font-bold tracking-tight">Hatékonyság</h2>
		<p class="mt-1 text-xs text-muted">
			Szezonbeli értékek · a cella színe a percentilis ({mode === 'liga' ? 'liga' : 'pozíción belül'})
		</p>
	</div>
	<div class="flex flex-wrap gap-2">
		<div class="flex gap-1 rounded-lg border border-border bg-card p-1 text-xs font-semibold" role="group" aria-label="Játékosok">
			<button
				class="rounded px-3 py-1 transition-colors"
				class:bg-accent={scope === 'rotation'}
				class:text-fg={scope === 'rotation'}
				class:text-muted={scope !== 'rotation'}
				aria-pressed={scope === 'rotation'}
				onclick={() => (scope = 'rotation')}>Rotáció (≥10 perc)</button
			>
			<button
				class="rounded px-3 py-1 transition-colors"
				class:bg-accent={scope === 'all'}
				class:text-fg={scope === 'all'}
				class:text-muted={scope !== 'all'}
				aria-pressed={scope === 'all'}
				onclick={() => (scope = 'all')}>Mind</button
			>
		</div>
		<div class="flex items-center gap-1 rounded-lg border border-border bg-card p-1 text-xs font-semibold" role="group" aria-label="Percentilis alapja">
			<span class="px-1.5 text-muted">Percentilis:</span>
			<button
				class="rounded px-3 py-1 transition-colors"
				class:bg-accent={mode === 'liga'}
				class:text-fg={mode === 'liga'}
				class:text-muted={mode !== 'liga'}
				aria-pressed={mode === 'liga'}
				onclick={() => (mode = 'liga')}>Liga</button
			>
			<button
				class="rounded px-3 py-1 transition-colors"
				class:bg-accent={mode === 'poz'}
				class:text-fg={mode === 'poz'}
				class:text-muted={mode !== 'poz'}
				aria-pressed={mode === 'poz'}
				onclick={() => (mode = 'poz')}>Pozíción belül</button
			>
		</div>
	</div>
</div>

<div class="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted">
	<span><span class="mr-1 inline-block h-3 w-3 rounded-sm bg-positive/45 align-[-2px]"></span>top 25%</span>
	<span><span class="mr-1 inline-block h-3 w-3 rounded-sm bg-positive/15 align-[-2px]"></span>medián felett</span>
	<span><span class="mr-1 inline-block h-3 w-3 rounded-sm bg-negative/15 align-[-2px]"></span>medián alatt</span>
	<span><span class="mr-1 inline-block h-3 w-3 rounded-sm bg-negative/45 align-[-2px]"></span>alsó 25%</span>
	<span class="opacity-60">halvány sor = kicsi minta</span>
	{#if mode === 'poz'}<span>pozíció: G hátvéd (1–2) · F bedobó/erőcsatár (3–4) · C center (5) · † nincs elég adat → liga</span>{/if}
	<span>oszlopfejléc: rendezés · <span class="font-serif italic">i</span>: képlet</span>
</div>

<div class="overflow-x-auto rounded-lg border border-border">
	<table class="w-full border-collapse text-sm tabular-nums">
		<thead>
			<tr class="bg-card text-[10px] uppercase tracking-wider text-muted">
				<th class="sticky left-0 z-10 bg-card px-3 py-2 text-left font-semibold">Játékos</th>
				{#each COLS as c (c.key)}
					<th class="whitespace-nowrap px-2 py-2 text-right font-semibold" class:border-l={c.group} class:border-border={c.group}>
						<span class="inline-flex items-center gap-1">
							<button
								class="uppercase tracking-wider hover:text-fg"
								class:text-fg={sortKey === c.key}
								onclick={() => setSort(c.key)}
								aria-label={`Rendezés: ${c.label}`}
							>
								{c.label}{sortKey === c.key ? (sortDesc ? ' ↓' : ' ↑') : ''}
							</button>
							<button
								class="grid h-3.5 w-3.5 place-items-center rounded-full border border-muted font-serif text-[9px] normal-case italic hover:border-fg hover:text-fg"
								aria-label={`${c.label}: magyarázat`}
								onmouseenter={(e) => showTip(c, e.currentTarget)}
								onmouseleave={hideTip}
								onfocus={(e) => showTip(c, e.currentTarget)}
								onblur={hideTip}
								onclick={(e) => showTip(c, e.currentTarget)}
							>i</button>
						</span>
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each rows as p (p.name)}
				{@const isSmall = small(p)}
				<tr class="border-t border-border hover:bg-card-hover" class:opacity-55={isSmall}>
					<td class="sticky left-0 z-10 whitespace-nowrap bg-card px-3 py-1.5">
						<div class="flex max-w-[8.5rem] items-baseline gap-1 sm:max-w-none" title={p.name}>
							<span class="hidden font-mono text-xs text-muted sm:inline">{p.jersey != null ? `#${p.jersey}` : ''}</span>
							<span class="truncate font-semibold">{p.name}</span>
							{#if p.pos_group}<span class="text-[10px] text-muted">{p.pos_group}</span>{/if}
							{#if isSmall}<span class="hidden text-[10px] text-muted sm:inline">· kicsi minta</span>{/if}
						</div>
					</td>
					{#each COLS as c (c.key)}
						{@const v = c.value(p)}
						{@const pc = c.pct && !c.neutral ? pctOf(p, c.pct) : null}
						<td class="whitespace-nowrap px-2 py-1.5 text-right" class:border-l={c.group} class:border-border={c.group}>
							{#if pc && !isSmall}
								<span
									class="inline-block min-w-[3.2em] rounded px-1.5 py-0.5 {shade(pc.v)}"
									title={`${pc.fallback ? 'liga' : mode === 'poz' ? GRP_LABEL[p.pos_group ?? ''] ?? 'liga' : 'liga'}-percentilis: ${pc.v}.`}
								>{fmt(v, c.digits ?? 1)}{pc.fallback ? '†' : ''}</span>
							{:else}
								<span class="inline-block min-w-[3.2em] px-1.5 py-0.5">{fmt(v, c.digits ?? 1)}</span>
							{/if}
						</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
</div>

{#if tipCol}
	<div
		class="pointer-events-none fixed z-50 max-w-[280px] rounded-lg border border-border bg-card-hover px-3 py-2 text-xs shadow-2xl"
		style:left="{tipX}px"
		style:top="{tipY}px"
		role="tooltip"
	>
		<p class="font-semibold">{tipCol.label}</p>
		<p class="mt-0.5 text-muted">{tipCol.title}</p>
		{#if tipCol.formula}<p class="mt-1 font-mono text-[11px]">{tipCol.formula}</p>{/if}
	</div>
{/if}

<p class="mt-4 text-xs text-muted">
	Forrás: play-by-play (a pontok és dobások egyeznek a hivatalos box score-ral) · alapszakasz + rájátszás ·
	Percentilis: legalább {minGp} meccs és {minFga} mezőnydobás; ez alatt „kicsi minta”, színezés nélkül ·
	Pozíción belüli percentilis csak ott, ahol legalább {data.thresholds.min_pos_pool ?? 8} összevethető játékos van ·
	A 3PA arány stílusmutató, nem kap színt.
</p>
