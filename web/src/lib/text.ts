const ESCAPE: Record<string, string> = {
	'&': '&amp;',
	'<': '&lt;',
	'>': '&gt;',
	'"': '&quot;'
};

export function escapeHtml(text: string): string {
	return text.replace(/[&<>"]/g, (ch) => ESCAPE[ch] ?? ch);
}

export function proseHtml(text: string): string {
	const escaped = escapeHtml(text.trim());
	const linked = escaped.replace(
		/(https?:\/\/[^\s<]+)/g,
		'<a href="$1" rel="noreferrer">$1</a>'
	);
	return linked
		.split(/\n{2,}/)
		.map((para) => `<p>${para.replace(/\n/g, '<br />')}</p>`)
		.join('');
}

export function tokenDiff(
	left: string,
	right: string
): { type: 'eq' | 'del' | 'ins'; text: string }[] {
	const a = left.split(/(\s+)/);
	const b = right.split(/(\s+)/);
	const n = a.length;
	const m = b.length;
	const dp: number[][] = Array.from({ length: n + 1 }, () => Array(m + 1).fill(0));
	for (let i = n - 1; i >= 0; i--) {
		for (let j = m - 1; j >= 0; j--) {
			dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
		}
	}
	const out: { type: 'eq' | 'del' | 'ins'; text: string }[] = [];
	let i = 0;
	let j = 0;
	while (i < n && j < m) {
		if (a[i] === b[j]) {
			out.push({ type: 'eq', text: a[i] });
			i += 1;
			j += 1;
		} else if (dp[i + 1][j] >= dp[i][j + 1]) {
			out.push({ type: 'del', text: a[i] });
			i += 1;
		} else {
			out.push({ type: 'ins', text: b[j] });
			j += 1;
		}
	}
	while (i < n) {
		out.push({ type: 'del', text: a[i] });
		i += 1;
	}
	while (j < m) {
		out.push({ type: 'ins', text: b[j] });
		j += 1;
	}
	return out;
}

export function githubCorrectionUrl(label: string, href: string): string {
	const title = `Correction: ${label}`;
	const body = `Page: ${href}\n\nWhat should change:\n\n`;
	return `https://github.com/ryarmst/asvs-origins/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
}
