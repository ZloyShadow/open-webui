<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { config } from '$lib/stores';
	import APILogs from '$lib/components/admin/APILogs.svelte';

	onMount(() => {
		if (!($config?.features.enable_admin_analytics ?? true)) {
			goto('/admin');
		}
	});
</script>

{#if $config?.features.enable_admin_analytics ?? true}
	<APILogs />
{/if}
