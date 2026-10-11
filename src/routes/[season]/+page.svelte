<script lang="ts">
	import { base } from '$app/paths';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const season = $derived(data.season);
	const summaries = $derived(data.summaries);
	const archive = $derived(!season.active);
</script>

<svelte:head>
	<title>{season.displayName} — bajnokság-választó</title>
</svelte:head>

<main class="mx-auto max-w-3xl px-6 py-12">
	<nav class="mb-8">
		<a
			href={`${base}/`}
			class="inline-flex items-center gap-2 text-sm text-muted transition hover:text-accent"
		>
			<span>←</span> Szezon-választó
		</a>
	</nav>

	<header class="mb-10 text-center">
		<p class="text-sm font-semibold tracking-widest text-accent uppercase">Scout Report</p>
		<h1 class="mt-2 text-4xl font-extrabold tracking-tight sm:text-5xl">
			{season.displayName}
			{#if archive}
				<span class="ml-2 rounded border border-border px-2 py-0.5 align-middle text-xs font-semibold uppercase tracking-wider text-muted">
					Archív
				</span>
			{/if}
		</h1>
		<p class="mt-3 text-sm text-muted">Válassz bajnokságot</p>
	</header>

	<ul class="grid gap-4 sm:grid-cols-2">
		{#each summaries as s (s.comp.id)}
			{@const empty = s.teamCount === 0}
			<li>
				<a
					href={empty ? undefined : `${base}/${season.id}/${s.comp.id}/`}
					aria-disabled={empty}
					class="group block rounded-xl border border-border bg-card p-6 transition"
					class:hover:border-accent={!empty}
					class:hover:bg-card-hover={!empty}
					class:opacity-50={empty}
					class:cursor-not-allowed={empty}
					class:pointer-events-none={empty}
				>
					<div class="flex items-start justify-between gap-3">
						<div>
							<p class="text-sm font-semibold uppercase tracking-wider {s.comp.accentClass}">
								{s.comp.shortName}
							</p>
							<p class="mt-1 text-3xl font-extrabold tracking-tight">{s.comp.displayName}</p>
						</div>
					</div>
					<p class="mt-4 text-sm text-muted">
						{s.teamCount > 0 ? `${s.teamCount} csapat` : 'Nincs adat ehhez a szezonhoz'}
						{#if s.scrapedAt}
							· frissítve {new Date(s.scrapedAt).toLocaleDateString('hu-HU')}
						{/if}
					</p>
					{#if !empty}
						<p class="mt-4 text-sm font-semibold text-accent transition group-hover:translate-x-0.5">
							Megnyitás →
						</p>
					{/if}
				</a>
			</li>
		{/each}
	</ul>
</main>
