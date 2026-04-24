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

	// mkosz / mockup_s1s2.py convention: basket at TOP, hy=0 at baseline, hy=100 at half-court.
	// (hx, hy) space is NON-ISOTROPIC. Empirically the 3pt arc is an ellipse with
	// rx ≈ 44 hx-units and ry ≈ 57 hy-units (derived from mid/three zone boundary
	// in mkosz data) → aspect H/W = 44/57 ≈ 0.77.
	const Y_SCALE = 0.77;
	const height = $derived(width * Y_SCALE);
	const W = $derived(width);
	const H = $derived(height);

	function toX(hx: number) {
		return (hx / 100) * W;
	}
	// hy=0 (baseline / basket side) at SVG top; hy=100 (half-court) at SVG bottom.
	function toY(hy: number) {
		return (hy / 100) * H;
	}

	// Court dimensions (hx = horizontal %, hy = vertical %)
	const paintW = 32;
	const paintH = 24;
	const paintLeft = 50 - paintW / 2; // 34
	const paintRight = 50 + paintW / 2; // 66
	const ftCircleR = paintW / 2; // 16 (radius on hx-axis; y-radius = 16/Y_SCALE)
	const threeR = 44; // 3pt radius on hx-axis
	const threeRy = threeR / Y_SCALE; // 3pt radius on hy-axis (≈51.76)
	const cornerHy = 12;
	const basketHy = 3;
	const raR = 9; // restricted area radius on hx-axis (≈1.35m)
	const raRyHy = raR / Y_SCALE; // RA radius on hy-axis (≈10.59)
	const wingSplitAngle = 25; // degrees — wing 3 vs above-the-break split (measured in pixel space)

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

	// Angle measured in pixel space (where the ellipse becomes a true circle).
	// Uses atan2(dx_px, dy_px_logical_upward) so 0° = straight out from basket, + = right.
	function angleFromBasket(hx: number, hy: number): number {
		const dxPx = ((hx - 50) / 100) * W;
		const dyPxLogical = Math.max(((hy - basketHy) / 100) * H, 0.001);
		return (Math.atan2(dxPx, dyPxLogical) * 180) / Math.PI;
	}

	// Elliptical distance squared — 1.0 means exactly on the 3pt arc
	function ellipticalFrac(hx: number, hy: number, rhx: number, rhy: number): number {
		const ex = (hx - 50) / rhx;
		const ey = (hy - basketHy) / rhy;
		return ex * ex + ey * ey;
	}

	function classifyZone(hx: number, hy: number): ZoneKey {
		const ang = angleFromBasket(hx, hy);
		const insideThree = ellipticalFrac(hx, hy, threeR, threeRy) <= 1;
		const outside3 = !insideThree || (hy < cornerHy && (hx < 6 || hx > 94));

		if (outside3) {
			if (hy < cornerHy && hx < 6) return 'corner3_l';
			if (hy < cornerHy && hx > 94) return 'corner3_r';
			if (ang < -wingSplitAngle) return 'wing3_l';
			if (ang > wingSplitAngle) return 'wing3_r';
			return 'above_break_3';
		}

		// Inside 3pt
		if (ellipticalFrac(hx, hy, raR, raRyHy) <= 1) return 'ra';
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

	// SVG arc radii — TRUE PIXEL CIRCLES (rx=ry in pixel space).
	// On H = 0.85·W canvas, a pixel circle of pixel-radius r becomes an ellipse in
	// (hx, hy) space with hx-radius = r/W*100 and hy-radius = r/H*100 = hx-radius/Y_SCALE.
	const rx = $derived((threeR / 100) * W);
	const ry = $derived((threeR / 100) * W);
	const raRx = $derived((raR / 100) * W);
	const raRy = $derived((raR / 100) * W);
	const ftRx = $derived((ftCircleR / 100) * W);
	const ftRy = $derived((ftCircleR / 100) * W);

	// Arc endpoints where 3pt ellipse meets hy=cornerHy:
	//   (hx-50)²/threeR² + (cornerHy-basketHy)²/threeRy² = 1
	const arcXLeft =
		50 - threeR * Math.sqrt(1 - ((cornerHy - basketHy) / threeRy) ** 2);
	const arcXRight = 100 - arcXLeft;

	// Convert pixel-space angle (from basket) into (hx, hy) point on the 3pt arc.
	// distPx is the pixel radius from basket — defaults to the 3pt pixel radius.
	function pointAtAngle(angleDeg: number, distPxOverride?: number) {
		const distPx = distPxOverride ?? (threeR / 100) * W;
		const rad = (angleDeg * Math.PI) / 180;
		const dxPx = Math.sin(rad) * distPx;
		const dyPxLogical = Math.cos(rad) * distPx; // upward in logical hy
		return {
			x: 50 + (dxPx / W) * 100,
			y: basketHy + (dyPxLogical / H) * 100
		};
	}

	// Ray from basket at pixel-space angleDeg until it hits a canvas edge.
	// Works in pixel space, returns (hx, hy) of the edge hit.
	function rayToEdge(angleDeg: number): { x: number; y: number } {
		const rad = (angleDeg * Math.PI) / 180;
		const dirXPx = Math.sin(rad);
		const dirYPxLogical = Math.cos(rad); // upward
		const basketPxX = (50 / 100) * W;
		const basketPxYLogical = (basketHy / 100) * H; // from baseline, upward
		const candidates: { t: number; hx: number; hy: number }[] = [];
		// Top edge: hy=100 → pixel-upward-distance = H (basket to top)
		if (dirYPxLogical > 0) {
			const t = (H - basketPxYLogical) / dirYPxLogical;
			const xPx = basketPxX + dirXPx * t;
			candidates.push({ t, hx: (xPx / W) * 100, hy: 100 });
		}
		// Left edge hx=0
		if (dirXPx < 0) {
			const t = -basketPxX / dirXPx;
			const yPxLogical = basketPxYLogical + dirYPxLogical * t;
			candidates.push({ t, hx: 0, hy: (yPxLogical / H) * 100 });
		}
		// Right edge hx=100
		if (dirXPx > 0) {
			const t = (W - basketPxX) / dirXPx;
			const yPxLogical = basketPxYLogical + dirYPxLogical * t;
			candidates.push({ t, hx: 100, hy: (yPxLogical / H) * 100 });
		}
		candidates.sort((a, b) => a.t - b.t);
		const first = candidates.find(
			(c) => c.hx >= 0 && c.hx <= 100 && c.hy >= basketHy && c.hy <= 100
		);
		return first ? { x: first.hx, y: first.hy } : { x: 50, y: 100 };
	}

	// Y value (hy) where the 3pt ellipse crosses vertical line hx=c.
	function arcYAtX(c: number): number {
		const dxv = c - 50;
		const under = 1 - (dxv / threeR) ** 2;
		if (under <= 0) return cornerHy;
		return basketHy + threeRy * Math.sqrt(under);
	}

	const arcY34 = $derived(arcYAtX(paintLeft));
	const arcY66 = $derived(arcYAtX(paintRight));

	// Zone paths
	const zonePaths = $derived.by(() => {
		// Inside zones
		const paint = `M ${toX(paintLeft)} ${toY(0)} L ${toX(paintRight)} ${toY(0)} L ${toX(paintRight)} ${toY(paintH)} L ${toX(paintLeft)} ${toY(paintH)} Z`;
		// Restricted area: ellipse (pixel-circle rendered) above basket, flat base on baseline.
		// Base points: (50 ± xBase, 0) where (xBase/raR)² + (basketHy/raRyHy)² = 1
		const xBase = raR * Math.sqrt(Math.max(1 - (basketHy / raRyHy) ** 2, 0));
		const raPath = `M ${toX(50 - xBase)} ${toY(0)} A ${raRx} ${raRy} 0 0 1 ${toX(50 + xBase)} ${toY(0)} Z`;

		const shortCL = `M ${toX(6)} ${toY(0)} L ${toX(paintLeft)} ${toY(0)} L ${toX(paintLeft)} ${toY(cornerHy)} L ${toX(6)} ${toY(cornerHy)} Z`;
		const shortCR = `M ${toX(paintRight)} ${toY(0)} L ${toX(94)} ${toY(0)} L ${toX(94)} ${toY(cornerHy)} L ${toX(paintRight)} ${toY(cornerHy)} Z`;

		const midWL = `M ${toX(arcXLeft)} ${toY(cornerHy)} L ${toX(paintLeft)} ${toY(cornerHy)} L ${toX(paintLeft)} ${toY(arcY34)} A ${rx} ${ry} 0 0 1 ${toX(arcXLeft)} ${toY(cornerHy)} Z`;
		const midWR = `M ${toX(paintRight)} ${toY(cornerHy)} L ${toX(arcXRight)} ${toY(cornerHy)} A ${rx} ${ry} 0 0 1 ${toX(paintRight)} ${toY(arcY66)} Z`;
		const topKey = `M ${toX(paintLeft)} ${toY(paintH)} L ${toX(paintRight)} ${toY(paintH)} L ${toX(paintRight)} ${toY(arcY66)} A ${rx} ${ry} 0 0 1 ${toX(paintLeft)} ${toY(arcY34)} Z`;

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
			wingSplitL_edge.x > 0
				? `L ${toX(wingSplitL_edge.x)} ${toY(wingSplitL_edge.y)}`
				: '',
			`L ${toX(wingSplitL_arc.x)} ${toY(wingSplitL_arc.y)}`,
			// arc from wingSplitL_arc to (arcXLeft, cornerHy) — basket at top → sweep=1
			`A ${rx} ${ry} 0 0 1 ${toX(arcXLeft)} ${toY(cornerHy)}`,
			`Z`
		]
			.filter(Boolean)
			.join(' ');

		const wing3R = [
			`M ${toX(100)} ${toY(cornerHy)}`,
			`L ${toX(arcXRight)} ${toY(cornerHy)}`,
			`A ${rx} ${ry} 0 0 1 ${toX(wingSplitR_arc.x)} ${toY(wingSplitR_arc.y)}`,
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
			// basket at top: arc dome dips toward bottom → sweep=0
			`A ${rx} ${ry} 0 0 0 ${toX(wingSplitR_arc.x)} ${toY(wingSplitR_arc.y)}`
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

		// 3pt arc line — basket at top, arc dome dips downward → sweep=0
		const threeLineArc = `M ${toX(arcXLeft)} ${toY(cornerHy)} A ${rx} ${ry} 0 0 0 ${toX(arcXRight)} ${toY(cornerHy)}`;

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
