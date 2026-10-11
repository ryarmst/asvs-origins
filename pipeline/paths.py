"""Repository paths."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SOURCES_DIR = ROOT / "sources"
SCHEMA_DIR = ROOT / "schema"
BUILD_DIR = ROOT / "build"
GIT_CACHE = SOURCES_DIR / "git-cache" / "ASVS"
ASVS_DIR = SOURCES_DIR / "asvs"
ISSUES_DIR = SOURCES_DIR / "issues"
MANIFEST_PATH = SOURCES_DIR / "manifest.json"
DEFAULT_ISSUE_ANALYZE = Path("/home/dbg/Dev/asvs-provenance/asvs-issue-analyze-main")
