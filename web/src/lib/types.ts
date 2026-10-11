export type Origin = 'human' | 'llm' | 'llm_reviewed' | 'deterministic';

export type ReviewStatus =
	| 'unreviewed'
	| 'in_review'
	| 'accepted'
	| 'changes_requested'
	| 'rejected';

export type Coverage = 'empty' | 'linked' | 'drafted' | 'reviewed' | 'authored' | 'blocked';

export type Author = { name: string; github: string };

export type Model = {
	provider: string;
	id: string;
	prompt_id: string;
	prompt_version: string;
};

export type Review = {
	status: ReviewStatus;
	by: string[];
	at: string | null;
	note: string | null;
};

export type Provenance = {
	origin: Origin;
	created_at: string;
	updated_at: string;
	authors: Author[];
	model: Model | null;
	review: Review;
	input_digest: string | null;
	confidence: 'high' | 'medium' | 'low';
};

export type Citation = {
	type: string;
	url: string;
	issue?: number;
	pr?: number;
	comment_id?: string | null;
	commit?: string | null;
	author?: string | null;
	date?: string | null;
	quote?: string | null;
	edited_after?: boolean | null;
};

export type Summary = {
	id: string;
	kind: string;
	body: string;
	citations: Citation[];
	supersedes: string | null;
	provenance: Provenance;
};

export type Claim = {
	id: string;
	statement: string;
	kind: string;
	subkind: string;
	date: string | null;
	actors: string[];
	status: string;
	citations: Citation[];
	provenance: Provenance;
};

export type LineageEvent = {
	date: string;
	kind: string;
	commit: string | null;
	actor: string | null;
	id_at_time: string | null;
	summary: string;
	citations: Citation[];
};

export type Predecessor = {
	release: string;
	id: string;
	relation: string;
	text: string | null;
	note: string | null;
};

export type KeySource = {
	kind: 'issue' | 'pr';
	number: number;
	role: string;
	rank: number;
};

export type RequirementRecord = {
	uid: string;
	slug: string;
	current: {
		release: string;
		id: string;
		chapter_id: string;
		chapter_name: string;
		section_id: string;
		section_name: string;
		level: number | null;
		text: string;
		source: string;
		status: string;
	};
	master: {
		id: string | null;
		level: number | null;
		text: string | null;
		differs_from_release: boolean;
		checked_at: string;
	};
	identifiers: { release: string; id: string; level: number | null; status: string }[];
	lineage: {
		origin_kind: string;
		predecessors: Predecessor[];
		mapping_entry: {
			raw: string;
			status: string;
			agrees_with_git: boolean;
			note: string | null;
		} | null;
		events: LineageEvent[];
		provenance: Provenance;
	};
	summaries: Summary[];
	decisions: Claim[];
	open_questions: Claim[];
	terminology: Claim[];
	key_sources: KeySource[];
	related_requirements: {
		uid: string;
		id: string;
		relation: string;
		note: string | null;
	}[];
	external_references: { kind: string; id?: string | null; title?: string | null; url: string }[];
	status: {
		coverage: Coverage;
		lineage_state: string;
		last_pipeline_run: string | null;
		last_human_review: string | null;
		blocked_reason: string | null;
		stale: boolean;
	};
};

export type IssueSlice = {
	id: string;
	requirement_uid: string;
	requirement_id_at_time: string | null;
	relevance: string;
	body: string;
	decisions: Claim[];
	arguments: Claim[];
	terminology: Claim[];
	open_questions: Claim[];
	outcome: string;
	citations: Citation[];
	provenance: Provenance;
};

export type IssueRecord = {
	kind: 'issue';
	number: number;
	url: string;
	title: string;
	state: string;
	created_at: string;
	closed_at: string | null;
	author: string;
	participants: string[];
	labels: string[];
	source: Record<string, unknown>;
	triage: {
		class: string;
		relevance: string;
		estimated_requirement_count: number;
		reason: string;
		provenance: Provenance;
	} | null;
	summaries: Summary[];
	outcome: {
		state: string;
		resulting_changes: string[];
		closed_reason: string | null;
		provenance: Provenance;
	} | null;
	requirement_summaries: IssueSlice[];
	unmapped_topics: { topic: string; reason: string; provenance: Provenance }[];
	external_references: { kind: string; url: string; title?: string | null }[];
	status: {
		coverage: Coverage;
		last_pipeline_run: string | null;
		last_human_review: string | null;
		stale: boolean;
	};
};

export type RequirementCard = {
	uid: string;
	id: string;
	slug: string;
	chapter_id: string;
	chapter_name: string;
	section_id: string;
	section_name: string;
	level: number | null;
	coverage: Coverage;
	lineage_state: string;
	blocked_reason: string | null;
	text: string;
	has_origin: boolean;
	key_source_count: number;
	event_count: number;
	enrichment: 'human' | 'ai_reviewed' | 'ai_draft' | 'extracted' | 'none';
};

export type IssueCard = {
	number: number;
	title: string;
	state: string;
	coverage: Coverage;
	author: string | null;
	relevance: string | null;
	class: string | null;
	requirement_ids: string[];
	chapter_ids: string[];
};

export type Chapter = {
	id: string;
	name: string;
	requirement_ids: string[];
	by_coverage: Record<string, number>;
	sections: { id: string; name: string; requirement_ids: string[] }[];
};

export type CoverageReport = {
	generated_at: string;
	requirements: {
		total: number;
		by_coverage: Record<string, number>;
		reviewed_or_better: number;
		reviewed_or_better_pct: number;
		lineage_complete: number;
		lineage_complete_pct: number;
		sourced: number;
		sourced_pct: number;
		orphans_without_key_sources: number;
	};
	issues: {
		total: number;
		by_coverage: Record<string, number>;
		requirement_bearing: number;
		requirement_bearing_drafted_or_better: number;
	};
	provenance_mix: Record<string, number>;
	provenance_mix_published: Record<string, number>;
};

export type Mention = {
	issue: number;
	title: string;
	relevance: string;
	body: string;
	id: string;
};

export type SearchDoc = {
	id: string;
	kind: string;
	title: string;
	text: string;
	href: string;
	chapter: string | null;
	coverage: string;
};

export type QueueItem = {
	priority: number;
	kind: string;
	id: string | number;
	reason: string;
	coverage: string;
	confidence?: string;
};

export type SourceComment = {
	id: string;
	url: string;
	author: string;
	createdAt: string;
	body: string;
};

export type SourceThread = {
	number: number;
	title: string;
	url: string;
	author: string;
	body: string;
	comments: SourceComment[];
};
