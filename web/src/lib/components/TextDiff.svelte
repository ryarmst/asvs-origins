<script lang="ts">
	import { tokenDiff } from '$lib/text';

	let { left, right, leftLabel, rightLabel }: { left: string; right: string; leftLabel: string; rightLabel: string } =
		$props();
	const tokens = $derived(tokenDiff(left, right));
</script>

<div class="split">
	<div>
		<p class="kicker">{leftLabel}</p>
		<p>{left}</p>
	</div>
	<div>
		<p class="kicker">{rightLabel}</p>
		<p class="diff">
			{#each tokens as token}
				{#if token.type === 'del'}<del>{token.text}</del>{:else if token.type === 'ins'}<ins>{token.text}</ins>{:else}{token.text}{/if}
			{/each}
		</p>
	</div>
</div>
