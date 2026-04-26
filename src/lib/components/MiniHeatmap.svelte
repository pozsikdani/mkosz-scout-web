<script lang="ts">
	// Compact 12-zone shotchart heatmap for the player card.
	//
	// Geometry constants are duplicated from ShotchartZones.svelte intentionally —
	// the two components have different rendering needs (this one is label-free,
	// fixed-aspect, and uses a 100×77 viewBox so paths can be precomputed). If a
	// third consumer appears, factor into src/lib/shotchart/geometry.ts.

	interface Shot {
		x: number;
		y: number;
		made: number | boolean;
	}
	interface ZoneBaseline {
		made: number;
		att: number;
		fg_pct: number | null;
	}

	let {
		shots = [],
		baselines,
		minVolume = 5
	}: {
		shots?: Shot[];
		baselines: Record<string, ZoneBaseline>;
		minVolume?: number;
	} = $props();

	// Geometry — match ShotchartZones.svelte exactly.
	const Y_SCALE = 0.77;
	const W = 100;
	const H = W * Y_SCALE; // 77
	const paintW = 32;
	const paintH = 24;
	const paintLeft = 50 - paintW / 2; // 34
	const paintRight = 50 + paintW / 2; // 66
	const threeR = 44;
	const threeRy = threeR / Y_SCALE; // ≈51.76
	const cornerHy = 12;
	const basketHy = 3;
	const raR = 9;
	const raRyHy = raR / Y_SCALE;
	const wingSplitAngle = 25;

	type ZoneKey =
		| 'ra'
		| 'paint'
		| 'short_corner_l'
		| 'short_corner_r'
		| 'mid_wing_l'
		| 'mid_wing_r'
		| 'top_key'
		| 'corner3_l'
		| 'wing3_l'
		| 'above_break_3'
		| 'wing3_r'
		| 'corner3_r';

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

	const toX = (hx: number) => hx;
	const toY = (hy: number) => hy * Y_SCALE;

	function angleFromBasket(hx: number, hy: number): number {
		const dx = hx - 50;
		const dyLogical = Math.max((hy - basketHy) * Y_SCALE, 0.001);
		return (Math.atan2(dx, dyLogical) * 180) / Math.PI;
	}
	function ellipticalFrac(hx: number, hy: number, rhx: number, rhy: number): number {
		const ex = (hx - 50) / rhx;
		const ey = (hy - basketHy) / rhy;
		return ex * ex + ey * ey;
	}
	function classifyZone(hx: number, hy: number): ZoneKey {
		const ang = angleFromBasket(hx, hy);
		const insideThree = ellipticalFrac(hx, hy, threeR, threeRy) <= 1;
		const inCornerRect = hy <= cornerHy && (hx <= 6 || hx >= 94);
		const outside3 = !insideThree || inCornerRect;
		if (outside3) {
			if (inCornerRect && hx <= 6) return 'corner3_l';
			if (inCornerRect && hx >= 94) return 'corner3_r';
			if (ang < -wingSplitAngle) return 'wing3_l';
			if (ang > wingSplitAngle) return 'wing3_r';
			return 'above_break_3';
		}
		if (ellipticalFrac(hx, hy, raR, raRyHy) <= 1) return 'ra';
		if (hx >= paintLeft && hx <= paintRight && hy <= paintH) return 'paint';
		if (hy <= cornerHy && hx > 6 && hx < paintLeft) return 'short_corner_l';
		if (hy <= cornerHy && hx > paintRight && hx < 94) return 'short_corner_r';
		if (hx >= paintLeft && hx <= paintRight) return 'top_key';
		if (hx < paintLeft) return 'mid_wing_l';
		return 'mid_wing_r';
	}

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

	function zoneFill(z: ZoneKey): string {
		const s = byZone[z];
		if (s.total < minVolume) return 'rgba(42, 42, 48, 0.4)';
		const pct = s.made / s.total;
		const baseline = baselines?.[z]?.fg_pct ?? null;
		if (baseline == null) return 'rgba(42, 42, 48, 0.4)';
		const diff = pct - baseline; // -1..+1
		// ±15 percentage points = full saturation
		const clamped = Math.max(-0.15, Math.min(0.15, diff)) / 0.15;
		if (clamped >= 0) {
			const alpha = 0.18 + clamped * 0.55;
			return `rgba(0, 184, 148, ${alpha.toFixed(2)})`;
		}
		const alpha = 0.18 + -clamped * 0.55;
		return `rgba(225, 112, 85, ${alpha.toFixed(2)})`;
	}

	function zoneTitle(z: ZoneKey): string {
		const s = byZone[z];
		const labels: Record<ZoneKey, string> = {
			ra: 'Restricted area',
			paint: 'Festék',
			short_corner_l: 'Short corner (B)',
			short_corner_r: 'Short corner (J)',
			mid_wing_l: 'Mid (B)',
			mid_wing_r: 'Mid (J)',
			top_key: 'Top key',
			corner3_l: 'Corner 3 (B)',
			wing3_l: 'Wing 3 (B)',
			above_break_3: 'Above-the-break 3',
			wing3_r: 'Wing 3 (J)',
			corner3_r: 'Corner 3 (J)'
		};
		if (s.total === 0) return `${labels[z]}: nincs lövés`;
		const pct = (100 * s.made) / s.total;
		const base = baselines?.[z]?.fg_pct;
		const baseStr = base != null ? ` (liga ${(100 * base).toFixed(0)}%)` : '';
		return `${labels[z]}: ${s.made}/${s.total} = ${pct.toFixed(0)}%${baseStr}`;
	}

	// Static path strings (W=100, H=77 viewBox)
	const rx = threeR; // = 44 in viewBox units
	const ry = threeR; // pixel circle: rx=ry in pixel space
	const raRx = raR;
	const raRyPx = raR;

	// 3pt arc endpoints at hy = cornerHy
	const arcXLeft =
		50 - threeR * Math.sqrt(1 - ((cornerHy - basketHy) / threeRy) ** 2);
	const arcXRight = 100 - arcXLeft;

	function pointAtAngle(angleDeg: number) {
		const distPx = (threeR / 100) * W;
		const rad = (angleDeg * Math.PI) / 180;
		const dxPx = Math.sin(rad) * distPx;
		const dyPxLogical = Math.cos(rad) * distPx;
		return { x: 50 + (dxPx / W) * 100, y: basketHy + (dyPxLogical / H) * 100 };
	}
	function rayToEdge(angleDeg: number): { x: number; y: number } {
		const rad = (angleDeg * Math.PI) / 180;
		const dirXPx = Math.sin(rad);
		const dirYPxLogical = Math.cos(rad);
		const basketPxX = (50 / 100) * W;
		const basketPxYLogical = (basketHy / 100) * H;
		const candidates: { t: number; hx: number; hy: number }[] = [];
		if (dirYPxLogical > 0) {
			const t = (H - basketPxYLogical) / dirYPxLogical;
			const xPx = basketPxX + dirXPx * t;
			candidates.push({ t, hx: (xPx / W) * 100, hy: 100 });
		}
		if (dirXPx < 0) {
			const t = -basketPxX / dirXPx;
			const yPxLogical = basketPxYLogical + dirYPxLogical * t;
			candidates.push({ t, hx: 0, hy: (yPxLogical / H) * 100 });
		}
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
	function arcYAtX(c: number): number {
		const dxv = c - 50;
		const under = 1 - (dxv / threeR) ** 2;
		if (under <= 0) return cornerHy;
		return basketHy + threeRy * Math.sqrt(under);
	}
	const arcY34 = arcYAtX(paintLeft);
	const arcY66 = arcYAtX(paintRight);
	const wsLArc = pointAtAngle(-wingSplitAngle);
	const wsLEdge = rayToEdge(-wingSplitAngle);
	const wsRArc = pointAtAngle(wingSplitAngle);
	const wsREdge = rayToEdge(wingSplitAngle);

	const xBase = raR * Math.sqrt(Math.max(1 - (basketHy / raRyHy) ** 2, 0));
	const raPath = `M ${toX(50 - xBase)} ${toY(0)} A ${raRx} ${raRyPx} 0 0 1 ${toX(50 + xBase)} ${toY(0)} Z`;
	const paintPath = `M ${toX(paintLeft)} ${toY(0)} L ${toX(paintRight)} ${toY(0)} L ${toX(paintRight)} ${toY(paintH)} L ${toX(paintLeft)} ${toY(paintH)} Z`;
	const shortCL = `M ${toX(6)} ${toY(0)} L ${toX(paintLeft)} ${toY(0)} L ${toX(paintLeft)} ${toY(cornerHy)} L ${toX(6)} ${toY(cornerHy)} Z`;
	const shortCR = `M ${toX(paintRight)} ${toY(0)} L ${toX(94)} ${toY(0)} L ${toX(94)} ${toY(cornerHy)} L ${toX(paintRight)} ${toY(cornerHy)} Z`;
	const midWL = `M ${toX(arcXLeft)} ${toY(cornerHy)} L ${toX(paintLeft)} ${toY(cornerHy)} L ${toX(paintLeft)} ${toY(arcY34)} A ${rx} ${ry} 0 0 1 ${toX(arcXLeft)} ${toY(cornerHy)} Z`;
	const midWR = `M ${toX(paintRight)} ${toY(cornerHy)} L ${toX(arcXRight)} ${toY(cornerHy)} A ${rx} ${ry} 0 0 1 ${toX(paintRight)} ${toY(arcY66)} Z`;
	const topKey = `M ${toX(paintLeft)} ${toY(paintH)} L ${toX(paintRight)} ${toY(paintH)} L ${toX(paintRight)} ${toY(arcY66)} A ${rx} ${ry} 0 0 1 ${toX(paintLeft)} ${toY(arcY34)} Z`;
	const corner3L = `M ${toX(0)} ${toY(0)} L ${toX(6)} ${toY(0)} L ${toX(6)} ${toY(cornerHy)} L ${toX(0)} ${toY(cornerHy)} Z`;
	const corner3R = `M ${toX(94)} ${toY(0)} L ${toX(100)} ${toY(0)} L ${toX(100)} ${toY(cornerHy)} L ${toX(94)} ${toY(cornerHy)} Z`;
	const wing3L = [
		`M ${toX(0)} ${toY(cornerHy)}`,
		`L ${toX(0)} ${toY(wsLEdge.y)}`,
		wsLEdge.x > 0 ? `L ${toX(wsLEdge.x)} ${toY(wsLEdge.y)}` : '',
		`L ${toX(wsLArc.x)} ${toY(wsLArc.y)}`,
		`A ${rx} ${ry} 0 0 1 ${toX(arcXLeft)} ${toY(cornerHy)}`,
		`Z`
	]
		.filter(Boolean)
		.join(' ');
	const wing3R = [
		`M ${toX(100)} ${toY(cornerHy)}`,
		`L ${toX(arcXRight)} ${toY(cornerHy)}`,
		`A ${rx} ${ry} 0 0 1 ${toX(wsRArc.x)} ${toY(wsRArc.y)}`,
		wsREdge.x < 100 ? `L ${toX(wsREdge.x)} ${toY(wsREdge.y)}` : '',
		`L ${toX(100)} ${toY(wsREdge.y)}`,
		`Z`
	]
		.filter(Boolean)
		.join(' ');
	const above3Parts: string[] = [];
	above3Parts.push(`M ${toX(wsLArc.x)} ${toY(wsLArc.y)}`);
	above3Parts.push(`A ${rx} ${ry} 0 0 0 ${toX(wsRArc.x)} ${toY(wsRArc.y)}`);
	above3Parts.push(`L ${toX(wsREdge.x)} ${toY(wsREdge.y)}`);
	if (!(wsREdge.y >= 100 - 0.01 || wsLEdge.y >= 100 - 0.01)) {
		above3Parts.push(`L ${toX(100)} ${toY(100)}`);
		above3Parts.push(`L ${toX(0)} ${toY(100)}`);
	}
	above3Parts.push(`L ${toX(wsLEdge.x)} ${toY(wsLEdge.y)}`);
	above3Parts.push(`Z`);
	const above3 = above3Parts.join(' ');

	const threeLineArc = `M ${toX(arcXLeft)} ${toY(cornerHy)} A ${rx} ${ry} 0 0 0 ${toX(arcXRight)} ${toY(cornerHy)}`;

	const totalShots = $derived(shots.length);

	// Label positions (hx, hy) per zone — coordinates in 0..100 / 0..100 logical
	// space (toY scales hy by Y_SCALE for SVG y). Inherited from
	// ShotchartZones.svelte; tightened a bit for the 100×77 viewBox.
	const labelPositions: Record<ZoneKey, { hx: number; hy: number }> = {
		ra: { hx: 50, hy: 5 },
		paint: { hx: 50, hy: 17 },
		short_corner_l: { hx: 20, hy: 6 },
		short_corner_r: { hx: 80, hy: 6 },
		mid_wing_l: { hx: 17, hy: 26 },
		mid_wing_r: { hx: 83, hy: 26 },
		top_key: { hx: 50, hy: 33 },
		corner3_l: { hx: 3, hy: 6 },
		corner3_r: { hx: 97, hy: 6 },
		wing3_l: { hx: 5, hy: 42 },
		wing3_r: { hx: 95, hy: 42 },
		above_break_3: { hx: 50, hy: 65 }
	};

	// Narrow zones (sliver corner strips, etc.) get a smaller font.
	const NARROW_ZONES: Set<ZoneKey> = new Set([
		'corner3_l',
		'corner3_r',
		'short_corner_l',
		'short_corner_r',
		'ra',
		'wing3_l',
		'wing3_r'
	]);

	function fgPctText(z: ZoneKey): string {
		const s = byZone[z];
		if (s.total === 0) return '';
		return `${Math.round((100 * s.made) / s.total)}%`;
	}
	function shareText(z: ZoneKey): string {
		const s = byZone[z];
		if (s.total === 0) return '';
		return String(s.total);
	}
</script>

{#if totalShots === 0}
	<div
		class="flex h-[123px] w-[160px] items-center justify-center rounded border border-border bg-card-hover text-[10px] text-muted"
		title="Nincs lövésadat"
	>
		nincs lövés
	</div>
{:else}
	<svg
		viewBox={`0 0 ${W} ${H}`}
		xmlns="http://www.w3.org/2000/svg"
		class="h-auto w-[160px] rounded border border-border bg-card-hover"
		aria-label="Mini lövés-heatmap"
	>
		<rect x="0" y="0" width={W} height={H} fill="#0f0f13" />
		<g stroke="#3a3a42" stroke-width="0.4">
			<path d={corner3L} fill={zoneFill('corner3_l')}>
				<title>{zoneTitle('corner3_l')}</title>
			</path>
			<path d={corner3R} fill={zoneFill('corner3_r')}>
				<title>{zoneTitle('corner3_r')}</title>
			</path>
			<path d={wing3L} fill={zoneFill('wing3_l')}>
				<title>{zoneTitle('wing3_l')}</title>
			</path>
			<path d={wing3R} fill={zoneFill('wing3_r')}>
				<title>{zoneTitle('wing3_r')}</title>
			</path>
			<path d={above3} fill={zoneFill('above_break_3')}>
				<title>{zoneTitle('above_break_3')}</title>
			</path>
			<path d={midWL} fill={zoneFill('mid_wing_l')}>
				<title>{zoneTitle('mid_wing_l')}</title>
			</path>
			<path d={midWR} fill={zoneFill('mid_wing_r')}>
				<title>{zoneTitle('mid_wing_r')}</title>
			</path>
			<path d={topKey} fill={zoneFill('top_key')}>
				<title>{zoneTitle('top_key')}</title>
			</path>
			<path d={shortCL} fill={zoneFill('short_corner_l')}>
				<title>{zoneTitle('short_corner_l')}</title>
			</path>
			<path d={shortCR} fill={zoneFill('short_corner_r')}>
				<title>{zoneTitle('short_corner_r')}</title>
			</path>
			<path d={paintPath} fill={zoneFill('paint')} stroke-width="0.5">
				<title>{zoneTitle('paint')}</title>
			</path>
			<path d={raPath} fill={zoneFill('ra')} stroke-width="0.5">
				<title>{zoneTitle('ra')}</title>
			</path>
		</g>
		<path d={threeLineArc} fill="none" stroke="#8a8a8a" stroke-width="0.5" />
		<line x1={toX(6)} y1={toY(0)} x2={toX(6)} y2={toY(cornerHy)} stroke="#8a8a8a" stroke-width="0.5" />
		<line
			x1={toX(94)}
			y1={toY(0)}
			x2={toX(94)}
			y2={toY(cornerHy)}
			stroke="#8a8a8a"
			stroke-width="0.5"
		/>
		<circle cx={toX(50)} cy={toY(basketHy)} r="0.9" fill="none" stroke="#c41e3a" stroke-width="0.6" />

		<!-- Zone labels: FG% (top, white) + share of total attempts (bottom, dim) -->
		<g font-family="Inter, sans-serif" text-anchor="middle">
			{#each ZONE_KEYS as z (z)}
				{@const pos = labelPositions[z]}
				{@const fg = fgPctText(z)}
				{@const sh = shareText(z)}
				{#if fg}
					{@const isNarrow = NARROW_ZONES.has(z)}
					{@const fs = isNarrow ? 3.4 : 4.4}
					<text
						x={toX(pos.hx)}
						y={toY(pos.hy)}
						font-size={fs}
						font-weight="700"
						fill="#f5f5f5"
						style="paint-order: stroke; stroke: #0f0f13; stroke-width: 1px; stroke-linejoin: round;"
					>
						{fg}
					</text>
					<text
						x={toX(pos.hx)}
						y={toY(pos.hy) + fs * 1.05}
						font-size={fs * 0.78}
						font-weight="500"
						fill="#c9c9c9"
						style="paint-order: stroke; stroke: #0f0f13; stroke-width: 1px; stroke-linejoin: round;"
					>
						{sh}
					</text>
				{/if}
			{/each}
		</g>
	</svg>
{/if}
