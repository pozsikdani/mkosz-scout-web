<script lang="ts">
	import { base } from '$app/paths';
	import PlayerEfficiency from '$lib/components/PlayerEfficiency.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const season = $derived(data.season);
	const comp = $derived(data.comp);
</script>

<svelte:head>
	<title>Játékos-ranglista — {comp.displayName} {season.displayName}</title>
</svelte:head>

<main class="mx-auto max-w-7xl px-4 py-10 sm:px-6">
	<nav class="mb-8">
		<a
			href={`${base}/${season.id}/${comp.id}/`}
			class="inline-flex items-center gap-2 text-sm text-muted transition hover:text-accent"
		>
			<span>←</span> Vissza a tabellához
		</a>
	</nav>
	<header class="mb-6">
		<p class="text-sm font-semibold tracking-widest {comp.accentClass} uppercase">{comp.displayName}</p>
		<h1 class="mt-1 text-3xl font-extrabold tracking-tight sm:text-4xl">{season.displayName}</h1>
		<p class="mt-2 text-sm text-muted">
			A liga összes játékosa · {data.players.players.length} játékos · rendezhető, kereshető
		</p>
	</header>
	<PlayerEfficiency data={data.players} league seasonId={season.id} compId={comp.id} />
</main>
