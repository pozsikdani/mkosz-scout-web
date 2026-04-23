<script lang="ts">
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const team = $derived(data.team);
	const standings = $derived(data.standings);

	const gp = $derived(team.gp || 0);
	const diff = $derived(team.scored - team.allowed);
	const ppg = $derived(gp > 0 ? team.scored / gp : 0);
	const oppg = $derived(gp > 0 ? team.allowed / gp : 0);
	const margin = $derived(ppg - oppg);

	function fmt(n: number, digits = 1): string {
		return n.toLocaleString('hu-HU', {
			minimumFractionDigits: digits,
			maximumFractionDigits: digits
		});
	}
</script>

<svelte:head>
	<title>{team.team} — {standings.display_name}</title>
</svelte:head>

<main class="mx-auto max-w-5xl px-6 py-10">
	<nav class="mb-8">
		<a
			href="/"
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

	<p class="mt-8 text-xs text-muted">
		Forrás:
		<a href={standings.source_url} class="underline hover:text-accent" target="_blank" rel="noopener">
			mkosz.hu
		</a>
	</p>
</main>
