<script lang="ts">
	import { base } from '$app/paths';
	import type { MatchPhase, MatchRow } from '$lib/types';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const team = $derived(data.team);
	const standings = $derived(data.standings);
	const allMatches = $derived(data.matches?.matches ?? []);

	const gp = $derived(team.gp || 0);
	const diff = $derived(team.scored - team.allowed);
	const ppg = $derived(gp > 0 ? team.scored / gp : 0);
	const oppg = $derived(gp > 0 ? team.allowed / gp : 0);
	const margin = $derived(ppg - oppg);

	type PhaseFilter = 'all' | 'alapszakasz' | 'rajatszas';
	let phaseFilter = $state<PhaseFilter>('all');

	const playedMatches = $derived(
		allMatches.filter((m) => m.result !== null).sort((a, b) => (b.date ?? '').localeCompare(a.date ?? ''))
	);

	const filteredMatches = $derived(
		phaseFilter === 'all'
			? playedMatches
			: phaseFilter === 'alapszakasz'
				? playedMatches.filter((m) => m.phase === 'alapszakasz')
				: playedMatches.filter((m) => m.phase !== 'alapszakasz')
	);

	const shownMatches = $derived(filteredMatches.slice(0, 10));

	const phaseCounts = $derived({
		all: playedMatches.length,
		alapszakasz: playedMatches.filter((m) => m.phase === 'alapszakasz').length,
		rajatszas: playedMatches.filter((m) => m.phase !== 'alapszakasz').length
	});

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

	<header class="mb-10 border-b border-border pb-6">
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
					<span class:text-positive={team.streak.startsWith('W')} class:text-negative={team.streak.startsWith('L')}>
						{team.streak}
					</span>
				</span>
			{/if}
		</div>
	</header>

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
							class="rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wider {phaseChipClass(match.phase)}"
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

			{#if filteredMatches.length > shownMatches.length}
				<p class="mt-3 text-center text-xs text-muted">
					{shownMatches.length} / {filteredMatches.length} meccs (legfrissebb)
				</p>
			{/if}
		</section>
	{/if}

	<p class="mt-8 text-xs text-muted">
		Tabella forrása:
		<a href={standings.source_url} class="underline hover:text-accent" target="_blank" rel="noopener">
			mkosz.hu
		</a>{#if playedMatches.length > 0}
			· Meccsek forrása: mkosz-stats DB{/if}
	</p>
</main>
