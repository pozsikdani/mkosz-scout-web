<script lang="ts">
	import { base } from '$app/paths';
	import LineupNRtg from '$lib/components/LineupNRtg.svelte';
	import PlayerCards from '$lib/components/PlayerCards.svelte';
	import PossessionBreakdown from '$lib/components/PossessionBreakdown.svelte';
	import Shotchart from '$lib/components/Shotchart.svelte';
	import ShotchartZones from '$lib/components/ShotchartZones.svelte';
	import StartingFive from '$lib/components/StartingFive.svelte';
	import type { MatchRow } from '$lib/types';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const team = $derived(data.team);
	const standings = $derived(data.standings);
	const allMatches = $derived(data.matches?.matches ?? []);
	const shotData = $derived(data.shots);
	const playersData = $derived(data.players);
	const hasPlayers = $derived((playersData?.players?.length ?? 0) > 0);
	const lineupsData = $derived(data.lineups);
	const hasLineups = $derived((lineupsData?.matches?.length ?? 0) > 0);
	const possessionsData = $derived(data.possessions);
	const lineupNRtgData = $derived(data.lineupNRtg);
	const hasLineupNRtg = $derived((lineupNRtgData?.matches?.length ?? 0) > 0);

	const gp = $derived(team.gp || 0);
	const diff = $derived(team.scored - team.allowed);
	const ppg = $derived(gp > 0 ? team.scored / gp : 0);
	const oppg = $derived(gp > 0 ? team.allowed / gp : 0);
	const margin = $derived(ppg - oppg);

	type Tab = 'info' | 'lineups' | 'lineup-nrtg' | 'players' | 'shotchart';
	let activeTab = $state<Tab>('info');

	type PhaseFilter = 'all' | 'alapszakasz' | 'rajatszas';
	let phaseFilter = $state<PhaseFilter>('all');
	let expanded = $state(false);

	const playedMatches = $derived(
		allMatches
			.filter((m) => m.result !== null)
			.sort((a, b) => (b.date ?? '').localeCompare(a.date ?? ''))
	);

	const filteredMatches = $derived(
		phaseFilter === 'all'
			? playedMatches
			: phaseFilter === 'alapszakasz'
				? playedMatches.filter((m) => m.phase === 'alapszakasz')
				: playedMatches.filter((m) => m.phase !== 'alapszakasz')
	);

	const shownMatches = $derived(expanded ? filteredMatches : filteredMatches.slice(0, 10));

	const phaseCounts = $derived({
		all: playedMatches.length,
		alapszakasz: playedMatches.filter((m) => m.phase === 'alapszakasz').length,
		rajatszas: playedMatches.filter((m) => m.phase !== 'alapszakasz').length
	});

	// Shotchart state — multi-select set of gamecodes
	const shotMatches = $derived(
		(shotData?.matches ?? []).slice().sort((a, b) => (b.date ?? '').localeCompare(a.date ?? ''))
	);
	const hasShots = $derived(shotMatches.length > 0);
	const selectableMatches = $derived(shotMatches.filter((m) => m.has_shotchart));
	const selectableGamecodes = $derived(selectableMatches.map((m) => m.gamecode));
	const missingCount = $derived(shotMatches.length - selectableMatches.length);

	let selectedSet = $state<Set<string>>(new Set());
	let selectorOpen = $state(false);
	let initialized = $state(false);

	// Initialize selection to "all SELECTABLE" once on first data load
	$effect(() => {
		if (hasShots && !initialized) {
			selectedSet = new Set(selectableGamecodes);
			initialized = true;
		}
	});

	const selectedMatches = $derived(shotMatches.filter((m) => selectedSet.has(m.gamecode)));
	const selectedShots = $derived(selectedMatches.flatMap((m) => m.shots));
	const selectedCount = $derived(selectedSet.size);
	const isAllSelected = $derived(selectedCount === selectableMatches.length);
	const selectedMatchMeta = $derived(selectedCount === 1 ? selectedMatches[0] : null);

	function toggleMatch(m: (typeof shotMatches)[number]) {
		if (!m.has_shotchart) return;
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

	function selectOnlyAlapszakasz() {
		selectedSet = new Set(
			selectableMatches.filter((m) => m.phase === 'alapszakasz').map((m) => m.gamecode)
		);
	}

	function selectOnlyRajatszas() {
		selectedSet = new Set(
			selectableMatches.filter((m) => m.phase !== 'alapszakasz').map((m) => m.gamecode)
		);
	}

	function selectOnlyHome() {
		selectedSet = new Set(selectableMatches.filter((m) => m.home).map((m) => m.gamecode));
	}

	function selectOnlyAway() {
		selectedSet = new Set(selectableMatches.filter((m) => !m.home).map((m) => m.gamecode));
	}

	function selectOnlyWon() {
		selectedSet = new Set(
			selectableMatches.filter((m) => m.result === 'W').map((m) => m.gamecode)
		);
	}

	function selectOnlyLost() {
		selectedSet = new Set(
			selectableMatches.filter((m) => m.result === 'L').map((m) => m.gamecode)
		);
	}

	const hasPlayoffShots = $derived(selectableMatches.some((m) => m.phase !== 'alapszakasz'));
	const homeCount = $derived(selectableMatches.filter((m) => m.home).length);
	const awayCount = $derived(selectableMatches.filter((m) => !m.home).length);
	const wonCount = $derived(selectableMatches.filter((m) => m.result === 'W').length);
	const lostCount = $derived(selectableMatches.filter((m) => m.result === 'L').length);
	const shotAlapCount = $derived(
		selectableMatches.filter((m) => m.phase === 'alapszakasz').length
	);
	const shotRajatszasCount = $derived(
		selectableMatches.filter((m) => m.phase !== 'alapszakasz').length
	);

	function fmt(n: number, digits = 1): string {
		return n.toLocaleString('hu-HU', {
			minimumFractionDigits: digits,
			maximumFractionDigits: digits
		});
	}

	function fmtDate(iso: string | null): string {
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

</script>

<svelte:head>
	<title>{team.team} — {standings.display_name}</title>
</svelte:head>

<main class="mx-auto max-w-5xl px-6 py-10">
	<nav class="mb-8">
		<a
			href={`${base}/`}
			class="inline-flex items-center gap-2 text-sm text-muted transition hover:text-accent"
		>
			<span>←</span> Vissza a tabellához
		</a>
	</nav>

	<header class="mb-6 border-b border-border pb-6">
		<p class="text-sm font-semibold tracking-widest text-accent uppercase">
			{standings.display_name}
		</p>
		<h1 class="mt-1 text-4xl font-extrabold tracking-tight sm:text-5xl">{team.team}</h1>
		<div class="mt-3 flex flex-wrap items-baseline gap-x-6 gap-y-1 font-mono text-sm">
			<span class="text-2xl font-bold">#{team.rank}</span>
			<span>
				<span class="text-positive text-xl font-bold">{team.w}</span>
				<span class="text-muted">–</span>
				<span class="text-negative text-xl font-bold">{team.l}</span>
				<span class="text-muted">({team.gp} meccs)</span>
			</span>
			{#if team.streak}
				<span class="text-muted">
					Sorozat:
					<span
						class:text-positive={team.streak.startsWith('W')}
						class:text-negative={team.streak.startsWith('L')}
					>
						{team.streak}
					</span>
				</span>
			{/if}
		</div>
	</header>

	<div class="mb-6 flex gap-1 rounded-lg border border-border bg-card p-1 text-sm font-semibold w-fit">
		<button
			type="button"
			onclick={() => (activeTab = 'info')}
			class="rounded px-4 py-2 transition"
			class:bg-accent={activeTab === 'info'}
			class:text-fg={activeTab === 'info'}
			class:text-muted={activeTab !== 'info'}
		>
			Alapadatok
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'lineups')}
			class="rounded px-4 py-2 transition"
			class:bg-accent={activeTab === 'lineups'}
			class:text-fg={activeTab === 'lineups'}
			class:text-muted={activeTab !== 'lineups'}
			disabled={!hasLineups}
		>
			Kezdőötös
			{#if !hasLineups}<span class="ml-1 text-xs opacity-60">(nincs adat)</span>{/if}
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'lineup-nrtg')}
			class="rounded px-4 py-2 transition"
			class:bg-accent={activeTab === 'lineup-nrtg'}
			class:text-fg={activeTab === 'lineup-nrtg'}
			class:text-muted={activeTab !== 'lineup-nrtg'}
			disabled={!hasLineupNRtg}
		>
			Lineup NRTG
			{#if !hasLineupNRtg}<span class="ml-1 text-xs opacity-60">(nincs adat)</span>{/if}
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'players')}
			class="rounded px-4 py-2 transition"
			class:bg-accent={activeTab === 'players'}
			class:text-fg={activeTab === 'players'}
			class:text-muted={activeTab !== 'players'}
			disabled={!hasPlayers}
		>
			Játékosok
			{#if !hasPlayers}<span class="ml-1 text-xs opacity-60">(nincs adat)</span>{/if}
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'shotchart')}
			class="rounded px-4 py-2 transition"
			class:bg-accent={activeTab === 'shotchart'}
			class:text-fg={activeTab === 'shotchart'}
			class:text-muted={activeTab !== 'shotchart'}
			disabled={!hasShots}
		>
			Shotchart
			{#if !hasShots}<span class="ml-1 text-xs opacity-60">(nincs adat)</span>{/if}
		</button>
	</div>

	{#if activeTab === 'info'}
		<section class="grid grid-cols-2 gap-4 sm:grid-cols-4">
			<div class="rounded-lg border border-border bg-card p-4">
				<p class="text-xs font-semibold tracking-wider text-muted uppercase">Helyezés</p>
				<p class="mt-2 text-3xl font-bold">#{team.rank}</p>
			</div>
			<div class="rounded-lg border border-border bg-card p-4">
				<p class="text-xs font-semibold tracking-wider text-muted uppercase">Mérleg</p>
				<p class="mt-2 font-mono text-3xl font-bold">
					<span class="text-positive">{team.w}</span>
					<span class="text-muted">–</span>
					<span class="text-negative">{team.l}</span>
				</p>
			</div>
			<div class="rounded-lg border border-border bg-card p-4">
				<p class="text-xs font-semibold tracking-wider text-muted uppercase">Dobott</p>
				<p class="mt-2 font-mono text-3xl font-bold">{team.scored}</p>
			</div>
			<div class="rounded-lg border border-border bg-card p-4">
				<p class="text-xs font-semibold tracking-wider text-muted uppercase">Kapott</p>
				<p class="mt-2 font-mono text-3xl font-bold">{team.allowed}</p>
			</div>

			<div class="col-span-2 rounded-lg border border-border bg-card p-4 sm:col-span-1">
				<p class="text-xs font-semibold tracking-wider text-muted uppercase">Pontkülönbség</p>
				<p
					class="mt-2 font-mono text-3xl font-bold"
					class:text-positive={diff > 0}
					class:text-negative={diff < 0}
				>
					{diff > 0 ? '+' : ''}{diff}
				</p>
			</div>
			<div class="rounded-lg border border-border bg-card p-4">
				<p class="text-xs font-semibold tracking-wider text-muted uppercase">PPG</p>
				<p class="mt-2 font-mono text-3xl font-bold">{fmt(ppg)}</p>
			</div>
			<div class="rounded-lg border border-border bg-card p-4">
				<p class="text-xs font-semibold tracking-wider text-muted uppercase">OPPG</p>
				<p class="mt-2 font-mono text-3xl font-bold">{fmt(oppg)}</p>
			</div>
			<div class="rounded-lg border border-border bg-card p-4">
				<p class="text-xs font-semibold tracking-wider text-muted uppercase">Margin/g</p>
				<p
					class="mt-2 font-mono text-3xl font-bold"
					class:text-positive={margin > 0}
					class:text-negative={margin < 0}
				>
					{margin > 0 ? '+' : ''}{fmt(margin)}
				</p>
			</div>
		</section>

		<section class="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
			<div class="rounded-lg border border-border bg-card p-4">
				<p class="text-xs font-semibold tracking-wider text-muted uppercase">Hazai</p>
				<p class="mt-2 font-mono text-xl font-bold">{team.home || '—'}</p>
			</div>
			<div class="rounded-lg border border-border bg-card p-4">
				<p class="text-xs font-semibold tracking-wider text-muted uppercase">Idegen</p>
				<p class="mt-2 font-mono text-xl font-bold">{team.away || '—'}</p>
			</div>
			<div class="rounded-lg border border-border bg-card p-4">
				<p class="text-xs font-semibold tracking-wider text-muted uppercase">Utolsó 5</p>
				<p class="mt-2 font-mono text-xl font-bold">{team.last5 || '—'}</p>
			</div>
		</section>

		{#if playedMatches.length > 0}
			<section class="mt-10">
				<div class="mb-4 flex flex-wrap items-center justify-between gap-3">
					<h2 class="text-xl font-bold tracking-tight">Utolsó meccsek</h2>
					<div class="flex gap-1 rounded-lg border border-border bg-card p-1 text-xs font-semibold">
						<button
							type="button"
							onclick={() => (phaseFilter = 'all')}
							class="rounded px-3 py-1.5 transition"
							class:bg-accent={phaseFilter === 'all'}
							class:text-fg={phaseFilter === 'all'}
							class:text-muted={phaseFilter !== 'all'}
						>
							Összes <span class="ml-1 opacity-60">{phaseCounts.all}</span>
						</button>
						<button
							type="button"
							onclick={() => (phaseFilter = 'alapszakasz')}
							class="rounded px-3 py-1.5 transition"
							class:bg-accent={phaseFilter === 'alapszakasz'}
							class:text-fg={phaseFilter === 'alapszakasz'}
							class:text-muted={phaseFilter !== 'alapszakasz'}
						>
							Alapszakasz <span class="ml-1 opacity-60">{phaseCounts.alapszakasz}</span>
						</button>
						<button
							type="button"
							onclick={() => (phaseFilter = 'rajatszas')}
							class="rounded px-3 py-1.5 transition"
							class:bg-accent={phaseFilter === 'rajatszas'}
							class:text-fg={phaseFilter === 'rajatszas'}
							class:text-muted={phaseFilter !== 'rajatszas'}
							disabled={phaseCounts.rajatszas === 0}
						>
							Rájátszás <span class="ml-1 opacity-60">{phaseCounts.rajatszas}</span>
						</button>
					</div>
				</div>

				<ul class="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card">
					{#each shownMatches as match (match.gamecode)}
						<li class="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
							<span class="w-20 font-mono text-xs text-muted">{fmtDate(match.date)}</span>
							<span
								class="rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wider {phaseChipClass(
									match.phase
								)}"
							>
								{phaseLabel(match.phase)}
							</span>
							<span
								class="w-6 text-center font-mono text-xs"
								class:text-muted={match.home}
								class:text-accent={!match.home}
								title={match.home ? 'Hazai' : 'Idegen'}
							>
								{match.home ? 'H' : '@'}
							</span>
							<span class="flex-1 font-medium">{match.opponent}</span>
							<span class="font-mono text-sm">
								<span
									class:text-positive={match.result === 'W'}
									class:text-negative={match.result === 'L'}
								>
									{match.our_score}
								</span>
								<span class="text-muted">–</span>
								<span class="text-muted">{match.their_score}</span>
							</span>
							<span
								class="w-6 rounded px-1.5 py-0.5 text-center font-mono text-xs font-bold"
								class:bg-positive={match.result === 'W'}
								class:bg-negative={match.result === 'L'}
								class:text-bg={match.result !== null}
							>
								{match.result ?? '—'}
							</span>
						</li>
					{/each}
				</ul>

				{#if filteredMatches.length > 10}
					<div class="mt-3 text-center">
						<button
							type="button"
							onclick={() => (expanded = !expanded)}
							class="inline-flex items-center gap-2 rounded border border-border bg-card px-4 py-1.5 text-xs font-semibold text-muted transition hover:bg-card-hover hover:text-fg"
						>
							{#if expanded}
								Kevesebb mutatása <span aria-hidden="true">▲</span>
							{:else}
								Összes megjelenítése ({filteredMatches.length}) <span aria-hidden="true">▼</span>
							{/if}
						</button>
					</div>
				{/if}
			</section>
		{/if}

		<p class="mt-8 text-xs text-muted">
			Tabella forrása:
			<a
				href={standings.source_url}
				class="underline hover:text-accent"
				target="_blank"
				rel="noopener">mkosz.hu</a
			>{#if playedMatches.length > 0}
				· Meccsek forrása: mkosz-stats DB{/if}
		</p>
	{:else if activeTab === 'lineups'}
		<section>
			{#if !lineupsData || lineupsData.matches.length === 0}
				<div class="rounded-lg border border-border bg-card p-6 text-sm text-muted">
					Ehhez a csapathoz még nincs kezdőötös adat.
				</div>
			{:else}
				<StartingFive data={lineupsData} />
			{/if}
		</section>
	{:else if activeTab === 'lineup-nrtg'}
		<section>
			{#if !lineupNRtgData || lineupNRtgData.matches.length === 0}
				<div class="rounded-lg border border-border bg-card p-6 text-sm text-muted">
					Ehhez a csapathoz még nincs PBP-alapú lineup adat.
				</div>
			{:else}
				<LineupNRtg data={lineupNRtgData} />
			{/if}
		</section>
	{:else if activeTab === 'players'}
		<section>
			{#if !playersData || playersData.players.length === 0}
				<div class="rounded-lg border border-border bg-card p-6 text-sm text-muted">
					Ehhez a csapathoz még nincs játékos-statisztika az adatbázisban.
				</div>
			{:else}
				<PlayerCards data={playersData} />
			{/if}
		</section>
	{:else if activeTab === 'shotchart'}
		<section>
			{#if !hasShots}
				<div class="rounded-lg border border-border bg-card p-6 text-sm text-muted">
					Ehhez a csapathoz még nincs shotchart adat az adatbázisban.
				</div>
			{:else}
				<div class="mb-4 flex flex-wrap items-center justify-between gap-3">
					<div>
						<h2 class="text-xl font-bold tracking-tight">Shotchart</h2>
						<p class="text-xs text-muted mt-1">
							{selectableMatches.length} meccs shotchart-tal
							{#if missingCount > 0}<span class="text-negative">
									· {missingCount} meccs adat nélkül</span
								>{/if}
							· {shotData?.total_shots} lövés · FG%
							{(
								(100 * (shotData?.total_made ?? 0)) / Math.max(1, shotData?.total_shots ?? 1)
							).toFixed(1)}
						</p>
					</div>
					<button
						type="button"
						onclick={() => (selectorOpen = !selectorOpen)}
						class="inline-flex items-center gap-2 rounded border border-border bg-card px-3 py-2 text-sm font-semibold transition hover:bg-card-hover"
					>
						<span>
							{selectedCount}
							<span class="text-muted">/ {selectableMatches.length} meccs</span>
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
								onclick={selectOnlyAlapszakasz}
								class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
							>
								Csak alapszakasz <span class="opacity-60">{shotAlapCount}</span>
							</button>
							{#if hasPlayoffShots}
								<button
									type="button"
									onclick={selectOnlyRajatszas}
									class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
								>
									Csak rájátszás <span class="opacity-60">{shotRajatszasCount}</span>
								</button>
							{/if}
							<span class="text-muted">|</span>
							<button
								type="button"
								onclick={selectOnlyHome}
								class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
								disabled={homeCount === 0}
							>
								Csak hazai <span class="opacity-60">{homeCount}</span>
							</button>
							<button
								type="button"
								onclick={selectOnlyAway}
								class="rounded border border-border px-2.5 py-1 font-semibold hover:bg-card-hover"
								disabled={awayCount === 0}
							>
								Csak vendég <span class="opacity-60">{awayCount}</span>
							</button>
							<span class="text-muted">|</span>
							<button
								type="button"
								onclick={selectOnlyWon}
								class="rounded border border-border px-2.5 py-1 font-semibold text-positive hover:bg-card-hover"
								disabled={wonCount === 0}
							>
								Csak nyert <span class="opacity-60">{wonCount}</span>
							</button>
							<button
								type="button"
								onclick={selectOnlyLost}
								class="rounded border border-border px-2.5 py-1 font-semibold text-negative hover:bg-card-hover"
								disabled={lostCount === 0}
							>
								Csak vesztett <span class="opacity-60">{lostCount}</span>
							</button>
						</div>
						<ul class="max-h-96 divide-y divide-border overflow-y-auto">
							{#each shotMatches as m (m.gamecode)}
								{@const checked = selectedSet.has(m.gamecode)}
								{@const disabled = !m.has_shotchart}
								<li>
									<label
										class="flex flex-wrap items-center gap-3 px-4 py-2 text-sm"
										class:cursor-pointer={!disabled}
										class:hover:bg-card-hover={!disabled}
										class:opacity-40={disabled}
										class:cursor-not-allowed={disabled}
										title={disabled ? 'Nincs shotchart adat ehhez a meccshez' : ''}
									>
										<input
											type="checkbox"
											{checked}
											{disabled}
											onchange={() => toggleMatch(m)}
											class="h-4 w-4 accent-accent"
										/>
										<span class="w-20 font-mono text-xs text-muted">{fmtDate(m.date)}</span>
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
										<span class="w-10 text-right font-mono text-xs text-muted">
											{#if disabled}—{:else}{m.shots.length}{/if}
										</span>
									</label>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				{#if selectedMatchMeta}
					<div class="mb-3 flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-4 py-2 text-sm">
						<span class="font-mono text-xs text-muted">{fmtDate(selectedMatchMeta.date)}</span>
						<span
							class="rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wider {phaseChipClass(
								selectedMatchMeta.phase
							)}"
						>
							{phaseLabel(selectedMatchMeta.phase)}
						</span>
						<span class="flex-1 font-medium">
							{selectedMatchMeta.home ? 'vs' : '@'}
							{selectedMatchMeta.opponent}
						</span>
						{#if selectedMatchMeta.result}
							<span class="font-mono">
								<span
									class:text-positive={selectedMatchMeta.result === 'W'}
									class:text-negative={selectedMatchMeta.result === 'L'}
								>
									{selectedMatchMeta.our_score}
								</span>
								<span class="text-muted">–</span>
								<span class="text-muted">{selectedMatchMeta.their_score}</span>
							</span>
						{/if}
					</div>
				{:else if selectedCount > 1 && !isAllSelected}
					<p class="mb-3 text-xs text-muted">
						{selectedCount} meccs kiválasztva — {selectedShots.length} lövés összesítve
					</p>
				{/if}

				{#if selectedCount === 0}
					<div class="rounded-lg border border-border bg-card p-6 text-center text-sm text-muted">
						Válassz meccs(ek)et a shotchart megjelenítéséhez.
					</div>
				{:else}
					<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
						<div>
							<p class="mb-2 text-xs font-semibold tracking-wider text-muted uppercase">
								Dobás-eloszlás
							</p>
							<Shotchart shots={selectedShots} />
						</div>
						<div>
							<p class="mb-2 text-xs font-semibold tracking-wider text-muted uppercase">
								Zónák szerint
							</p>
							<ShotchartZones shots={selectedShots} />
						</div>
					</div>
				{/if}

				<p class="mt-6 text-xs text-muted">
					Forrás: mkosz.hu shotchart API · csak mezőnyből dobott lövések (büntetők kihagyva)
				</p>

				{#if possessionsData}
					<div class="mt-8">
						<PossessionBreakdown
							data={possessionsData}
							selectedGamecodes={selectedSet}
							teamLabel={team.team}
						/>
					</div>
				{/if}
			{/if}
		</section>
	{/if}
</main>
