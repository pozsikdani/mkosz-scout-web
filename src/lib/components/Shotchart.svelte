<script lang="ts">
	interface Shot {
		x: number;
		y: number;
		made: number | boolean;
	}

	let {
		shots = [],
		width = 520,
		showLegend = true
	}: { shots?: Shot[]; width?: number; showLegend?: boolean } = $props();

	// Half-court rendered with basket at TOP center (mkosz / mockup_s1s2.py convention).
	// mkosz hx,hy are 0-100%: hx = 0 (left) → 100 (right); hy = 0 (baseline, basket side) → 100 (half-court).
	// SVG y grows downward, so hy=0 maps to SVG y=0 (top) and hy=100 to SVG y=H (bottom).
	//
	// IMPORTANT: mkosz's (hx, hy) space is NON-ISOTROPIC. Empirically (from the
	// mid/three zone boundary in the data) the 3pt arc is an ellipse with
	// rx ≈ 44 hx-units and ry ≈ 57 hy-units → aspect H/W = 44/57 ≈ 0.77.
	// Rendering at this ratio makes SVG pixel-circles coincide with the actual
	// mkosz 3pt boundary, so shots land on the drawn arc at their true positions.
	const Y_SCALE = 0.77;
	const height = $derived(width * Y_SCALE);
	const W = $derived(width);
	const H = $derived(height);

	// Convert court hx,hy → SVG coords. hy=0 (baseline) at TOP, hy=100 (half-court) at BOTTOM.
	function toX(hx: number) {
		return (hx / 100) * W;
	}
	function toY(hy: number) {
		return (hy / 100) * H;
	}

	// Court element positions (in hx,hy 0-100 space), per mockup_s1s2.py
	const basketX = 50;
	const basketY = 3;
	const paintWidth = 32; // %
	const paintDepth = 24; // % (from baseline up)
	const paintLeft = 50 - paintWidth / 2;
	const paintRight = 50 + paintWidth / 2;
	const ftCircleR = paintWidth / 2; // 16%
	const three = { cx: 50, cy: basketY, r: 44 }; // x-radius in hx units
	const threeRy = three.r / Y_SCALE; // y-radius in hy units (≈51.76) — arc is ellipse in (hx,hy)
	const cornerHy = 12;

	// Arc endpoints on the ellipse: at hy=cornerHy, solve (hx-50)²/threeR² + (hy-bY)²/threeRy² = 1
	const arcXLeft =
		50 - three.r * Math.sqrt(1 - ((cornerHy - basketY) / threeRy) ** 2);
	const arcXRight = 100 - arcXLeft;

	// Arc path: pixel circle (rx=ry=0.44W) rendered on H=0.85W canvas → ellipse in (hx,hy) space
	const arcPath = $derived.by(() => {
		const x1 = toX(arcXLeft);
		const y1 = toY(cornerHy);
		const x2 = toX(arcXRight);
		const y2 = toY(cornerHy);
		const rPx = (three.r / 100) * W;
		// sweep=0: arc dips downward from the corners toward half-court (basket at top)
		return `M ${x1} ${y1} A ${rPx} ${rPx} 0 0 0 ${x2} ${y2}`;
	});

	const made = $derived(shots.filter((s) => Number(s.made) === 1));
	const missed = $derived(shots.filter((s) => Number(s.made) === 0));
	const fgPct = $derived(shots.length > 0 ? (100 * made.length) / shots.length : 0);
</script>

<div class="flex flex-col items-center gap-3">
	<svg
		viewBox={`0 0 ${W} ${H}`}
		xmlns="http://www.w3.org/2000/svg"
		class="w-full max-w-xl rounded-lg border border-border bg-card"
		aria-label="Shotchart"
	>
		<!-- court background -->
		<rect x="0" y="0" width={W} height={H} fill="#0f0f13" />

		<!-- baseline + sidelines + half-court -->
		<g fill="none" stroke="#3a3a42" stroke-width="1.5">
			<rect x="1" y="1" width={W - 2} height={H - 2} />
			<!-- paint (key) — extends from baseline (hy=0, top) down to hy=paintDepth -->
			<rect
				x={toX(paintLeft)}
				y={toY(0)}
				width={toX(paintRight) - toX(paintLeft)}
				height={toY(paintDepth) - toY(0)}
			/>
			<!-- free throw circle (top half visible, bottom dashed inside paint) -->
			<circle cx={toX(50)} cy={toY(paintDepth)} r={(ftCircleR / 100) * W} />
			<!-- 3-point arc -->
			<path d={arcPath} />
			<!-- corner 3 lines: vertical from baseline to cornerHy -->
			<line x1={toX(6)} y1={toY(0)} x2={toX(6)} y2={toY(cornerHy)} />
			<line x1={toX(94)} y1={toY(0)} x2={toX(94)} y2={toY(cornerHy)} />
		</g>

		<!-- restricted area arc (1.25m radius ~ small arc near basket) -->
		<circle
			cx={toX(basketX)}
			cy={toY(basketY)}
			r={(5 / 100) * W}
			fill="none"
			stroke="#3a3a42"
			stroke-width="1"
		/>

		<!-- basket -->
		<circle cx={toX(basketX)} cy={toY(basketY)} r={(1.2 / 100) * W} fill="none" stroke="#c41e3a" stroke-width="2" />

		<!-- missed shots (render first so made draw on top) -->
		<g>
			{#each missed as s, i (i)}
				<circle cx={toX(s.x)} cy={toY(s.y)} r="3.5" fill="#e17055" fill-opacity="0.55" stroke="#e17055" stroke-width="0.5" />
			{/each}
		</g>

		<!-- made shots -->
		<g>
			{#each made as s, i (i)}
				<circle cx={toX(s.x)} cy={toY(s.y)} r="3.5" fill="#00b894" fill-opacity="0.75" stroke="#00b894" stroke-width="0.5" />
			{/each}
		</g>
	</svg>

	{#if showLegend}
		<div class="flex flex-wrap items-center justify-center gap-4 text-xs">
			<span class="flex items-center gap-1.5">
				<span class="inline-block h-2.5 w-2.5 rounded-full bg-positive"></span>
				Bement <span class="font-mono text-muted">{made.length}</span>
			</span>
			<span class="flex items-center gap-1.5">
				<span class="inline-block h-2.5 w-2.5 rounded-full bg-negative opacity-60"></span>
				Kimaradt <span class="font-mono text-muted">{missed.length}</span>
			</span>
			<span class="font-mono">
				{shots.length} lövés · FG%
				<span class:text-positive={fgPct >= 50} class:text-negative={fgPct < 40}>
					{fgPct.toFixed(1)}
				</span>
			</span>
		</div>
	{/if}
</div>
