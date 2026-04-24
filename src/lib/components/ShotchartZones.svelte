<script lang="ts">
	interface Shot {
		x: number; // hx 0-100
		y: number; // hy 0-100
		made: number | boolean;
	}

	let {
		shots = [],
		width = 520
	}: { shots?: Shot[]; width?: number } = $props();

	const height = $derived(Math.round(width * 0.94));
	const W = $derived(width);
	const H = $derived(height);

	function toX(hx: number) {
		return (hx / 100) * W;
	}
	function toY(hy: number) {
		return H - (hy / 100) * H;
	}

	// Court dimensions (same as Shotchart.svelte)
	const paintW = 32;
	const paintH = 24;
	const paintLeft = 50 - paintW / 2; // 34
	const paintRight = 50 + paintW / 2; // 66
	const ftCircleR = paintW / 2; // 16
	const threeR = 44;
	const cornerHy = 12;

	type ZoneKey =
		| 'paint'
		| 'mid_left'
		| 'mid_center'
		| 'mid_right'
		| 'corner3_left'
		| 'corner3_right'
		| 'above_break_3';

	// Classify a shot into a zone based on hx,hy and angle from basket.
	function classifyZone(hx: number, hy: number): ZoneKey {
		// Paint (rectangular key)
		if (hx >= paintLeft && hx <= paintRight && hy <= paintHeight(hx, hy)) {
			return 'paint';
		}
		// Basket at (50, 3). Angle in degrees: 0 = straight up toward top of court.
		const dx = hx - 50;
		const dy = Math.max(hy - 3, 0.001);
		const distance = Math.sqrt(dx * dx + dy * dy);
		const angle = (Math.atan2(dx, dy) * 180) / Math.PI;

		// Three-point detection: outside the 3pt arc OR in corner 3 zones
		const inCornerZone = hy < cornerHy && (hx < 6 || hx > 94);
		const beyondArc = distance > threeR;
		if (inCornerZone || beyondArc) {
			if (hy < cornerHy) {
				return hx < 50 ? 'corner3_left' : 'corner3_right';
			}
			return 'above_break_3';
		}

		// Mid-range: angle-based split
		if (angle < -20) return 'mid_left';
		if (angle > 20) return 'mid_right';
		return 'mid_center';
	}

	// Paint height check — rectangular, but we need to handle shots at paint edges correctly
	function paintHeight(_hx: number, _hy: number): number {
		return paintH;
	}

	const byZone = $derived.by(() => {
		const stats: Record<ZoneKey, { made: number; total: number }> = {
			paint: { made: 0, total: 0 },
			mid_left: { made: 0, total: 0 },
			mid_center: { made: 0, total: 0 },
			mid_right: { made: 0, total: 0 },
			corner3_left: { made: 0, total: 0 },
			corner3_right: { made: 0, total: 0 },
			above_break_3: { made: 0, total: 0 }
		};
		for (const s of shots) {
			const z = classifyZone(s.x, s.y);
			stats[z].total += 1;
			if (Number(s.made) === 1) stats[z].made += 1;
		}
		return stats;
	});

	// Heat color based on FG% (league avg ~45% for 2pt, ~33% for 3pt).
	// For simple visual: blend between cold blue and hot red around a neutral baseline.
	function heatFill(pct: number | null, baseline: number): string {
		if (pct === null) return 'rgba(42, 42, 48, 0.6)'; // neutral grey when no shots
		const diff = pct - baseline; // positive = hot, negative = cold
		const clamped = Math.max(-20, Math.min(20, diff)) / 20; // -1..1
		if (clamped > 0) {
			// hot — accent red
			const alpha = 0.2 + clamped * 0.45;
			return `rgba(196, 30, 58, ${alpha.toFixed(2)})`;
		} else {
			// cold — steel blue
			const alpha = 0.2 + -clamped * 0.35;
			return `rgba(70, 130, 180, ${alpha.toFixed(2)})`;
		}
	}

	function baselineFor(zone: ZoneKey): number {
		// FIBA NB1B average FG% per zone (rough). Paint ~58%, mid ~35%, three ~32%.
		if (zone === 'paint') return 58;
		if (zone === 'corner3_left' || zone === 'corner3_right' || zone === 'above_break_3')
			return 32;
		return 35;
	}

	// Zone polygon paths in hx,hy space, converted to SVG paths.
	// Each zone is an SVG path string using toX/toY conversion.
	const zonePaths = $derived.by(() => {
		// Paint: simple rect
		const paint = `M ${toX(paintLeft)} ${toY(0)} L ${toX(paintRight)} ${toY(0)} L ${toX(paintRight)} ${toY(paintH)} L ${toX(paintLeft)} ${toY(paintH)} Z`;
		// Corner 3 left: rect (0,0)-(6,12)
		const c3l = `M ${toX(0)} ${toY(0)} L ${toX(6)} ${toY(0)} L ${toX(6)} ${toY(cornerHy)} L ${toX(0)} ${toY(cornerHy)} Z`;
		// Corner 3 right: rect (94,0)-(100,12)
		const c3r = `M ${toX(94)} ${toY(0)} L ${toX(100)} ${toY(0)} L ${toX(100)} ${toY(cornerHy)} L ${toX(94)} ${toY(cornerHy)} Z`;

		// Arc points for 3pt line: arc from (6, 12) through top to (94, 12), radius=44 around (50, 3)
		const rx = (threeR / 100) * W;
		const ry = (threeR / 100) * H;
		const arcStartX = toX(6);
		const arcStartY = toY(cornerHy);
		const arcEndX = toX(94);
		const arcEndY = toY(cornerHy);

		// Above-the-break 3: outside the arc, bounded by court edges (excluding corners)
		const above3 = `M ${arcStartX} ${arcStartY} A ${rx} ${ry} 0 0 1 ${arcEndX} ${arcEndY} L ${toX(100)} ${toY(cornerHy)} L ${toX(100)} ${toY(100)} L ${toX(0)} ${toY(100)} L ${toX(0)} ${toY(cornerHy)} Z`;

		// Mid-range divisions by angle from basket (50, 3):
		// angle < -20° = mid_left (left wedge inside arc, outside paint)
		// |angle| ≤ 20° = mid_center (top wedge)
		// angle > 20° = mid_right (right wedge)
		// The mid region is: inside 3pt arc, outside paint, not in the paint columns.

		// Compute arc intersection points for mid-range sectors.
		// Angle split lines at ±20° from basket.
		// Line from basket (50,3) at angle θ: direction (sin θ, cos θ).
		// Find intersection with 3pt arc (r = 44) — at distance 44 from basket.
		function pointAtAngle(angleDeg: number, dist = threeR) {
			const rad = (angleDeg * Math.PI) / 180;
			return { x: 50 + Math.sin(rad) * dist, y: 3 + Math.cos(rad) * dist };
		}
		const p20neg = pointAtAngle(-20);
		const p20pos = pointAtAngle(20);

		// Mid-left: bounded by paint-left side, bottom paint-corner (34, 24),
		// up to mid_left/mid_center split at p20neg on arc, then arc down to corner3 start (6, 12),
		// then corner3 edge down to (6, 0), basket side edge to (34, 0), up to paint.
		// Actually: mid-range is the space between paint and 3pt arc, above corner3 lines.
		// Easier: use angle wedges from basket (50,3) radiating out to the 3pt arc.

		// Mid-left wedge: from paint-top-left (34, 24) along paint top to (50, 24) (free throw line center),
		// up along -20° line to arc intersection p20neg, along arc to corner arc start (6, 12),
		// down to (6, cornerHy) on corner edge... wait, corner3 is outside the arc.
		// The mid area stops at 3pt line. Below hy=12 with hx<6 is corner3. With 6<hx<34 and hy<12 is mid too.

		// Simplification: mid_left = polygon from (34, 0) → (34, 24) → (50, 24) → p20neg → arc to (6, 12) → (6, 0) → (34, 0)
		// BUT the angle split between mid_left and mid_center in the top (above paint, inside arc)
		// should go from the basket (50, 3) up through free-throw extended.
		// Rather than perfectly match the angle rule, approximate:
		// mid_left: below free-throw line (hy ≤ paintH + top), hx in [6, 34]
		// mid_center: above paint (hy > paintH), hx in [some left, some right] inside arc
		// mid_right: hx in [66, 94], hy ≤ paintH + top

		// Three mid sub-zones:
		// mid_left: left of paint, inside 3pt arc. Bounded: arc (left side), paint-left-edge, corner3-inner-edge
		// mid_right: mirror
		// mid_center: above free-throw line, inside arc, between mid_left and mid_right

		// mid_left polygon (approx): (6, cornerHy) → (34, cornerHy) → (34, paintH) → (50, paintH) → arc from top to (6, cornerHy)
		// This doesn't look right either. Let me use angle wedges cleanly:

		// Wedge from basket (50,3) between angles θ1 and θ2, clipped by 3pt arc (r=44) and outer paint/court:
		// Path: M basket → line to arc @ θ1 → arc to θ2 → line back to basket
		// This is simple and matches the angle classification.

		function wedge(angle1: number, angle2: number) {
			// Start from basket, go to arc at angle1, arc to angle2 (sweep), back to basket.
			const bx = toX(50);
			const by = toY(3);
			const a1 = pointAtAngle(angle1);
			const a2 = pointAtAngle(angle2);
			return `M ${bx} ${by} L ${toX(a1.x)} ${toY(a1.y)} A ${rx} ${ry} 0 0 1 ${toX(a2.x)} ${toY(a2.y)} Z`;
		}
		// Mid angle covers roughly -70° to +70° (left corner to right corner, through top).
		// Split: left = -70 to -20, center = -20 to +20, right = +20 to +70.
		// But we need to SUBTRACT the paint from mid_center and mid_left/right.
		// For visual simplicity, draw wedges without subtracting — the paint is drawn ON TOP
		// so its fill overlaps. This causes double-coverage but since paint comes last in z-order,
		// the paint color wins visually. Stats are computed per-shot so no double-counting there.

		const midLeft = wedge(-70, -20);
		const midCenter = wedge(-20, 20);
		const midRight = wedge(20, 70);

		return { paint, c3l, c3r, above3, midLeft, midCenter, midRight };
	});

	// Zone label positions (approximate centers in hx,hy space)
	const labelPositions: Record<ZoneKey, { hx: number; hy: number }> = {
		paint: { hx: 50, hy: 12 },
		mid_left: { hx: 22, hy: 25 },
		mid_center: { hx: 50, hy: 36 },
		mid_right: { hx: 78, hy: 25 },
		corner3_left: { hx: 9, hy: 6 },
		corner3_right: { hx: 91, hy: 6 },
		above_break_3: { hx: 50, hy: 62 }
	};

	function zoneStatsText(zone: ZoneKey): { count: string; pct: string; madeText: string } {
		const s = byZone[zone];
		if (s.total === 0) return { count: '0', pct: '—', madeText: '0/0' };
		const pct = (100 * s.made) / s.total;
		return {
			count: s.total.toString(),
			pct: `${pct.toFixed(0)}%`,
			madeText: `${s.made}/${s.total}`
		};
	}

	function zoneFill(zone: ZoneKey): string {
		const s = byZone[zone];
		if (s.total === 0) return 'rgba(42, 42, 48, 0.4)';
		const pct = (100 * s.made) / s.total;
		return heatFill(pct, baselineFor(zone));
	}
</script>

<div class="flex flex-col items-center gap-3">
	<svg
		viewBox={`0 0 ${W} ${H}`}
		xmlns="http://www.w3.org/2000/svg"
		class="w-full max-w-xl rounded-lg border border-border bg-card"
		aria-label="Shotchart zónák"
	>
		<rect x="0" y="0" width={W} height={H} fill="#0f0f13" />

		<!-- Zone fills (order matters for overlap: draw mid-wedges first, then specific zones on top) -->
		<g>
			<path d={zonePaths.midLeft} fill={zoneFill('mid_left')} stroke="#3a3a42" stroke-width="1" />
			<path d={zonePaths.midCenter} fill={zoneFill('mid_center')} stroke="#3a3a42" stroke-width="1" />
			<path d={zonePaths.midRight} fill={zoneFill('mid_right')} stroke="#3a3a42" stroke-width="1" />
			<path d={zonePaths.above3} fill={zoneFill('above_break_3')} stroke="#3a3a42" stroke-width="1" />
			<path d={zonePaths.c3l} fill={zoneFill('corner3_left')} stroke="#3a3a42" stroke-width="1" />
			<path d={zonePaths.c3r} fill={zoneFill('corner3_right')} stroke="#3a3a42" stroke-width="1" />
			<!-- paint drawn last so it covers the mid-wedge overlap under the paint -->
			<path d={zonePaths.paint} fill={zoneFill('paint')} stroke="#3a3a42" stroke-width="1.5" />
		</g>

		<!-- Court line details over the fills -->
		<g fill="none" stroke="#5a5a62" stroke-width="1">
			<!-- free throw circle -->
			<circle cx={toX(50)} cy={toY(paintH)} r={(ftCircleR / 100) * W} />
			<!-- restricted area -->
			<circle cx={toX(50)} cy={toY(3)} r={(5 / 100) * W} />
		</g>
		<!-- basket -->
		<circle
			cx={toX(50)}
			cy={toY(3)}
			r={(1.2 / 100) * W}
			fill="none"
			stroke="#c41e3a"
			stroke-width="2"
		/>

		<!-- Zone stat labels -->
		<g font-family="Inter, sans-serif" font-weight="700" text-anchor="middle" fill="#f5f5f5">
			{#each Object.keys(labelPositions) as zone (zone)}
				{@const z = zone as ZoneKey}
				{@const pos = labelPositions[z]}
				{@const t = zoneStatsText(z)}
				{@const cx = toX(pos.hx)}
				{@const cy = toY(pos.hy)}
				{@const isCorner = z === 'corner3_left' || z === 'corner3_right'}
				{@const fontSize = isCorner ? W * 0.028 : W * 0.035}
				<text
					x={cx}
					y={cy}
					font-size={fontSize}
					style="paint-order: stroke; stroke: #0f0f13; stroke-width: 3px; stroke-linejoin: round;"
				>
					{t.madeText}
				</text>
				<text
					x={cx}
					y={cy + fontSize * 1.15}
					font-size={fontSize * 0.85}
					fill="#c9c9c9"
					font-weight="500"
					style="paint-order: stroke; stroke: #0f0f13; stroke-width: 3px; stroke-linejoin: round;"
				>
					{t.pct}
				</text>
			{/each}
		</g>
	</svg>

	<p class="text-xs text-muted text-center">
		Zónánkénti találat / próbálkozás · % = bedobási arány ·
		<span class="text-accent">piros</span> = átlag fölött,
		<span class="text-[#4682b4]">kék</span> = átlag alatt
	</p>
</div>
