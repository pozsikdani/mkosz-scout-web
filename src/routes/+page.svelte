<script lang="ts">
	import { base } from '$app/paths';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const summaries = $derived(data.summaries);
</script>

<svelte:head>
	<title>MKOSZ Scout Report — NB1 B Piros</title>
</svelte:head>

<main class="mx-auto max-w-3xl px-6 py-12">
	<header class="mb-10 text-center">
		<p class="text-sm font-semibold tracking-widest text-accent uppercase">Scout Report</p>
		<h1 class="mt-2 text-4xl font-extrabold tracking-tight sm:text-5xl">NB1 B Piros</h1>
		<p class="mt-3 text-sm text-muted">Válassz szezont</p>
	</header>

	<ul class="grid gap-4 sm:grid-cols-2">
		{#each summaries as s (s.season.id)}
			<li>
				<a
					href={`${base}/${s.season.id}/`}
					class="group block rounded-xl border border-border bg-card p-6 transition hover:border-accent hover:bg-card-hover"
					class:border-accent={s.season.active}
				>
					<div class="flex items-start justify-between gap-3">
						<div>
							<p class="text-sm font-semibold uppercase tracking-wider text-muted">Szezon</p>
							<p class="mt-1 text-3xl font-extrabold tracking-tight">{s.season.displayName}</p>
						</div>
						<span
							class="rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
							class:bg-accent={s.season.active}
							class:text-fg={s.season.active}
							class:bg-border={!s.season.active}
							class:text-muted={!s.season.active}
						>
							{s.season.label}
						</span>
					</div>
					<p class="mt-4 text-sm text-muted">
						{s.teamCount > 0 ? `${s.teamCount} csapat` : 'Nincs adat'}
						{#if s.scrapedAt}
							· frissítve {new Date(s.scrapedAt).toLocaleDateString('hu-HU')}
						{/if}
					</p>
					<p
						class="mt-4 text-sm font-semibold text-accent transition group-hover:translate-x-0.5"
					>
						Megnyitás →
					</p>
				</a>
			</li>
		{/each}
	</ul>

	<p class="mt-10 text-center text-xs text-muted">
		Forrás: mkosz.hu · Statisztika: scoresheet + play-by-play · Deploy: GitHub Pages
	</p>
</main>
