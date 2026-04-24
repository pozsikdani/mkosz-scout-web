<script lang="ts">
	interface Shot {
		x: number; // hx 0-100
		y: number; // hy 0-100
		made: number | boolean;
	}

	let {
		shots = [],
		width = 520,
		showDots = true
	}: { shots?: Shot[]; width?: number; showDots?: boolean } = $props();

	const height = $derived(Math.round(width * 0.94));
	const W = $derived(width);
	const H = $derived(height);

	function toX(hx: number) {
		return (hx / 100) * W;
	}
	function toY(hy: number) {
		return H - (hy / 100) * H;
	}

	// Court dimensions
	const paintW = 32;
	const paintH = 24;
	const paintLeft = 50 - paintW / 2; // 34
	const paintRight = 50 + paintW / 2; // 66
	const ftCircleR = paintW / 2; // 16
	const threeR = 44;
	const cornerHy = 12;

	type ZoneKey =
		| 'paint'
		| 'short_corner_l'
		| 'short_corner_r'
		| 'mid_wing_l'
		| 'mid_wing_r'
		| 'top_key'
		| 'corner3_l'
		| 'corner3_r'
		| 'above_break_3';

	function classifyZone(hx: number, hy: number): ZoneKey {
		// Corner 3
		if (hx < 6 && hy < cornerHy) return 'corner3_l';
		if (hx > 94 && hy < cornerHy) return 'corner3_r';

		// Above-the-break 3 (outside arc, not in corners)
		const dx = hx - 50;
		const dy = Math.max(hy - 3, 0.001);
		const dist = Math.sqrt(dx * dx + dy * dy);
		if (dist > threeR) return 'above_break_3';

		// Paint (rectangular key)
		if (hx >= paintLeft && hx <= paintRight && hy <= paintH) return 'paint';

		// Short corners (outside paint, near baseline)
		if (hy < cornerHy && hx >= 6 && hx < paintLeft) return 'short_corner_l';
		if (hy < cornerHy && hx > paintRight && hx <= 94) return 'short_corner_r';

		// Top of key (above paint, inside arc, center)
		if (hx >= paintLeft && hx <= paintRight) return 'top_key';

		// Mid-range wings
		if (hx < paintLeft) return 'mid_wing_l';
		return 'mid_wing_r';
	}

	const byZone = $derived.by(() => {
		const stats: Record<ZoneKey, { made: number; total: number }> = {
			paint: { made: 0, total: 0 },
			short_corner_l: { made: 0, total: 0 },
			short_corner_r: { made: 0, total: 0 },
			mid_wing_l: { made: 0, total: 0 },
			mid_wing_r: { made: 0, total: 0 },
			top_key: { made: 0, total: 0 },
			corner3_l: { made: 0, total: 0 },
			corner3_r: { made: 0, total: 0 },
			above_break_3: { made: 0, total: 0 }
		};
		for (const s of shots) {
			const z = classifyZone(s.x, s.y);
			stats[z].total += 1;
			if (Number(s.made) === 1) stats[z].made += 1;
		}
		return stats;
	});

	// Heat: green = above baseline, red = below. Intensity scales with deviation.
	function heatFill(pct: number | null, baseline: number): string {
		if (pct === null) return 'rgba(42, 42, 48, 0.4)';
		const diff = pct - baseline;
		const clamped = Math.max(-20, Math.min(20, diff)) / 20;
		if (clamped >= 0) {
			const alpha = 0.15 + clamped * 0.5;
			return `rgba(0, 184, 148, ${alpha.toFixed(2)})`; // positive green
		} else {
			const alpha = 0.15 + -clamped * 0.5;
			return `rgba(225, 112, 85, ${alpha.toFixed(2)})`; // negative red-orange
		}
	}

	function baselineFor(zone: ZoneKey): number {
		if (zone === 'paint') return 58;
		if (zone === 'short_corner_l' || zone === 'short_corner_r') return 45;
		if (zone === 'corner3_l' || zone === 'corner3_r') return 35;
		if (zone === 'above_break_3') return 32;
		return 35; // mid-range / top key
	}

	// Arc points for 3pt line
	const rx = $derived((threeR / 100) * W);
	const ry = $derived((threeR / 100) * H);

	function pointAtAngle(angleDeg: number, dist = threeR) {
		const rad = (angleDeg * Math.PI) / 180;
		return { x: 50 + Math.sin(rad) * dist, y: 3 + Math.cos(rad) * dist };
	}

	// Intersection of a vertical line hx=c with the 3pt arc (basket center (50,3), radius 44).
	function arcYAtX(c: number): number {
		const dxv = c - 50;
		const under = threeR * threeR - dxv * dxv;
		if (under <= 0) return cornerHy;
		return 3 + Math.sqrt(under);
	}

	const arcY34 = $derived(arcYAtX(paintLeft)); // ~ 44.0
	const arcY66 = $derived(arcYAtX(paintRight)); // ~ 44.0

	// Zone SVG paths
	const zonePaths = $derived.by(() => {
		const paint = `M ${toX(paintLeft)} ${toY(0)} L ${toX(paintRight)} ${toY(0)} L ${toX(paintRight)} ${toY(paintH)} L ${toX(paintLeft)} ${toY(paintH)} Z`;

		const shortCL = `M ${toX(6)} ${toY(0)} L ${toX(paintLeft)} ${toY(0)} L ${toX(paintLeft)} ${toY(cornerHy)} L ${toX(6)} ${toY(cornerHy)} Z`;
		const shortCR = `M ${toX(paintRight)} ${toY(0)} L ${toX(94)} ${toY(0)} L ${toX(94)} ${toY(cornerHy)} L ${toX(paintRight)} ${toY(cornerHy)} Z`;

		const corner3L = `M ${toX(0)} ${toY(0)} L ${toX(6)} ${toY(0)} L ${toX(6)} ${toY(cornerHy)} L ${toX(0)} ${toY(cornerHy)} Z`;
		const corner3R = `M ${toX(94)} ${toY(0)} L ${toX(100)} ${toY(0)} L ${toX(100)} ${toY(cornerHy)} L ${toX(94)} ${toY(cornerHy)} Z`;

		// Mid wing L: polygon bounded by paint-left edge, corner3 top line, and 3pt arc
		// Vertices: (6, cornerHy) → (paintLeft, cornerHy) → (paintLeft, arcY34) → arc sweep down to (6, cornerHy)
		const midWL = `M ${toX(6)} ${toY(cornerHy)} L ${toX(paintLeft)} ${toY(cornerHy)} L ${toX(paintLeft)} ${toY(arcY34)} A ${rx} ${ry} 0 0 0 ${toX(6)} ${toY(cornerHy)} Z`;
		const midWR = `M ${toX(94)} ${toY(cornerHy)} L ${toX(paintRight)} ${toY(cornerHy)} L ${toX(paintRight)} ${toY(arcY66)} A ${rx} ${ry} 0 0 1 ${toX(94)} ${toY(cornerHy)} Z`;

		// Top of key: bounded by paint top edge, paint-side verticals, and top of arc
		const topKey = `M ${toX(paintLeft)} ${toY(paintH)} L ${toX(paintRight)} ${toY(paintH)} L ${toX(paintRight)} ${toY(arcY66)} A ${rx} ${ry} 0 0 0 ${toX(paintLeft)} ${toY(arcY34)} Z`;

		// Above-the-break 3: outside arc, above corners. Enclosed by court edges and arc.
		const above3 = `M ${toX(6)} ${toY(cornerHy)} L ${toX(0)} ${toY(cornerHy)} L ${toX(0)} ${toY(100)} L ${toX(100)} ${toY(100)} L ${toX(100)} ${toY(cornerHy)} L ${toX(94)} ${toY(cornerHy)} A ${rx} ${ry} 0 0 0 ${toX(6)} ${toY(cornerHy)} Z`;

		return { paint, shortCL, shortCR, midWL, midWR, topKey, corner3L, corner3R, above3 };
	});

	// Label positions (approx zone centers)
	const labelPositions: Record<ZoneKey, { hx: number; hy: number }> = {
		paint: { hx: 50, hy: 12 },
		short_corner_l: { hx: 20, hy: 6 },
		short_corner_r: { hx: 80, hy: 6 },
		mid_wing_l: { hx: 17, hy: 27 },
		mid_wing_r: { hx: 83, hy: 27 },
		top_key: { hx: 50, hy: 34 },
		corner3_l: { hx: 3, hy: 6 },
		corner3_r: { hx: 97, hy: 6 },
		above_break_3: { hx: 50, hy: 65 }
	};

	function zoneStatsText(zone: ZoneKey) {
		const s = byZone[zone];
		if (s.total === 0) return { madeText: '0/0', pct: '—', hasData: false };
		const pct = (100 * s.made) / s.total;
		return {
			madeText: `${s.made}/${s.total}`,
			pct: `${pct.toFixed(0)}%`,
			hasData: true
		};
	}

	function zoneFill(zone: ZoneKey): string {
		const s = byZone[zone];
		if (s.total === 0) return 'rgba(42, 42, 48, 0.35)';
		const pct = (100 * s.made) / s.total;
		return heatFill(pct, baselineFor(zone));
	}

	// Dots (semi-transparent overlay)
	const made = $derived(shots.filter((s) => Number(s.made) === 1));
	const missed = $derived(shots.filter((s) => Number(s.made) === 0));
</script>

<div class="flex flex-col items-center gap-3">
	<svg
		viewBox={`0 0 ${W} ${H}`}
		xmlns="http://www.w3.org/2000/svg"
		class="w-full max-w-xl rounded-lg border border-border bg-card"
		aria-label="Shotchart zónák"
	>
		<rect x="0" y="0" width={W} height={H} fill="#0f0f13" />

		<!-- Zone fills -->
		<g stroke="#3a3a42" stroke-width="1">
			<path d={zonePaths.above3} fill={zoneFill('above_break_3')} />
			<path d={zonePaths.midWL} fill={zoneFill('mid_wing_l')} />
			<path d={zonePaths.midWR} fill={zoneFill('mid_wing_r')} />
			<path d={zonePaths.topKey} fill={zoneFill('top_key')} />
			<path d={zonePaths.shortCL} fill={zoneFill('short_corner_l')} />
			<path d={zonePaths.shortCR} fill={zoneFill('short_corner_r')} />
			<path d={zonePaths.corner3L} fill={zoneFill('corner3_l')} />
			<path d={zonePaths.corner3R} fill={zoneFill('corner3_r')} />
			<path d={zonePaths.paint} fill={zoneFill('paint')} stroke-width="1.5" />
		</g>

		<!-- Court detail lines -->
		<g fill="none" stroke="#5a5a62" stroke-width="1">
			<circle cx={toX(50)} cy={toY(paintH)} r={(ftCircleR / 100) * W} />
			<circle cx={toX(50)} cy={toY(3)} r={(5 / 100) * W} />
		</g>

		{#if showDots}
			<!-- Shot dots -->
			<g>
				{#each missed as s, i (i)}
					<circle cx={toX(s.x)} cy={toY(s.y)} r="2" fill="#e17055" fill-opacity="0.55" />
				{/each}
				{#each made as s, i (i)}
					<circle cx={toX(s.x)} cy={toY(s.y)} r="2" fill="#00b894" fill-opacity="0.8" />
				{/each}
			</g>
		{/if}

		<!-- Basket -->
		<circle cx={toX(50)} cy={toY(3)} r={(1.2 / 100) * W} fill="none" stroke="#c41e3a" stroke-width="2" />

		<!-- Zone stat labels (drawn last so they're on top) -->
		<g font-family="Inter, sans-serif" text-anchor="middle" fill="#f5f5f5">
			{#each Object.keys(labelPositions) as zone (zone)}
				{@const z = zone as ZoneKey}
				{@const pos = labelPositions[z]}
				{@const t = zoneStatsText(z)}
				{@const isNarrow =
					z === 'corner3_l' ||
					z === 'corner3_r' ||
					z === 'short_corner_l' ||
					z === 'short_corner_r'}
				{@const fs = isNarrow ? W * 0.026 : W * 0.036}
				{@const cx = toX(pos.hx)}
				{@const cy = toY(pos.hy)}
				<text
					x={cx}
					y={cy}
					font-size={fs}
					font-weight="700"
					style="paint-order: stroke; stroke: #0f0f13; stroke-width: 3px; stroke-linejoin: round;"
				>
					{t.pct}
				</text>
				<text
					x={cx}
					y={cy + fs * 1.1}
					font-size={fs * 0.8}
					fill="#c9c9c9"
					font-weight="500"
					style="paint-order: stroke; stroke: #0f0f13; stroke-width: 3px; stroke-linejoin: round;"
				>
					{t.madeText}
				</text>
			{/each}
		</g>
	</svg>

	<p class="text-xs text-muted text-center">
		Zónánkénti bedobási % (fent) és találat/próbálkozás (lent) ·
		<span class="text-positive">zöld</span> = zóna-átlag fölött,
		<span class="text-negative">piros</span> = alatt
	</p>
</div>
