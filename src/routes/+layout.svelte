<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>MKOSZ Scout Report</title>
</svelte:head>

<div class="min-h-screen bg-bg text-fg">
	{@render children()}
</div>
