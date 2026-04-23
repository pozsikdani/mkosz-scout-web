<script lang="ts">
	import { teamToSlug } from '$lib/slug';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const standings = $derived(data.standings);
</script>

<svelte:head>
	<title>Scout Report — {standings.display_name}</title>
</svelte:head>

<main class="mx-auto max-w-5xl px-6 py-10">
	<header class="mb-10">
		<p class="text-sm font-semibold tracking-widest text-accent uppercase">Scout Report</p>
		<h1 class="mt-1 text-4xl font-extrabold tracking-tight sm:text-5xl">
			{standings.display_name}
		</h1>
		<p class="mt-2 text-sm text-muted">
			{standings.season.replace('x', '').replace(/^(\d{2})(\d{2})$/, '20$1/20$2')} alapszakasz ·
			{standings.teams.length} csapat · frissítve
			{new Date(standings.scraped_at).toLocaleDateString('hu-HU')}
		</p>
	</header>

	<ul class="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card">
		{#each standings.teams as team (team.team)}
			{@const slug = teamToSlug(team.team)}
			{@const diff = team.scored - team.allowed}
			<li>
				<a
					href={`/hun2a/${slug}/`}
					class="flex items-center gap-4 px-5 py-4 transition hover:bg-card-hover"
				>
					<span class="w-8 text-right font-mono text-lg font-bold text-muted">
						{team.rank}.
					</span>
					<span class="flex-1 text-base font-semibold">{team.team}</span>
					<span class="font-mono text-sm">
						<span class="text-positive">{team.w}</span>
						<span class="text-muted">–</span>
						<span class="text-negative">{team.l}</span>
					</span>
					<span class="hidden w-20 text-right font-mono text-sm sm:inline-block"
						class:text-positive={diff > 0}
						class:text-negative={diff < 0}
						class:text-muted={diff === 0}
					>
						{diff > 0 ? '+' : ''}{diff}
					</span>
					<span class="text-muted">→</span>
				</a>
			</li>
		{/each}
	</ul>

	<p class="mt-6 text-xs text-muted">
		Forrás:
		<a href={standings.source_url} class="underline hover:text-accent" target="_blank" rel="noopener">
			mkosz.hu
		</a>
	</p>
</main>
