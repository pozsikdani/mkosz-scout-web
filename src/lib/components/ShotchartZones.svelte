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

	// Court dimensions
	const paintW = 32;
	const paintH = 24;
	const paintLeft = 50 - paintW / 2; // 34
	const paintRight = 50 + paintW / 2; // 66
	const ftCircleR = paintW / 2; // 16
	const threeR = 44;
	const cornerHy = 12;
	const basketHy = 3;
	const splitAngle = 40; // degrees — threshold between corner-3 and above-the-break-3

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

	// Angle from basket's "up" direction (toward half-court). Degrees, negative = left, positive = right.
	function angleFromBasket(hx: number, hy: number): number {
		const dx = hx - 50;
		const dy = Math.max(hy - basketHy, 0.001);
		return (Math.atan2(dx, dy) * 180) / Math.PI;
	}

	function distFromBasket(hx: number, hy: number): number {
		const dx = hx - 50;
		const dy = hy - basketHy;
		return Math.sqrt(dx * dx + dy * dy);
	}

	function classifyZone(hx: number, hy: number): ZoneKey {
		const dist = distFromBasket(hx, hy);
		const ang = angleFromBasket(hx, hy);
		const outside3 = dist > threeR || (hy < cornerHy && (hx < 6 || hx > 94));

		if (outside3) {
			if (ang < -splitAngle) return 'corner3_l';
			if (ang > splitAngle) return 'corner3_r';
			return 'above_break_3';
		}

		// Inside the 3pt line
		if (hx >= paintLeft && hx <= paintRight && hy <= paintH) return 'paint';
		if (hy < cornerHy && hx >= 6 && hx < paintLeft) return 'short_corner_l';
		if (hy < cornerHy && hx > paintRight && hx <= 94) return 'short_corner_r';
		if (hx >= paintLeft && hx <= paintRight) return 'top_key';
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

	function heatFill(pct: number | null, baseline: number): string {
		if (pct === null) return 'rgba(42, 42, 48, 0.4)';
		const diff = pct - baseline;
		const clamped = Math.max(-20, Math.min(20, diff)) / 20;
		if (clamped >= 0) {
			const alpha = 0.15 + clamped * 0.5;
			return `rgba(0, 184, 148, ${alpha.toFixed(2)})`; // positive green
		}
		const alpha = 0.15 + -clamped * 0.5;
		return `rgba(225, 112, 85, ${alpha.toFixed(2)})`; // negative red-orange
	}

	function baselineFor(zone: ZoneKey): number {
		if (zone === 'paint') return 58;
		if (zone === 'short_corner_l' || zone === 'short_corner_r') return 45;
		if (zone === 'corner3_l' || zone === 'corner3_r') return 35;
		if (zone === 'above_break_3') return 32;
		return 35;
	}

	// Arc sizing
	const rx = $derived((threeR / 100) * W);
	const ry = $derived((threeR / 100) * H);

	function pointAtAngle(angleDeg: number, dist = threeR) {
		const rad = (angleDeg * Math.PI) / 180;
		return { x: 50 + Math.sin(rad) * dist, y: basketHy + Math.cos(rad) * dist };
	}

	// Where a ray from basket at given angle hits the outer court rectangle (0-100, 0-100).
	function rayToEdge(angleDeg: number): { x: number; y: number } {
		const rad = (angleDeg * Math.PI) / 180;
		const dirX = Math.sin(rad);
		const dirY = Math.cos(rad);
		// Intersect with top (hy=100), left (hx=0), right (hx=100)
		const candidates: { t: number; x: number; y: number }[] = [];
		if (dirY > 0) {
			const t = (100 - basketHy) / dirY;
			candidates.push({ t, x: 50 + dirX * t, y: 100 });
		}
		if (dirX < 0) {
			const t = -50 / dirX;
			candidates.push({ t, x: 0, y: basketHy + dirY * t });
		}
		if (dirX > 0) {
			const t = 50 / dirX;
			candidates.push({ t, x: 100, y: basketHy + dirY * t });
		}
		candidates.sort((a, b) => a.t - b.t);
		const first = candidates.find((c) => c.x >= 0 && c.x <= 100 && c.y >= basketHy && c.y <= 100);
		return first ? { x: first.x, y: first.y } : { x: 50, y: 100 };
	}

	function arcYAtX(c: number): number {
		const dxv = c - 50;
		const under = threeR * threeR - dxv * dxv;
		if (under <= 0) return cornerHy;
		return basketHy + Math.sqrt(under);
	}

	const arcY34 = $derived(arcYAtX(paintLeft));
	const arcY66 = $derived(arcYAtX(paintRight));

	// Zone paths
	const zonePaths = $derived.by(() => {
		// --- Inside zones ---
		const paint = `M ${toX(paintLeft)} ${toY(0)} L ${toX(paintRight)} ${toY(0)} L ${toX(paintRight)} ${toY(paintH)} L ${toX(paintLeft)} ${toY(paintH)} Z`;
		const shortCL = `M ${toX(6)} ${toY(0)} L ${toX(paintLeft)} ${toY(0)} L ${toX(paintLeft)} ${toY(cornerHy)} L ${toX(6)} ${toY(cornerHy)} Z`;
		const shortCR = `M ${toX(paintRight)} ${toY(0)} L ${toX(94)} ${toY(0)} L ${toX(94)} ${toY(cornerHy)} L ${toX(paintRight)} ${toY(cornerHy)} Z`;
		// mid_wing_l: inside arc, left of paint line, above short-corner.
		// Polygon: (6, cornerHy) → (paintLeft, cornerHy) → (paintLeft, arcY34) → arc to (6, cornerHy).
		const midWL = `M ${toX(6)} ${toY(cornerHy)} L ${toX(paintLeft)} ${toY(cornerHy)} L ${toX(paintLeft)} ${toY(arcY34)} A ${rx} ${ry} 0 0 0 ${toX(6)} ${toY(cornerHy)} Z`;
		const midWR = `M ${toX(paintRight)} ${toY(cornerHy)} L ${toX(94)} ${toY(cornerHy)} A ${rx} ${ry} 0 0 0 ${toX(paintRight)} ${toY(arcY66)} Z`;
		// top_key: inside arc, above paint, between paintLeft and paintRight.
		// Polygon: (paintLeft, paintH) → (paintRight, paintH) → (paintRight, arcY66) → arc over top to (paintLeft, arcY34).
		const topKey = `M ${toX(paintLeft)} ${toY(paintH)} L ${toX(paintRight)} ${toY(paintH)} L ${toX(paintRight)} ${toY(arcY66)} A ${rx} ${ry} 0 0 0 ${toX(paintLeft)} ${toY(arcY34)} Z`;

		// --- Outside zones (wedges from basket, clipped by 3pt arc + court) ---
		// Corner 3 L: wedge from angle -90° to -splitAngle, outside arc.
		// Boundary: follow court edge from far corner of wedge (at -90° toward (-x, +y) = (0, something))
		// and arc on inside.
		const basketX = toX(50);
		const basketY = toY(basketHy);

		// End point on arc at -splitAngle
		const arcPtSplit_L = pointAtAngle(-splitAngle);
		// End point on arc at +splitAngle
		const arcPtSplit_R = pointAtAngle(splitAngle);

		// Ray endpoints on court edge at split angles
		const edgePtSplit_L = rayToEdge(-splitAngle);
		const edgePtSplit_R = rayToEdge(splitAngle);

		// Corner 3 L polygon (going CCW in court coordinates):
		//   basket corner (0, 0) → up-left sideline to split ray edge point →
		//   along split ray INWARD to arc intersection (arcPtSplit_L) →
		//   along 3pt arc down-right to corner-3 arc endpoint (6, cornerHy) →
		//   down corner-3 vertical line to (6, 0) → back along baseline to (0, 0).
		const corner3L = [
			`M ${toX(0)} ${toY(0)}`,
			`L ${toX(0)} ${toY(edgePtSplit_L.y)}`,
			`L ${toX(arcPtSplit_L.x)} ${toY(arcPtSplit_L.y)}`,
			`A ${rx} ${ry} 0 0 0 ${toX(6)} ${toY(cornerHy)}`,
			`L ${toX(6)} ${toY(0)}`,
			`Z`
		].join(' ');

		const corner3R = [
			`M ${toX(100)} ${toY(0)}`,
			`L ${toX(94)} ${toY(0)}`,
			`L ${toX(94)} ${toY(cornerHy)}`,
			`A ${rx} ${ry} 0 0 0 ${toX(arcPtSplit_R.x)} ${toY(arcPtSplit_R.y)}`,
			`L ${toX(100)} ${toY(edgePtSplit_R.y)}`,
			`L ${toX(100)} ${toY(0)}`,
			`Z`
		].join(' ');

		// Above-the-break 3: between the two split rays, outside the arc.
		// Polygon: arcPtSplit_L → up via split ray to edgePtSplit_L →
		//   along top edge to (if needed) → edgePtSplit_R → split ray down to arcPtSplit_R →
		//   along arc over the top back to arcPtSplit_L.
		// Edge traversal: edgePtSplit_L → (0, 100) → (100, 100) → edgePtSplit_R (if top edge split),
		// or just (edgePtSplit_L.y=100 case) edgePtSplit_L → edgePtSplit_R along top.
		// Build edge path dynamically.
		const above3Parts: string[] = [`M ${toX(arcPtSplit_L.x)} ${toY(arcPtSplit_L.y)}`];
		above3Parts.push(`L ${toX(edgePtSplit_L.x)} ${toY(edgePtSplit_L.y)}`);
		// Traverse court corners from edgePtSplit_L to edgePtSplit_R going via top.
		if (edgePtSplit_L.x <= 0 + 0.01) {
			// on left sideline — go up to top-left corner
			above3Parts.push(`L ${toX(0)} ${toY(100)}`);
			above3Parts.push(`L ${toX(100)} ${toY(100)}`);
		} else {
			// already on top edge — skip corners
		}
		if (edgePtSplit_R.x >= 100 - 0.01) {
			// right side — come down from top-right corner
			above3Parts.push(`L ${toX(100)} ${toY(edgePtSplit_R.y)}`);
		}
		above3Parts.push(`L ${toX(edgePtSplit_R.x)} ${toY(edgePtSplit_R.y)}`);
		above3Parts.push(`L ${toX(arcPtSplit_R.x)} ${toY(arcPtSplit_R.y)}`);
		// Arc from arcPtSplit_R back over top to arcPtSplit_L (reverse of 3pt arc direction)
		above3Parts.push(`A ${rx} ${ry} 0 0 0 ${toX(arcPtSplit_L.x)} ${toY(arcPtSplit_L.y)}`);
		above3Parts.push(`Z`);
		const above3 = above3Parts.join(' ');

		// 3pt arc line (for visual reference) — same as Shotchart
		const threeLineArc = `M ${toX(6)} ${toY(cornerHy)} A ${rx} ${ry} 0 0 1 ${toX(94)} ${toY(cornerHy)}`;

		return { paint, shortCL, shortCR, midWL, midWR, topKey, corner3L, corner3R, above3, threeLineArc };
	});

	// Label positions — for corner3 wedges, put label at approximately the centroid
	const labelPositions: Record<ZoneKey, { hx: number; hy: number }> = {
		paint: { hx: 50, hy: 12 },
		short_corner_l: { hx: 20, hy: 6 },
		short_corner_r: { hx: 80, hy: 6 },
		mid_wing_l: { hx: 17, hy: 27 },
		mid_wing_r: { hx: 83, hy: 27 },
		top_key: { hx: 50, hy: 34 },
		corner3_l: { hx: 5, hy: 35 },
		corner3_r: { hx: 95, hy: 35 },
		above_break_3: { hx: 50, hy: 68 }
	};

	function zoneStatsText(zone: ZoneKey) {
		const s = byZone[zone];
		if (s.total === 0) return { madeText: '0/0', pct: '—' };
		const pct = (100 * s.made) / s.total;
		return { madeText: `${s.made}/${s.total}`, pct: `${pct.toFixed(0)}%` };
	}

	function zoneFill(zone: ZoneKey): string {
		const s = byZone[zone];
		if (s.total === 0) return 'rgba(42, 42, 48, 0.35)';
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

		<!-- Zone fills -->
		<g stroke="#3a3a42" stroke-width="1">
			<!-- Outside-3pt wedges first (they form the outer shell) -->
			<path d={zonePaths.corner3L} fill={zoneFill('corner3_l')} />
			<path d={zonePaths.corner3R} fill={zoneFill('corner3_r')} />
			<path d={zonePaths.above3} fill={zoneFill('above_break_3')} />
			<!-- Inside-3pt zones on top -->
			<path d={zonePaths.midWL} fill={zoneFill('mid_wing_l')} />
			<path d={zonePaths.midWR} fill={zoneFill('mid_wing_r')} />
			<path d={zonePaths.topKey} fill={zoneFill('top_key')} />
			<path d={zonePaths.shortCL} fill={zoneFill('short_corner_l')} />
			<path d={zonePaths.shortCR} fill={zoneFill('short_corner_r')} />
			<path d={zonePaths.paint} fill={zoneFill('paint')} stroke-width="1.5" />
		</g>

		<!-- Explicit 3pt arc line for visual verification -->
		<path
			d={zonePaths.threeLineArc}
			fill="none"
			stroke="#8a8a8a"
			stroke-width="1.5"
		/>
		<!-- Corner 3 straight lines -->
		<line
			x1={toX(6)}
			y1={toY(0)}
			x2={toX(6)}
			y2={toY(cornerHy)}
			stroke="#8a8a8a"
			stroke-width="1.5"
		/>
		<line
			x1={toX(94)}
			y1={toY(0)}
			x2={toX(94)}
			y2={toY(cornerHy)}
			stroke="#8a8a8a"
			stroke-width="1.5"
		/>

		<!-- Court detail lines -->
		<g fill="none" stroke="#5a5a62" stroke-width="1">
			<circle cx={toX(50)} cy={toY(paintH)} r={(ftCircleR / 100) * W} />
			<circle cx={toX(50)} cy={toY(basketHy)} r={(5 / 100) * W} />
		</g>

		<!-- Basket -->
		<circle
			cx={toX(50)}
			cy={toY(basketHy)}
			r={(1.2 / 100) * W}
			fill="none"
			stroke="#c41e3a"
			stroke-width="2"
		/>

		<!-- Zone stat labels -->
		<g font-family="Inter, sans-serif" text-anchor="middle" fill="#f5f5f5">
			{#each Object.keys(labelPositions) as zone (zone)}
				{@const z = zone as ZoneKey}
				{@const pos = labelPositions[z]}
				{@const t = zoneStatsText(z)}
				{@const isNarrow = z === 'short_corner_l' || z === 'short_corner_r'}
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
