<script lang="ts">
	import { base } from '$app/paths';
	import type { LineupMatch, TeamLineups } from '$lib/types';

	type PosCat = 'PG' | 'SG' | 'SF' | 'PF' | 'C';
	function posCategory(pos: string | undefined): PosCat | null {
		if (!pos) return null;
		const p = pos.replace(/\s/g, '');
		if (p === '1' || p === '1-2') return 'PG';
		if (p === '2' || p === '2-3') return 'SG';
		if (p === '3' || p === '3-4') return 'SF';
		if (p === '4' || p === '4-5') return 'PF';
		if (p === '5') return 'C';
		const digits = (p.match(/\d/g) ?? []).map(Number);
		if (!digits.length) return null;
		const hi = Math.max(...digits);
		return (['PG', 'SG', 'SF', 'PF', 'C'][hi - 1] ?? null) as PosCat | null;
	}
	const POS_CLS: Record<PosCat, string> = {
		PG: 'bg-blue-500/25 text-blue-300',
		SG: 'bg-emerald-500/25 text-emerald-300',
		SF: 'bg-orange-500/25 text-orange-300',
		PF: 'bg-red-500/25 text-red-300',
		C: 'bg-purple-500/25 text-purple-300'
	};

	type Props = {
		data: TeamLineups;
	};
	let { data }: Props = $props();

	const matches = $derived(data.matches);

	let selectedIdx = $state(0); // 0 = most recent
	const selected = $derived<LineupMatch | undefined>(matches[selectedIdx]);

	let scrubberEl = $state<HTMLElement | null>(null);
	$effect(() => {
		// Scroll to the right end on mount: with flex-row-reverse the latest
		// (selected) match sits at the right edge — start the scroll there so
		// the user sees the selected match without manual scrolling.
		if (scrubberEl) {
			scrubberEl.scrollLeft = scrubberEl.scrollWidth;
		}
	});

	function fmtDate(iso: string | null): string {
		if (!iso) return '—';
		const [y, m, d] = iso.split('-');
		return `${y}.${m}.${d}`;
	}

	function shortDate(iso: string | null): string {
		if (!iso) return '?';
		const [, m, d] = iso.split('-');
		return `${m}.${d}`;
	}

	function phaseLabel(phase: string): string {
		if (phase === 'alapszakasz') return 'Alap';
		if (phase === 'rajatszas_felso') return 'Rj-F';
		if (phase === 'rajatszas_also') return 'Rj-A';
		return phase;
	}
</script>

<div class="mb-4">
	<h2 class="text-xl font-bold tracking-tight">Kezdőötös és rotáció</h2>
	<p class="mt-1 text-xs text-muted">
		Per-meccs kezdőötös scoresheet alapján · csere-lánc PBP-ből · {data.match_count} meccs
	</p>
</div>

<!-- Match scrubber -->
<div bind:this={scrubberEl} class="mb-4 overflow-x-auto rounded-lg border border-border bg-card p-2">
	<div class="flex flex-row-reverse gap-1 min-w-max justify-end">
		{#each matches as m, i (m.gamecode)}
			{@const isSel = i === selectedIdx}
			<button
				type="button"
				onclick={() => (selectedIdx = i)}
				class="flex w-14 flex-col items-center rounded px-1 py-1.5 text-[10px] font-mono leading-tight transition shrink-0"
				class:bg-accent={isSel}
				class:text-fg={isSel}
				class:hover:bg-card-hover={!isSel}
				title={`${fmtDate(m.date)} ${m.home ? 'vs' : '@'} ${m.opponent} ${m.our_score}-${m.their_score}`}
			>
				<span class="text-[9px] opacity-70">{shortDate(m.date)}</span>
				<span class="truncate w-full text-center text-[10px]">
					{m.home ? '' : '@'}{m.opponent.split(' ')[0].slice(0, 6)}
				</span>
				<span class="font-bold">
					<span
						class:text-positive={m.result === 'W' && !isSel}
						class:text-negative={m.result === 'L' && !isSel}
					>
						{m.result}
					</span>
					{m.our_score}-{m.their_score}
				</span>
				{#if m.phase !== 'alapszakasz'}
					<span class="text-[8px] opacity-60">{phaseLabel(m.phase)}</span>
				{/if}
			</button>
		{/each}
	</div>
</div>

{#if selected}
	<!-- Selected match header -->
	<div class="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-4 py-3">
		<span class="font-mono text-sm text-muted">{fmtDate(selected.date)}</span>
		{#if selected.phase !== 'alapszakasz'}
			<span class="rounded bg-accent/20 px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-accent">
				{selected.phase === 'rajatszas_felso' ? 'Felső házi' : 'Alsó házi'}
			</span>
		{/if}
		<span class="flex-1 font-medium">
			{selected.home ? 'vs' : '@'}
			{selected.opponent}
		</span>
		<span class="font-mono text-lg">
			<span
				class:text-positive={selected.result === 'W'}
				class:text-negative={selected.result === 'L'}
			>
				{selected.our_score}
			</span>
			<span class="text-muted">–</span>
			<span class="text-muted">{selected.their_score}</span>
			<span
				class="ml-2 rounded px-2 py-0.5 text-sm font-bold"
				class:bg-positive={selected.result === 'W'}
				class:bg-negative={selected.result === 'L'}
				class:text-bg={true}
			>
				{selected.result}
			</span>
		</span>
	</div>

	<!-- Starting 5 cards -->
	<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
		{#each selected.starters as starter (starter.name)}
			{@const pc = posCategory(starter.position)}
			<div class="flex flex-col rounded-lg border border-border bg-card overflow-hidden">
				<!-- Name on top, photo + jersey below -->
				<div class="border-b border-border bg-card-hover px-3 py-2">
					<p class="mb-1.5 truncate text-sm font-semibold leading-snug" title={starter.name}>
						{starter.name}
					</p>
					<div class="flex items-center gap-2">
						{#if starter.photo_filename}
							<img
								src={`${base}/players/${starter.photo_filename}`}
								alt={starter.name}
								loading="lazy"
								class="h-12 w-12 shrink-0 rounded-lg object-cover"
							/>
						{:else}
							<div
								class="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-card text-muted"
								title="Nincs fotó"
								aria-label="Nincs fotó"
							>
								<svg viewBox="0 0 24 24" class="h-6 w-6" fill="currentColor" aria-hidden="true">
									<path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0 2c-4.42 0-8 2.69-8 6v2h16v-2c0-3.31-3.58-6-8-6Z" />
								</svg>
							</div>
						{/if}
						<div class="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-accent font-mono text-base font-bold text-fg">
							{starter.jersey != null ? `#${starter.jersey}` : '—'}
						</div>
						<div class="ml-auto flex flex-col items-end gap-0.5">
							{#if pc}
								<span class="rounded px-1 py-px font-mono text-[9px] font-bold {POS_CLS[pc]}">{pc}</span>
							{/if}
							<span class="font-mono text-[10px] text-muted">{starter.minutes} perc</span>
						</div>
					</div>
				</div>

				<!-- Mini box: PTS / REB / AST -->
				<div class="grid grid-cols-3 gap-px bg-border text-center">
					<div class="bg-card px-2 py-2">
						<p class="text-[9px] font-semibold uppercase tracking-wider text-muted">PTS</p>
						<p class="font-mono text-base font-bold leading-tight">{starter.points}</p>
					</div>
					<div class="bg-card px-2 py-2">
						<p class="text-[9px] font-semibold uppercase tracking-wider text-muted">REB</p>
						<p class="font-mono text-base font-bold leading-tight">{starter.reb}</p>
					</div>
					<div class="bg-card px-2 py-2">
						<p class="text-[9px] font-semibold uppercase tracking-wider text-muted">AST</p>
						<p class="font-mono text-base font-bold leading-tight">{starter.ast}</p>
					</div>
				</div>

				<!-- Sub chain -->
				<div class="flex-1 px-3 py-2.5">
					<p class="mb-1.5 text-[9px] font-semibold uppercase tracking-wider text-muted">
						Cserék
					</p>
					{#if !selected.has_subs}
						<p class="text-xs text-muted italic">PBP nem elérhető</p>
					{:else if starter.subs.length === 0}
						<p class="text-xs text-muted">Nem cserélték le</p>
					{:else}
						<ul class="space-y-1">
							{#each starter.subs as sub (sub.name)}
								<li class="flex items-center gap-1.5 text-xs">
									{#if sub.photo_filename}
										<img
											src={`${base}/players/${sub.photo_filename}`}
											alt={sub.name}
											loading="lazy"
											class="h-6 w-6 shrink-0 rounded object-cover"
										/>
									{:else}
										<div
											class="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-card text-muted"
											aria-label="Nincs fotó"
										>
											<svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="currentColor" aria-hidden="true">
												<path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0 2c-4.42 0-8 2.69-8 6v2h16v-2c0-3.31-3.58-6-8-6Z" />
											</svg>
										</div>
									{/if}
									<span class="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-border font-mono text-[10px] font-bold text-muted">
										{sub.jersey != null ? `#${sub.jersey}` : '?'}
									</span>
									<span class="truncate flex-1" title={sub.name}>{sub.name}</span>
									<span class="font-mono text-[10px] text-muted">{sub.minutes}p</span>
									<span class="font-mono text-muted">{sub.count}×</span>
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			</div>
		{/each}
	</div>
{/if}

<p class="mt-4 text-xs text-muted">
	Forrás: scoresheet (kezdőötös, box stat) + PBP (cserék) · csere-lánc = a kezdő helyére beálló játékosok
	az adott meccsen
</p>
