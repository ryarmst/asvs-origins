import type { Provenance } from './types';

export type Artifact = {
	path: string;
	preview: string;
	kind?: string;
	provenance: Provenance;
};

function walk(value: unknown, path: string, found: Artifact[]) {
	if (Array.isArray(value)) {
		value.forEach((child, index) => walk(child, path ? `${path}/${index}` : String(index), found));
		return;
	}
	if (!value || typeof value !== 'object') return;
	const node = value as Record<string, unknown>;
	if (node.provenance && typeof node.provenance === 'object') {
		const provenance = node.provenance as Provenance;
		if (provenance.origin && provenance.review) {
			found.push({
				path,
				kind: typeof node.kind === 'string' ? node.kind : undefined,
				preview: String(node.body ?? node.statement ?? node.reason ?? path).slice(0, 240),
				provenance
			});
		}
	} else if (typeof node.origin === 'string' && node.review && typeof node.review === 'object') {
		found.push({
			path,
			preview: path,
			provenance: node as unknown as Provenance
		});
	}
	for (const [key, child] of Object.entries(node)) {
		if (key === 'provenance') continue;
		walk(child, path ? `${path}/${key}` : key, found);
	}
}

export function listArtifacts(record: unknown): Artifact[] {
	const found: Artifact[] = [];
	walk(record, '', found);
	return found.filter((item) => !item.path.startsWith('lineage'));
}
