<script>
	import Plot from '$lib/Plot.svelte';
 </script>

<svelte:head>
	<title>Temperature</title>
	<meta name="description" content="Svelte demo app" />
</svelte:head>

<section>
	<h1>Temperature Dashboard</h1>
	<Plot />
</section>

<style>
	section {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		flex: 0.6;
	}

	h1 {
		width: 100%;
	}

</style>
