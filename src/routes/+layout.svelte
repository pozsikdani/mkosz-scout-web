<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { base } from '$app/paths';
	import { SEASONS } from '$lib/seasons';

	let { children } = $props();
	const archive = SEASONS.filter((s) => !s.active);
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>MKOSZ Scout Report</title>
</svelte:head>

<div class="flex min-h-screen flex-col bg-bg text-fg">
	<div class="flex-1">
		{@render children()}
	</div>
	<footer class="border-t border-border bg-card">
		<div class="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-6 py-4 text-xs text-muted">
			<a href={`${base}/`} class="font-semibold uppercase tracking-wider text-muted hover:text-accent">
				MKOSZ Scout
			</a>
			{#if archive.length > 0}
				<div class="flex flex-wrap items-center gap-2">
					<span class="uppercase tracking-wider">Előző szezonok:</span>
					{#each archive as s (s.id)}
						<a
							href={`${base}/${s.id}/`}
							class="rounded border border-border bg-card-hover px-2 py-1 font-mono text-[11px] text-muted transition hover:border-accent hover:text-accent"
						>
							{s.displayName}
						</a>
					{/each}
				</div>
			{/if}
		</div>
	</footer>
</div>
