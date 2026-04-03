<script lang="ts">
	import SecurityPolicies from '$lib/components/admin/security/SecurityPolicies.svelte';
	import { user } from '$lib/stores';
	import { onMount } from 'svelte';

	let loaded = false;

	onMount(() => {
		if ($user?.role !== 'admin') {
			// Redirect non-admin users
			window.location.href = '/';
		} else {
			loaded = true;
		}
	});
</script>

{#if loaded}
	<div class="p-6">
		<h1 class="text-2xl font-bold mb-6">Security Policies & Alerts</h1>
		<SecurityPolicies />
	</div>
{/if}
