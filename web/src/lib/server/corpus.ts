import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import type {
	Chapter,
	CoverageReport,
	IssueCard,
	IssueRecord,
	Mention,
	RequirementCard,
	RequirementRecord,
	SourceThread
} from '$lib/types';

function repoRoot(): string {
	const cwd = process.cwd();
	if (existsSync(join(cwd, 'data', 'requirements'))) return cwd;
	if (existsSync(join(cwd, '..', 'data', 'requirements'))) return join(cwd, '..');
	throw new Error(`cannot find asvs-origins repo root from ${cwd}`);
}

export const REPO_ROOT = repoRoot();
const DATA = join(REPO_ROOT, 'data');
const INDEX = join(REPO_ROOT, 'build/index');
const SOURCES = join(REPO_ROOT, 'sources');

function readJson<T>(path: string): T {
	return JSON.parse(readFileSync(path, 'utf8')) as T;
}

export function indexJson<T>(name: string): T {
	return readJson<T>(join(INDEX, name));
}

export function coverage(): CoverageReport {
	return indexJson('coverage.json');
}

export function requirementCards(): RequirementCard[] {
	return indexJson('requirements.json');
}

export function issueCards(): IssueCard[] {
	return indexJson('issues.json');
}

export function chapters(): Chapter[] {
	return indexJson('chapters.json');
}

export function uidToId(): Record<string, string> {
	return indexJson('uid-to-id.json');
}

export function idToUid(): Record<string, string> {
	return indexJson('id-to-uid.json');
}

export function legacyMap(): Record<string, Record<string, { uid: string; id: string; slug: string }>> {
	return indexJson('legacy.json');
}

export function mentions(): Record<string, Mention[]> {
	return indexJson('mentions.json');
}

export function people(): Record<
	string,
	{
		login: string;
		authored_issues: number[];
		participated_issues: number[];
		reviewed_artifacts: number;
		claim_mentions: number;
		requirement_ids: string[];
	}
> {
	return indexJson('people.json');
}

export function lineagePairs(): {
	from_release: string;
	from_id: string;
	to_id: string;
	to_uid: string;
	relation: string;
	from_text: string | null;
	to_text: string;
	note: string | null;
	mapping: { raw: string; status: string; agrees_with_git: boolean; note: string | null } | null;
}[] {
	return indexJson('lineage-pairs.json');
}

export function mappingV4(): {
	from_id: string;
	from_text: string | null;
	raw: string;
	status: string;
	to_ids: string[];
	deleted: boolean;
	v5_yaml_backrefs: string[];
}[] {
	return indexJson('mapping-v4.json');
}

export function mappingAlignment(): {
	source: Record<string, string>;
	counts: Record<string, number>;
	yaml_mismatches: { kind: string; v5_id: string; v4_id: string; detail: string }[];
	git_disagreements: { id: string; uid: string; raw: string | null; note: string | null; kind?: string }[];
	stale_slots: { id: string; uid: string; raw: string | null; note: string | null; kind?: string }[];
} {
	return indexJson('mapping-alignment.json');
}

export function loadRequirement(id: string): RequirementRecord {
	const chapter = id.split('.')[0];
	return readJson(join(DATA, 'requirements', chapter, `${id}.json`));
}

export function loadIssue(number: number | string): IssueRecord {
	return readJson(join(DATA, 'issues', `${number}.json`));
}

export function requirementExists(id: string): boolean {
	const chapter = id.split('.')[0];
	return existsSync(join(DATA, 'requirements', chapter, `${id}.json`));
}

export function issueExists(number: number | string): boolean {
	return existsSync(join(DATA, 'issues', `${number}.json`));
}

export function loadSourceThread(number: number): SourceThread | null {
	const path = join(SOURCES, 'issues', `${number}.json`);
	if (!existsSync(path)) return null;
	const raw = readJson<{
		title?: string;
		url?: string;
		body?: string;
		author?: { login?: string } | string;
		comments?: {
			id?: string;
			url?: string;
			createdAt?: string;
			body?: string;
			author?: { login?: string } | string;
		}[];
	}>(path);
	const author =
		typeof raw.author === 'string' ? raw.author : (raw.author?.login ?? 'unknown');
	return {
		number,
		title: raw.title ?? `Issue ${number}`,
		url: raw.url ?? `https://github.com/OWASP/ASVS/issues/${number}`,
		author,
		body: raw.body ?? '',
		comments: (raw.comments ?? []).map((comment) => ({
			id: String(comment.id ?? ''),
			url: comment.url ?? '',
			author: typeof comment.author === 'string' ? comment.author : (comment.author?.login ?? ''),
			createdAt: comment.createdAt ?? '',
			body: comment.body ?? ''
		}))
	};
}

export function pythonBin(): string {
	const venv = join(REPO_ROOT, '.venv/bin/python');
	return existsSync(venv) ? venv : 'python3';
}
