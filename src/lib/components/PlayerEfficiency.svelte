<script lang="ts">
	import type { PercentileStat, PlayerSeason, TeamPlayers } from '$lib/types';

	import { base } from '$app/paths';

	// league: liga-szintű ranglista (csapat-oszlop, keresés); seasonId/compId a csapat-linkhez
	type Props = { data: TeamPlayers; league?: boolean; seasonId?: string; compId?: string };
	let { data, league = false, seasonId = '', compId = '' }: Props = $props();
	let query = $state('');
	const rowKey = (p: PlayerSeason) => `${p.team_slug ?? ''}/${p.name}`;

	type Mode = 'liga' | 'poz';
	type Scope = 'rotation' | 'all';
	let mode = $state<Mode>('liga');
	let scope = $state<Scope>('rotation');

	const minFga = $derived(data.thresholds.min_fga_eff ?? 30);
	const minPoss = $derived(data.thresholds.min_poss ?? 50);
	const minGp = $derived(data.thresholds.min_gp_for_percentile);

	const GRP_LABEL: Record<string, string> = { G: 'hátvéd', F: 'bedobó/erőcsatár', C: 'center' };

	// Kevesebb = jobb: a színezés megfordul
	const INVERTED = new Set<PercentileStat>(['tov_pct', 'tov_100']);

	type Col = {
		key: string;
		label: string;
		title: string;
		formula?: string;
		value: (p: PlayerSeason) => number | null | undefined;
		digits?: number;
		pct?: PercentileStat;
		neutral?: boolean;
		signed?: boolean;
		group?: string; // csoport első oszlopán: a csoport neve
	};

	const P100 = '· 100 / saját labdabirtoklás a pályán';

	const COLS: Col[] = [
		{ key: 'gp', label: 'GP', title: 'Lejátszott meccsek.', value: (p) => p.gp, digits: 0 },
		{ key: 'mpg', label: 'MIN', title: 'Átlagos játékperc meccsenként.', value: (p) => p.mpg },
		{
			key: 'ts_pct', label: 'TS%', group: 'Dobás',
			title: 'Valódi dobószázalék: a tripla többletértékét és a büntetőket is számolja. A pontszerzés hatékonyságának legjobb egyszámos mutatója.',
			formula: 'PTS / (2 · (FGA + 0,44 · FTA))', value: (p) => p.ts_pct, pct: 'ts_pct'
		},
		{
			key: 'efg_pct', label: 'eFG%',
			title: 'Effektív mezőnyszázalék: a tripla 1,5 dobásnak számít. A büntetőket nem nézi.',
			formula: '(FGM + 0,5 · 3PM) / FGA', value: (p) => p.efg_pct, pct: 'efg_pct'
		},
		{
			key: 'ft_rate', label: 'FT-arány',
			title: 'Mennyi büntetőt harcol ki mezőnydobásonként, vagyis mennyire támad a gyűrű felé.',
			formula: 'FTA / FGA', value: (p) => p.ft_rate, pct: 'ft_rate'
		},
		{
			key: 'three_rate', label: '3PA arány',
			title: 'A mezőnydobások hány %-a tripla. Játékstílust mutat, ezért nincs jó/rossz színezése.',
			formula: '3PA / FGA', value: (p) => p.three_rate, pct: 'three_rate', neutral: true
		},
		{
			key: 'usg_pct', label: 'USG%', group: 'Szerep',
			title: 'A csapat labdabirtoklásainak hány %-át fejezi be (dobás, büntető vagy eladott labda), amíg a pályán van. Megmutatja, ki az első opció.',
			formula: '(FGA + 0,44 · FTA + TOV) / ugyanez a csapatra, amíg pályán van', value: (p) => p.usg_pct, pct: 'usg_pct'
		},
		{
			key: 'ast_pct', label: 'AST%',
			title: 'Amíg a pályán van, a csapattársak kosarainak hány %-át készíti elő.',
			formula: 'AST / (csapat FGM a pályán − saját FGM)', value: (p) => p.ast_pct, pct: 'ast_pct'
		},
		{
			key: 'tov_pct', label: 'TOV%',
			title: 'A saját befejezett labdabirtoklásainak hány %-a eladott labda. Kevesebb = jobb.',
			formula: 'TOV / (FGA + 0,44 · FTA + TOV)', value: (p) => p.tov_pct, pct: 'tov_pct'
		},
		{
			key: 'ato', label: 'AST/TO', title: 'Gólpassz és eladott labda aránya.',
			formula: 'AST / TOV', value: (p) => p.ato, digits: 2, pct: 'ato'
		},
		{ key: 'pts_100', label: 'PTS', group: '/100 labdabirtoklás', title: 'Pont 100 labdabirtoklásra, amíg a pályán van. A sok és kevés percet játszók így összevethetők.', formula: `PTS ${P100}`, value: (p) => p.pts_100, pct: 'pts_100' },
		{ key: 'reb_100', label: 'REB', title: 'Lepattanó 100 labdabirtoklásra.', formula: `REB ${P100}`, value: (p) => p.reb_100, pct: 'reb_100' },
		{ key: 'ast_100', label: 'AST', title: 'Gólpassz 100 labdabirtoklásra.', formula: `AST ${P100}`, value: (p) => p.ast_100, pct: 'ast_100' },
		{ key: 'tov_100', label: 'TOV', title: 'Eladott labda 100 labdabirtoklásra. Kevesebb = jobb.', formula: `TOV ${P100}`, value: (p) => p.tov_100, pct: 'tov_100' },
		{ key: 'stl_100', label: 'STL', title: 'Szerzett labda 100 labdabirtoklásra.', formula: `STL ${P100}`, value: (p) => p.stl_100, pct: 'stl_100' },
		{ key: 'blk_100', label: 'BLK', title: 'Blokk 100 labdabirtoklásra. A rögzítése jegyzőkönyvíró-függő.', formula: `BLK ${P100}`, value: (p) => p.blk_100, pct: 'blk_100' },
		{ key: 'fd_100', label: 'FD', title: 'Kiharcolt személyi hiba 100 labdabirtoklásra.', formula: `kiharcolt fault ${P100}`, value: (p) => p.fd_100, pct: 'fd_100' },
		{
			key: 'oreb_pct', label: 'OREB%', group: 'Lepattanó',
			title: 'A támadó lepattanó-lehetőségek hány %-át szerzi meg, amíg a pályán van.',
			formula: 'OREB / (csapat OREB + ellenfél DREB), pályán', value: (p) => p.oreb_pct, pct: 'oreb_pct'
		},
		{
			key: 'dreb_pct', label: 'DREB%',
			title: 'A védő lepattanó-lehetőségek hány %-át szerzi meg, amíg a pályán van.',
			formula: 'DREB / (csapat DREB + ellenfél OREB), pályán', value: (p) => p.dreb_pct, pct: 'dreb_pct'
		},
		{
			key: 'on_nrtg', label: 'ON NRtg', group: 'Hatás', signed: true,
			title: 'A csapat nettó ratingje (100 labdabirtoklásra), amíg a játékos a pályán van.',
			formula: '100 · PF / poss − 100 · PA / ellenfél-poss', value: (p) => p.on_nrtg, pct: 'on_nrtg'
		},
		{
			key: 'onoff_nrtg', label: 'ON–OFF', signed: true,
			title: `Mennyivel jobb a csapat nettó ratingje vele, mint nélküle (a szezon összes meccsén). Ha a játékos keveset ült a padon (${'<'} 50 labdabirtoklás), nincs színezés.`,
			formula: 'ON NRtg − OFF NRtg', value: (p) => p.onoff_nrtg, pct: 'onoff_nrtg'
		},
		{
			key: 'xpps', label: 'xPPS', group: 'Dobásminőség', digits: 2,
			title: 'Várható pont dobásonként: a játékos dobásai a lövéstérkép zónáiban mennyit érnének liga-átlagos értékesítéssel. A dobásválasztás minősége (gyűrű közeli és sarok-tripla = jó, középtáv = gyenge).',
			formula: 'Σ (zóna liga-FG% × zóna értéke) / dobások', value: (p) => p.xpps, pct: 'xpps'
		},
		{
			key: 'pps_diff', label: 'Többlet', digits: 2, signed: true,
			title: 'Ténylegesen szerzett pont dobásonként mínusz a várható. Pozitív = a liga-átlagnál jobban értékesíti a saját dobásait.',
			formula: 'PPS − xPPS (büntetők nélkül)', value: (p) => p.pps_diff, pct: 'pps_diff'
		},
		{
			key: 'assisted_pct', label: 'Gólpasszból',
			title: 'A saját mezőnykosarainak hány %-a jött gólpasszból. Stílusmutató: alacsony = maga teremti a helyzetét, magas = befejező. Nincs jó/rossz színezése.',
			formula: 'gólpasszhoz párosított FGM / FGM', value: (p) => p.assisted_pct, pct: 'assisted_pct', neutral: true
		},
		{
			key: 'poss_on', label: 'Poss', group: 'Minta',
			title: 'A minta nagysága: labdabirtoklások, amíg a pályán volt. 50 alatt kicsi minta.',
			formula: 'FGA + 0,44 · FTA + TOV − OREB (csapat, pályán)', value: (p) => p.poss_on, digits: 0
		}
	];

	const GROUP_SPANS = $derived.by(() => {
		const spans: { label: string; span: number }[] = [];
		for (const c of COLS) {
			if (c.group || spans.length === 0) spans.push({ label: c.group ?? '', span: 1 });
			else spans[spans.length - 1].span++;
		}
		return spans;
	});

	let sortKey = $state<string>('mpg');
	let sortDesc = $state(true);
	function setSort(key: string) {
		if (sortKey === key) sortDesc = !sortDesc;
		else {
			sortKey = key;
			sortDesc = true;
		}
	}

	const small = (p: PlayerSeason) =>
		p.gp < minGp || (p.poss_on !== undefined ? p.poss_on < minPoss : p.fg_att < minFga);

	const rows = $derived.by(() => {
		const col = COLS.find((c) => c.key === sortKey)!;
		const q = query.trim().toLowerCase();
		const pool = data.players.filter(
			(p) =>
				(scope === 'all' || (p.mpg >= 10 && p.gp >= 2)) &&
				(!q || p.name.toLowerCase().includes(q) || (p.team ?? '').toLowerCase().includes(q))
		);
		// Elég mintával rendelkezők (van percentilisük az adott mutatóra) előre kerülnek
		const ok = (p: PlayerSeason) => (col.pct ? p.percentiles[col.pct] !== undefined : true);
		return pool.slice().sort((a, b) => {
			if (ok(a) !== ok(b)) return ok(a) ? -1 : 1;
			const va = col.value(a) ?? -Infinity;
			const vb = col.value(b) ?? -Infinity;
			return sortDesc ? vb - va : va - vb;
		});
	});

	/** Percentilis a választott alapon (fordított mutatónál már "jóság" szerint). */
	function pctOf(p: PlayerSeason, key: PercentileStat): { v: number; fallback: boolean } | null {
		const liga = p.percentiles[key];
		let out: { v: number; fallback: boolean } | null = null;
		if (mode === 'poz') {
			const pos = p.percentiles_pos?.[key];
			if (pos !== undefined) out = { v: pos, fallback: false };
			else if (liga !== undefined) out = { v: liga, fallback: true };
		} else if (liga !== undefined) out = { v: liga, fallback: false };
		if (out && INVERTED.has(key)) out.v = 100 - out.v;
		return out;
	}

	function shade(v: number): string {
		if (v >= 75) return 'bg-positive/45 text-fg';
		if (v >= 50) return 'bg-positive/15';
		if (v >= 25) return 'bg-negative/15';
		return 'bg-negative/45 text-fg';
	}

	function diff(a: number | null | undefined, b: number | null | undefined): number | null {
		return a == null || b == null ? null : a - b;
	}

	function fmt(v: number | null | undefined, digits = 1, signed = false): string {
		if (v === null || v === undefined || !isFinite(v)) return '—';
		const s = v.toLocaleString('hu-HU', { minimumFractionDigits: digits, maximumFractionDigits: digits });
		return signed && v > 0 ? `+${s}` : s;
	}

	// Részlet-panel
	let selected = $state<string | null>(null);
	let wrapW = $state(0);
	const BARS: { label: string; key: PercentileStat; value: (p: PlayerSeason) => number | null | undefined; digits?: number }[] = [
		{ label: 'TS%', key: 'ts_pct', value: (p) => p.ts_pct },
		{ label: 'eFG%', key: 'efg_pct', value: (p) => p.efg_pct },
		{ label: 'FT-arány', key: 'ft_rate', value: (p) => p.ft_rate },
		{ label: 'USG%', key: 'usg_pct', value: (p) => p.usg_pct },
		{ label: 'AST%', key: 'ast_pct', value: (p) => p.ast_pct },
		{ label: 'TOV% (ford.)', key: 'tov_pct', value: (p) => p.tov_pct },
		{ label: 'OREB%', key: 'oreb_pct', value: (p) => p.oreb_pct },
		{ label: 'DREB%', key: 'dreb_pct', value: (p) => p.dreb_pct },
		{ label: 'STL/100', key: 'stl_100', value: (p) => p.stl_100 },
		{ label: 'ON–OFF', key: 'onoff_nrtg', value: (p) => p.onoff_nrtg },
		{ label: 'xPPS', key: 'xpps', value: (p) => p.xpps, digits: 2 },
		{ label: 'Többlet', key: 'pps_diff', value: (p) => p.pps_diff, digits: 2 }
	];
	const CLUTCH_MIN = 10;

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
		<h2 class="text-xl font-bold tracking-tight">{league ? 'Játékos-ranglista' : 'Hatékonyság'}</h2>
		<p class="mt-1 text-xs text-muted">
			Szezonbeli értékek · a cella színe a percentilis ({mode === 'liga' ? 'liga' : 'pozíción belül'}) · kattints egy sorra a részletekhez
		</p>
	</div>
	<div class="flex flex-wrap gap-2">
		{#if league}
			<input
				id="player-search"
				type="search"
				bind:value={query}
				placeholder="Játékos vagy csapat…"
				class="w-44 rounded-lg border border-border bg-card px-3 py-1 text-xs placeholder:text-muted focus:border-accent focus:outline-none"
			/>
		{/if}
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

<div class="overflow-x-auto rounded-lg border border-border" bind:clientWidth={wrapW}>
	<table class="w-full border-collapse text-sm tabular-nums">
		<thead>
			<tr class="bg-card text-[10px] uppercase tracking-wider text-muted">
				<th class="sticky left-0 z-10 bg-card"></th>
				{#each GROUP_SPANS as g, i (i)}
					<th colspan={g.span} class="px-2 pt-2 text-left font-semibold text-fg/70" class:border-l={g.label} class:border-border={g.label}>{g.label}</th>
				{/each}
			</tr>
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
			{#each rows as p (rowKey(p))}
				{@const isSmall = small(p)}
				<tr
					class="cursor-pointer border-t border-border hover:bg-card-hover"
					class:opacity-55={isSmall}
					class:bg-card-hover={selected === rowKey(p)}
					onclick={() => (selected = selected === rowKey(p) ? null : rowKey(p))}
				>
					<td class="sticky left-0 z-10 whitespace-nowrap bg-card px-3 py-1.5" class:!bg-card-hover={selected === rowKey(p)}>
						<div class="flex max-w-[8.5rem] items-baseline gap-1 sm:max-w-none" title={p.name}>
							<span class="hidden font-mono text-xs text-muted sm:inline">{p.jersey != null ? `#${p.jersey}` : ''}</span>
							<span class="truncate font-semibold">{p.name}</span>
							{#if p.pos_group}<span class="text-[10px] text-muted">{p.pos_group}</span>{/if}
							{#if isSmall}<span class="hidden text-[10px] text-muted sm:inline">· kicsi minta</span>{/if}
						</div>
						{#if league && p.team}
							<div class="max-w-[8.5rem] truncate text-[10px] text-muted sm:max-w-[16rem]">{p.team}</div>
						{/if}
					</td>
					{#each COLS as c (c.key)}
						{@const v = c.value(p)}
						{@const pc = c.pct && !c.neutral ? pctOf(p, c.pct) : null}
						<td class="whitespace-nowrap px-2 py-1.5 text-right" class:border-l={c.group} class:border-border={c.group}>
							{#if pc}
								<span
									class="inline-block min-w-[3.2em] rounded px-1.5 py-0.5 {shade(pc.v)}"
									title={`${pc.fallback || mode === 'liga' ? 'liga' : GRP_LABEL[p.pos_group ?? ''] ?? 'liga'}-percentilis: ${pc.v}.`}
								>{fmt(v, c.digits ?? 1, c.signed)}{pc.fallback ? '†' : ''}</span>
							{:else}
								<span class="inline-block min-w-[3.2em] px-1.5 py-0.5">{fmt(v, c.digits ?? 1, c.signed)}</span>
							{/if}
						</td>
					{/each}
				</tr>
				{#if selected === rowKey(p)}
					<tr>
						<td colspan={COLS.length + 1} class="p-0">{@render detail(p)}</td>
					</tr>
				{/if}
			{/each}
		</tbody>
	</table>
</div>

{#snippet detail(sel: PlayerSeason)}
	<div class="sticky left-0 grid gap-4 border-y border-border bg-card p-4 md:grid-cols-2" style:width="{wrapW}px">
		<div class="min-w-0">
			<div class="mb-3 flex items-baseline justify-between gap-2">
				<h3 class="text-lg font-bold">
					{sel.name}
					{#if league && sel.team_slug}
						<a class="ml-1 text-sm font-normal text-muted underline hover:text-fg" href={`${base}/${seasonId}/${compId}/${sel.team_slug}/`}>{sel.team}</a>
					{/if}
				</h3>
				<button class="text-xs text-muted hover:text-fg" onclick={() => (selected = null)}>bezár ✕</button>
			</div>
			<p class="mb-3 font-mono text-xs text-muted">
				{sel.position ? `poz. ${sel.position}` : ''}{sel.height_cm ? ` · ${sel.height_cm} cm` : ''} · {sel.gp} meccs ·
				{fmt(sel.mpg)} perc · {fmt(sel.poss_on, 0)} labdabirtoklás a pályán
			</p>
			<div class="mb-1 flex justify-between text-[10px] uppercase tracking-wider text-muted">
				<span>mutató</span>
				<span>percentilis ({mode === 'liga' ? 'liga' : GRP_LABEL[sel.pos_group ?? ''] ?? 'liga'})</span>
			</div>
			<div class="grid gap-1.5">
				{#each BARS as b (b.key)}
					{@const pc = pctOf(sel, b.key)}
					<div class="grid grid-cols-[8rem_1fr_3rem] items-center gap-2 text-xs">
						<span>{b.label} <span class="text-muted">{fmt(b.value(sel), b.digits ?? 1, b.key === 'onoff_nrtg' || b.key === 'pps_diff')}</span></span>
						<div class="relative h-2 overflow-hidden rounded bg-card-hover">
							{#if pc}
								<div class="absolute inset-y-0 left-0 rounded" class:bg-positive={pc.v >= 50} class:bg-negative={pc.v < 50} style:width="{pc.v}%"></div>
							{/if}
							<div class="absolute inset-y-[-2px] left-1/2 w-px bg-muted/70"></div>
						</div>
						<span class="text-right tabular-nums text-muted">{pc ? `${pc.v}.` : '—'}</span>
					</div>
				{/each}
			</div>
		</div>
		<div class="min-w-0">
			<h4 class="mb-2 text-sm font-semibold">Hatás a csapatra <span class="font-normal text-muted">/100 labdabirtoklás</span></h4>
			<div class="grid grid-cols-3 gap-2 text-center">
				<div class="rounded bg-card-hover p-2">
					<p class="text-xl font-bold tabular-nums" class:text-positive={(sel.on_nrtg ?? 0) >= 0} class:text-negative={(sel.on_nrtg ?? 0) < 0}>{fmt(sel.on_nrtg, 1, true)}</p>
					<p class="text-[10px] uppercase tracking-wider text-muted">pályán</p>
					<p class="text-[10px] text-muted tabular-nums">ORtg {fmt(sel.on_ortg)}</p>
					<p class="text-[10px] text-muted tabular-nums">DRtg {fmt(sel.on_drtg)}</p>
				</div>
				<div class="rounded bg-card-hover p-2">
					<p class="text-xl font-bold tabular-nums" class:text-positive={(sel.off_nrtg ?? 0) >= 0} class:text-negative={(sel.off_nrtg ?? 0) < 0}>{fmt(sel.off_nrtg, 1, true)}</p>
					<p class="text-[10px] uppercase tracking-wider text-muted">padon</p>
					<p class="text-[10px] text-muted tabular-nums">ORtg {fmt(sel.off_ortg)}</p>
					<p class="text-[10px] text-muted tabular-nums">DRtg {fmt(sel.off_drtg)}</p>
					<p class="text-[10px] text-muted">{fmt(sel.off_poss, 0)} poss</p>
				</div>
				<div class="rounded bg-card-hover p-2">
					<p class="text-xl font-bold tabular-nums" class:text-positive={(sel.onoff_nrtg ?? 0) >= 0} class:text-negative={(sel.onoff_nrtg ?? 0) < 0}>{fmt(sel.onoff_nrtg, 1, true)}</p>
					<p class="text-[10px] uppercase tracking-wider text-muted">különbség</p>
					<p class="text-[10px] text-muted tabular-nums">ORtg {fmt(diff(sel.on_ortg, sel.off_ortg), 1, true)}</p>
					<p class="text-[10px] text-muted tabular-nums">DRtg {fmt(diff(sel.on_drtg, sel.off_drtg), 1, true)}</p>
				</div>
			</div>
			<p class="mt-2 text-[11px] text-muted">ORtg = a csapat szerzett pontja, DRtg = a kapott pont, mindkettő 100 labdabirtoklásra. A DRtg-nél a kisebb a jobb, ezért ott a negatív különbség a kedvező.</p>
			{#if (sel.off_poss ?? 0) < minPoss}
				<p class="mt-2 text-xs text-muted">Keveset ült a padon ({fmt(sel.off_poss, 0)} labdabirtoklás), ezért a „padon” érték és a különbség bizonytalan.</p>
			{/if}
			<h4 class="mb-2 mt-4 text-sm font-semibold">100 labdabirtoklásra <span class="font-normal text-muted">amíg pályán van</span></h4>
			<div class="grid grid-cols-4 gap-2 text-center sm:grid-cols-7">
				{#each [['PTS', sel.pts_100], ['REB', sel.reb_100], ['AST', sel.ast_100], ['TOV', sel.tov_100], ['STL', sel.stl_100], ['BLK', sel.blk_100], ['FD', sel.fd_100]] as [l, v] (l)}
					<div class="rounded bg-card-hover p-2">
						<p class="text-[10px] uppercase tracking-wider text-muted">{l}</p>
						<p class="font-semibold tabular-nums">{fmt(v as number | null | undefined)}</p>
					</div>
				{/each}
			</div>

			<div class="mt-4 grid gap-4 sm:grid-cols-2">
				<div>
					<h4 class="mb-2 text-sm font-semibold">Gólpassz-kapcsolatok</h4>
					<p class="text-[10px] uppercase tracking-wider text-muted">neki passzol</p>
					{#each sel.ast_to ?? [] as [n, c] (n)}
						<p class="flex justify-between text-xs"><span class="truncate">{n}</span><span class="tabular-nums text-muted">{c}</span></p>
					{:else}<p class="text-xs text-muted">—</p>{/each}
					<p class="mt-2 text-[10px] uppercase tracking-wider text-muted">tőle kap · kosarai {fmt(sel.assisted_pct, 0)}%-a gólpasszból</p>
					{#each sel.ast_by ?? [] as [n, c] (n)}
						<p class="flex justify-between text-xs"><span class="truncate">{n}</span><span class="tabular-nums text-muted">{c}</span></p>
					{:else}<p class="text-xs text-muted">—</p>{/each}
				</div>
				<div>
					<h4 class="mb-2 text-sm font-semibold">Szoros végjáték</h4>
					<p class="mb-2 text-[11px] text-muted">utolsó 5 perc + hosszabbítás, legfeljebb 5 pontos különbségnél</p>
					{#if (sel.clutch_poss ?? 0) >= CLUTCH_MIN}
						<div class="grid grid-cols-3 gap-2 text-center">
							<div class="rounded bg-card-hover p-2"><p class="text-[10px] uppercase tracking-wider text-muted">pont</p><p class="font-semibold tabular-nums">{sel.clutch_pts ?? 0}</p></div>
							<div class="rounded bg-card-hover p-2"><p class="text-[10px] uppercase tracking-wider text-muted">TS%</p><p class="font-semibold tabular-nums">{fmt(sel.clutch_ts)}</p></div>
							<div class="rounded bg-card-hover p-2"><p class="text-[10px] uppercase tracking-wider text-muted">NRtg</p><p class="font-semibold tabular-nums" class:text-positive={(sel.clutch_nrtg ?? 0) >= 0} class:text-negative={(sel.clutch_nrtg ?? 0) < 0}>{fmt(sel.clutch_nrtg, 1, true)}</p></div>
						</div>
						<p class="mt-1 text-[11px] text-muted">{fmt(sel.clutch_poss, 0)} labdabirtoklás a pályán ilyen helyzetben</p>
					{:else}
						<p class="text-xs text-muted">Kevés szoros végjáték a pályán ({fmt(sel.clutch_poss ?? 0, 0)} labdabirtoklás, legalább {CLUTCH_MIN} kell).</p>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/snippet}

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
	Labdabirtoklás = FGA + 0,44·FTA + TOV − OREB, a cserék alapján a pályán töltött időre ·
	Percentilis: legalább {minGp} meccs; dobásmutatókhoz {minFga} mezőnydobás, a többihez {minPoss} labdabirtoklás a
	pályán — ez alatt nincs színezés („kicsi minta”) · ON–OFF: a szezon összes meccsének padon töltött idejéhez mérve ·
	Dobásminőség: lövéstérkép-zónák liga-átlaga alapján (büntetők nélkül) · Gólpassz-párosítás: a gólpassz a mellette álló
	csapattárs-kosárhoz kötve · Pozíción belüli percentilis csak ott, ahol legalább {data.thresholds.min_pos_pool ?? 8} összevethető játékos van ·
	A 3PA arány stílusmutató, nem kap színt.
</p>
