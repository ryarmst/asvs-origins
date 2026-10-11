import type { Citation, Provenance, Summary } from './types';

export function isRejected(provenance: Provenance | null | undefined): boolean {
	return provenance?.review?.status === 'rejected';
}

export function isUnreviewedAi(provenance: Provenance | null | undefined): boolean {
	if (!provenance) return false;
	if (provenance.origin !== 'llm') return false;
	const status = provenance.review?.status;
	return status !== 'accepted' && status !== 'rejected';
}

export function isPublic(provenance: Provenance | null | undefined): boolean {
	return !isRejected(provenance);
}

export type BadgeKind = 'human' | 'ai' | 'ai-reviewed' | 'extracted';

export function badgeKind(provenance: Provenance): BadgeKind {
	if (provenance.origin === 'human') return 'human';
	if (provenance.origin === 'llm_reviewed') return 'ai-reviewed';
	if (provenance.origin === 'deterministic') return 'extracted';
	return 'ai';
}

export function badgeLabel(kind: BadgeKind, reviewStatus?: string): string {
	if (kind === 'human') return 'Human';
	if (kind === 'ai-reviewed') return 'AI · reviewed';
	if (kind === 'extracted') return 'Extracted';
	if (reviewStatus && reviewStatus !== 'unreviewed') return `AI · ${reviewStatus.replace('_', ' ')}`;
	return 'AI draft';
}

export function chipClass(kind: BadgeKind): string {
	if (kind === 'human') return 'chip-human';
	if (kind === 'ai-reviewed') return 'chip-reviewed';
	if (kind === 'extracted') return 'chip-extracted';
	return 'chip-ai';
}

export function enrichmentLabel(state: string | null | undefined): string {
	if (state === 'human') return 'Human';
	if (state === 'ai_reviewed') return 'AI · reviewed';
	if (state === 'ai_draft') return 'AI draft';
	if (state === 'extracted') return 'Extracted';
	return 'Not enriched';
}

export function enrichmentClass(state: string | null | undefined): string {
	if (state === 'human') return 'chip-human';
	if (state === 'ai_reviewed') return 'chip-reviewed';
	if (state === 'ai_draft') return 'chip-ai';
	if (state === 'extracted') return 'chip-extracted';
	return 'chip-muted';
}

export function coverageLabel(coverage: string | null | undefined): string {
	return coverage || 'unknown';
}

export function pickSummary(summaries: Summary[], kind: string): Summary | null {
	const matches = summaries.filter((item) => item.kind === kind && isPublic(item.provenance));
	const human = matches.find((item) => item.provenance.origin === 'human');
	if (human) return human;
	const reviewed = matches.find((item) => item.provenance.origin === 'llm_reviewed');
	if (reviewed) return reviewed;
	const ai = matches.find((item) => item.provenance.origin === 'llm');
	if (ai) return ai;
	return matches[0] ?? null;
}

export function alternateSummary(summaries: Summary[], shown: Summary | null, kind: string): Summary | null {
	if (!shown) return null;
	return (
		summaries.find(
			(item) =>
				item.kind === kind &&
				item.id !== shown.id &&
				isPublic(item.provenance) &&
				item.provenance.origin !== shown.provenance.origin
		) ?? null
	);
}

export function citationLabel(citation: Citation): string {
	if (citation.issue && citation.type === 'issue_comment') {
		return `#${citation.issue}${citation.author ? ` (${citation.author})` : ''}`;
	}
	if (citation.issue) return `#${citation.issue}`;
	if (citation.commit) return citation.commit.slice(0, 8);
	if (citation.pr) return `PR #${citation.pr}`;
	return citation.type.replace(/_/g, ' ');
}

export function collapseKind(kind: string): boolean {
	return kind === 'renumbered' || kind === 'tag_cleanup';
}
