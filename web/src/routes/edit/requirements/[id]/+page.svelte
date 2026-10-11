<script lang="ts">
	import Editor from '$lib/components/Editor.svelte';
	let { data } = $props();
</script>

<Editor kind={data.kind} id={data.id} record={data.record} threads={data.threads} />
