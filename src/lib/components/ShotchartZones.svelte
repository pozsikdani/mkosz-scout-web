<script lang="ts">
	interface Shot {
		x: number;
		y: number;
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
	const raR = 9; // restricted area radius (≈1.35m on 15m court)
	const wingSplitAngle = 25; // degrees — wing 3 vs above-the-break split

	type ZoneKey =
		// Inside 3pt (7 zones)
		| 'ra'
		| 'paint'
		| 'short_corner_l'
		| 'short_corner_r'
		| 'mid_wing_l'
		| 'mid_wing_r'
		| 'top_key'
		// Outside 3pt (5 zones)
		| 'corner3_l'
		| 'wing3_l'
		| 'above_break_3'
		| 'wing3_r'
		| 'corner3_r';

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
			if (hy < cornerHy && hx < 6) return 'corner3_l';
			if (hy < cornerHy && hx > 94) return 'corner3_r';
			if (ang < -wingSplitAngle) return 'wing3_l';
			if (ang > wingSplitAngle) return 'wing3_r';
			return 'above_break_3';
		}

		// Inside 3pt
		if (dist <= raR) return 'ra';
		if (hx >= paintLeft && hx <= paintRight && hy <= paintH) return 'paint';
		if (hy < cornerHy && hx >= 6 && hx < paintLeft) return 'short_corner_l';
		if (hy < cornerHy && hx > paintRight && hx <= 94) return 'short_corner_r';
		if (hx >= paintLeft && hx <= paintRight) return 'top_key';
		if (hx < paintLeft) return 'mid_wing_l';
		return 'mid_wing_r';
	}

	const ZONE_KEYS: ZoneKey[] = [
		'ra',
		'paint',
		'short_corner_l',
		'short_corner_r',
		'mid_wing_l',
		'mid_wing_r',
		'top_key',
		'corner3_l',
		'wing3_l',
		'above_break_3',
		'wing3_r',
		'corner3_r'
	];

	const byZone = $derived.by(() => {
		const stats = Object.fromEntries(
			ZONE_KEYS.map((k) => [k, { made: 0, total: 0 }])
		) as Record<ZoneKey, { made: number; total: number }>;
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
			return `rgba(0, 184, 148, ${alpha.toFixed(2)})`;
		}
		const alpha = 0.15 + -clamped * 0.5;
		return `rgba(225, 112, 85, ${alpha.toFixed(2)})`;
	}

	function baselineFor(zone: ZoneKey): number {
		if (zone === 'ra') return 66;
		if (zone === 'paint') return 52;
		if (zone === 'short_corner_l' || zone === 'short_corner_r') return 45;
		if (zone === 'corner3_l' || zone === 'corner3_r') return 36;
		if (zone === 'wing3_l' || zone === 'wing3_r') return 34;
		if (zone === 'above_break_3') return 31;
		return 37; // mid-range / top key
	}

	// Arc sizes
	const rx = $derived((threeR / 100) * W);
	const ry = $derived((threeR / 100) * H);
	const raRx = $derived((raR / 100) * W);
	const raRy = $derived((raR / 100) * H);
	const ftRx = $derived((ftCircleR / 100) * W);
	const ftRy = $derived((ftCircleR / 100) * H);

	function pointAtAngle(angleDeg: number, dist = threeR) {
		const rad = (angleDeg * Math.PI) / 180;
		return { x: 50 + Math.sin(rad) * dist, y: basketHy + Math.cos(rad) * dist };
	}

	function rayToEdge(angleDeg: number): { x: number; y: number } {
		const rad = (angleDeg * Math.PI) / 180;
		const dirX = Math.sin(rad);
		const dirY = Math.cos(rad);
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
		// Inside zones
		const paint = `M ${toX(paintLeft)} ${toY(0)} L ${toX(paintRight)} ${toY(0)} L ${toX(paintRight)} ${toY(paintH)} L ${toX(paintLeft)} ${toY(paintH)} Z`;
		// Restricted area: semicircle above basket, with flat base on baseline (hy=0).
		// Base points on baseline: (50 ± xBase, 0) where xBase² + basketHy² = raR² → xBase = sqrt(raR² - basketHy²)
		const xBase = Math.sqrt(Math.max(raR * raR - basketHy * basketHy, 0));
		const raPath = `M ${toX(50 - xBase)} ${toY(0)} A ${raRx} ${raRy} 0 0 0 ${toX(50 + xBase)} ${toY(0)} Z`;

		const shortCL = `M ${toX(6)} ${toY(0)} L ${toX(paintLeft)} ${toY(0)} L ${toX(paintLeft)} ${toY(cornerHy)} L ${toX(6)} ${toY(cornerHy)} Z`;
		const shortCR = `M ${toX(paintRight)} ${toY(0)} L ${toX(94)} ${toY(0)} L ${toX(94)} ${toY(cornerHy)} L ${toX(paintRight)} ${toY(cornerHy)} Z`;

		const midWL = `M ${toX(6)} ${toY(cornerHy)} L ${toX(paintLeft)} ${toY(cornerHy)} L ${toX(paintLeft)} ${toY(arcY34)} A ${rx} ${ry} 0 0 0 ${toX(6)} ${toY(cornerHy)} Z`;
		const midWR = `M ${toX(paintRight)} ${toY(cornerHy)} L ${toX(94)} ${toY(cornerHy)} A ${rx} ${ry} 0 0 0 ${toX(paintRight)} ${toY(arcY66)} Z`;
		const topKey = `M ${toX(paintLeft)} ${toY(paintH)} L ${toX(paintRight)} ${toY(paintH)} L ${toX(paintRight)} ${toY(arcY66)} A ${rx} ${ry} 0 0 0 ${toX(paintLeft)} ${toY(arcY34)} Z`;

		// Outside zones: strict corner strips + wedges split at ±wingSplitAngle
		const corner3L = `M ${toX(0)} ${toY(0)} L ${toX(6)} ${toY(0)} L ${toX(6)} ${toY(cornerHy)} L ${toX(0)} ${toY(cornerHy)} Z`;
		const corner3R = `M ${toX(94)} ${toY(0)} L ${toX(100)} ${toY(0)} L ${toX(100)} ${toY(cornerHy)} L ${toX(94)} ${toY(cornerHy)} Z`;

		// Wing 3 L: from (0, cornerHy) up along sideline to wingSplit ray-edge, in along ray to arc,
		// then along 3pt arc down to (6, cornerHy), then left to (0, cornerHy).
		const wingSplitL_arc = pointAtAngle(-wingSplitAngle);
		const wingSplitL_edge = rayToEdge(-wingSplitAngle);
		const wingSplitR_arc = pointAtAngle(wingSplitAngle);
		const wingSplitR_edge = rayToEdge(wingSplitAngle);

		const wing3L = [
			`M ${toX(0)} ${toY(cornerHy)}`,
			`L ${toX(0)} ${toY(wingSplitL_edge.y)}`,
			// If edge point is on sideline (x=0), no extra corner; if on top edge, need to traverse
			wingSplitL_edge.x > 0
				? `L ${toX(wingSplitL_edge.x)} ${toY(wingSplitL_edge.y)}`
				: '',
			`L ${toX(wingSplitL_arc.x)} ${toY(wingSplitL_arc.y)}`,
			// arc from wingSplitL_arc to (6, cornerHy): backward direction, sweep=0
			`A ${rx} ${ry} 0 0 0 ${toX(6)} ${toY(cornerHy)}`,
			`Z`
		]
			.filter(Boolean)
			.join(' ');

		const wing3R = [
			`M ${toX(100)} ${toY(cornerHy)}`,
			`L ${toX(94)} ${toY(cornerHy)}`,
			// arc from (94, cornerHy) to wingSplitR_arc: forward direction, sweep=1... actually backward?
			// Shotchart forward: (6,12) → arc → (94,12). From (94,12) going backward to wingSplitR_arc (68.6, 42.9). That's backward → sweep=0.
			`A ${rx} ${ry} 0 0 0 ${toX(wingSplitR_arc.x)} ${toY(wingSplitR_arc.y)}`,
			wingSplitR_edge.x < 100
				? `L ${toX(wingSplitR_edge.x)} ${toY(wingSplitR_edge.y)}`
				: '',
			`L ${toX(100)} ${toY(wingSplitR_edge.y)}`,
			`Z`
		]
			.filter(Boolean)
			.join(' ');

		// Above-the-break 3: between the two wing splits, outside arc, bounded by top edge
		// M wingSplitL_arc → arc forward to wingSplitR_arc (sweep=1) → L to wingSplitR_edge →
		// traverse top edge → L to wingSplitL_edge → Z
		const above3Parts: string[] = [];
		above3Parts.push(`M ${toX(wingSplitL_arc.x)} ${toY(wingSplitL_arc.y)}`);
		above3Parts.push(
			`A ${rx} ${ry} 0 0 1 ${toX(wingSplitR_arc.x)} ${toY(wingSplitR_arc.y)}`
		);
		above3Parts.push(`L ${toX(wingSplitR_edge.x)} ${toY(wingSplitR_edge.y)}`);
		// Traverse along top edge or corners as needed
		if (wingSplitR_edge.x >= 100 - 0.01) {
			above3Parts.push(`L ${toX(100)} ${toY(100)}`);
		}
		if (wingSplitR_edge.y >= 100 - 0.01 || wingSplitL_edge.y >= 100 - 0.01) {
			// On top edge — go from right top to left top across
		} else {
			above3Parts.push(`L ${toX(100)} ${toY(100)}`);
			above3Parts.push(`L ${toX(0)} ${toY(100)}`);
		}
		if (wingSplitL_edge.x <= 0 + 0.01) {
			above3Parts.push(`L ${toX(0)} ${toY(100)}`);
		}
		above3Parts.push(`L ${toX(wingSplitL_edge.x)} ${toY(wingSplitL_edge.y)}`);
		above3Parts.push(`Z`);
		const above3 = above3Parts.join(' ');

		// 3pt arc line
		const threeLineArc = `M ${toX(6)} ${toY(cornerHy)} A ${rx} ${ry} 0 0 1 ${toX(94)} ${toY(cornerHy)}`;

		return {
			paint,
			raPath,
			shortCL,
			shortCR,
			midWL,
			midWR,
			topKey,
			corner3L,
			corner3R,
			wing3L,
			wing3R,
			above3,
			threeLineArc
		};
	});

	// Label positions
	const labelPositions: Record<ZoneKey, { hx: number; hy: number }> = {
		ra: { hx: 50, hy: 6 },
		paint: { hx: 50, hy: 18 },
		short_corner_l: { hx: 20, hy: 6 },
		short_corner_r: { hx: 80, hy: 6 },
		mid_wing_l: { hx: 17, hy: 27 },
		mid_wing_r: { hx: 83, hy: 27 },
		top_key: { hx: 50, hy: 34 },
		corner3_l: { hx: 3, hy: 6 },
		corner3_r: { hx: 97, hy: 6 },
		wing3_l: { hx: 5, hy: 42 },
		wing3_r: { hx: 95, hy: 42 },
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

	const NARROW_ZONES: ZoneKey[] = [
		'corner3_l',
		'corner3_r',
		'short_corner_l',
		'short_corner_r',
		'ra',
		'wing3_l',
		'wing3_r'
	];
</script>

<div class="flex flex-col items-center gap-3">
	<svg
		viewBox={`0 0 ${W} ${H}`}
		xmlns="http://www.w3.org/2000/svg"
		class="w-full max-w-xl rounded-lg border border-border bg-card"
		aria-label="Shotchart zónák"
	>
		<rect x="0" y="0" width={W} height={H} fill="#0f0f13" />

		<g stroke="#3a3a42" stroke-width="1">
			<!-- Outside zones -->
			<path d={zonePaths.corner3L} fill={zoneFill('corner3_l')} />
			<path d={zonePaths.corner3R} fill={zoneFill('corner3_r')} />
			<path d={zonePaths.wing3L} fill={zoneFill('wing3_l')} />
			<path d={zonePaths.wing3R} fill={zoneFill('wing3_r')} />
			<path d={zonePaths.above3} fill={zoneFill('above_break_3')} />
			<!-- Inside zones -->
			<path d={zonePaths.midWL} fill={zoneFill('mid_wing_l')} />
			<path d={zonePaths.midWR} fill={zoneFill('mid_wing_r')} />
			<path d={zonePaths.topKey} fill={zoneFill('top_key')} />
			<path d={zonePaths.shortCL} fill={zoneFill('short_corner_l')} />
			<path d={zonePaths.shortCR} fill={zoneFill('short_corner_r')} />
			<path d={zonePaths.paint} fill={zoneFill('paint')} stroke-width="1.5" />
			<path d={zonePaths.raPath} fill={zoneFill('ra')} stroke-width="1.5" />
		</g>

		<!-- 3pt arc + corner lines -->
		<path d={zonePaths.threeLineArc} fill="none" stroke="#8a8a8a" stroke-width="1.5" />
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

		<!-- FT circle (for visual reference) -->
		<circle
			cx={toX(50)}
			cy={toY(paintH)}
			r={ftRx}
			fill="none"
			stroke="#5a5a62"
			stroke-width="1"
		/>

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
			{#each ZONE_KEYS as z (z)}
				{@const pos = labelPositions[z]}
				{@const t = zoneStatsText(z)}
				{@const isNarrow = NARROW_ZONES.includes(z)}
				{@const fs = isNarrow ? W * 0.024 : W * 0.032}
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
		12 zóna — 7 a hárompontoson belül, 5 kívül · bedobási % (fent), találat/próbálkozás (lent) ·
		<span class="text-positive">zöld</span> = zóna-átlag fölött,
		<span class="text-negative">piros</span> = alatt
	</p>
</div>
