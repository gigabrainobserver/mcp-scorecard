"""Scoring weights, thresholds, and blocklists."""

from __future__ import annotations

# --- Category Weights (must sum to 1.0) ---
CATEGORY_WEIGHTS = {
    "provenance": 0.30,
    "maintenance": 0.25,
    "popularity": 0.20,
    "permissions": 0.25,
}

# --- Provenance Signal Points (sum = 100) ---
PROVENANCE_POINTS = {
    "has_source_repo": 25,
    "repo_not_archived": 10,
    "has_license": 10,
    "has_installable_package": 15,
    "has_website_url": 5,
    "has_icon": 5,
    "namespace_matches_owner": 10,
    "has_security_md": 10,
    "has_code_of_conduct": 5,
    "unique_description": 5,
}

# --- Maintenance Signal Points (sum = 100) ---
MAINTENANCE_POINTS = {
    "repo_age_over_90d": 10,
    "last_push_recency": 25,      # scaled
    "active_commit_weeks": 20,    # scaled
    "contributor_count": 15,      # tiered
    "version_count": 15,          # tiered
    "releases_past_year": 15,     # scaled
}

# --- Popularity Signal Points (sum = 100) ---
POPULARITY_POINTS = {
    "github_stars": 30,           # log scale
    "github_forks": 15,           # log scale
    "npm_weekly_downloads": 25,   # log scale (v0.2)
    "pypi_monthly_downloads": 25, # log scale (v0.2)
    "github_watchers": 5,
}

# For v0.1: no npm/pypi data, normalize from GitHub signals only
POPULARITY_GITHUB_ONLY_POINTS = {
    "github_stars": 55,
    "github_forks": 30,
    "github_watchers": 15,
}

# --- Permissions Signal Points (sum = 100) ---
PERMISSIONS_POINTS = {
    "secret_env_var_count": 40,   # fewer = higher
    "transport_type_risk": 25,
    "credential_sensitivity": 20,
    "package_type_risk": 15,
}

# --- Score Bands ---
SCORE_BANDS = [
    (80, 100, "High Trust"),
    (60, 79, "Moderate Trust"),
    (40, 59, "Low Trust"),
    (20, 39, "Very Low Trust"),
    (0, 19, "Unknown/Suspicious"),
]

# --- Thresholds ---

# Last push recency: days -> fraction of 25 points
PUSH_RECENCY_MAX_DAYS = 365  # 0 points if older
PUSH_RECENCY_FULL_DAYS = 30  # full points if newer

# Contributor count tiers -> fraction of 15 points
CONTRIBUTOR_TIERS = [
    (10, 1.0),   # 10+ contributors = full
    (4, 0.75),   # 4-9
    (2, 0.50),   # 2-3
    (1, 0.25),   # solo
]

# Version count tiers
VERSION_COUNT_TIERS = [
    (101, 5),    # >100 versions = suspicious
    (51, 10),    # >50 versions = slightly suspicious
    (2, 15),     # 2-50 = healthy
    (1, 5),      # single version
    (0, 0),      # no versions
]

# Stars log scale: 0 stars = 0, 1 = 0.1, 10 = 0.4, 100 = 0.6, 1000 = 0.8, 10000+ = 1.0
STARS_LOG_BRACKETS = [
    (10000, 1.0),
    (1000, 0.8),
    (100, 0.6),
    (10, 0.4),
    (1, 0.1),
    (0, 0.0),
]

FORKS_LOG_BRACKETS = [
    (1000, 1.0),
    (100, 0.8),
    (50, 0.6),
    (10, 0.4),
    (1, 0.1),
    (0, 0.0),
]

WATCHERS_LOG_BRACKETS = [
    (100, 1.0),
    (50, 0.8),
    (20, 0.6),
    (5, 0.4),
    (1, 0.1),
    (0, 0.0),
]

# Transport risk scores (out of 25)
TRANSPORT_RISK = {
    "stdio": 25,
    "sse": 10,
    "streamable-http": 10,
}
TRANSPORT_RISK_DEFAULT = 5  # unknown remote

# Package type risk scores (out of 15)
PACKAGE_TYPE_RISK = {
    "npm": 15,
    "pypi": 15,
    "oci": 10,
}
PACKAGE_TYPE_RISK_DEFAULT = 5  # remote-only, no package

# --- Sensitive Credential Patterns ---
SENSITIVE_CREDENTIAL_PATTERNS = [
    "wallet", "private_key", "secret_key", "master_key",
    "db_password", "database_password", "db_pass",
    "root_password", "admin_password",
    "seed_phrase", "mnemonic",
    "ssh_key", "ssl_cert",
]

# Credential sensitivity: env var name patterns -> score out of 20
# none of these patterns = 20 (best)
# API key patterns = 15
# Sensitive patterns = 5
API_KEY_PATTERNS = [
    "api_key", "api_token", "access_token", "auth_token",
    "bearer", "secret", "token", "key", "password", "credential",
]

# --- Template Description Patterns ---
TEMPLATE_DESCRIPTIONS = [
    "a model context protocol server",
    "an mcp server",
    "mcp server for",
    "a mcp server",
    "model context protocol server",
    "this is an mcp server",
    "this is a mcp server",
    "my mcp server",
    "test mcp server",
    "example mcp server",
    "sample mcp server",
    "hello world mcp server",
]

# --- Staging/Test Name Patterns ---
STAGING_PATTERNS = [
    "test-", "-test", "staging-", "-staging",
    "dev-", "-dev", "example-", "-example",
    "demo-", "-demo", "sample-", "-sample",
    "temp-", "-temp", "tmp-", "-tmp",
]

# --- Registry API ---
REGISTRY_BASE_URL = "https://registry.modelcontextprotocol.io"
REGISTRY_LIMIT = 100  # 'limit' param for pagination

# --- GitHub API ---
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RATE_LIMIT_PER_HOUR = 5000  # authenticated
GITHUB_RATE_LIMIT_BUFFER = 100     # stop this many before limit
GITHUB_CONCURRENT_REQUESTS = 10

# --- Verified Publishers (curated whitelist) ---
# Namespace must match exactly. Dave curates manually.
VERIFIED_PUBLISHERS: set[str] = {
    "com.microsoft",
    "io.github.apollographql",
    "io.github.bytedance",
    "io.github.firebase",
    "io.github.github",
    "io.github.googleapis",
    "io.github.netdata",
    "io.github.nrwl",
    "io.github.safedep",
    "io.github.upstash",
}

# --- License Classification ---
# SPDX IDs grouped by commercial-use impact.
# Source: SPDX license list + common non-standard identifiers from GitHub.
PERMISSIVE_LICENSES: set[str] = {
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC",
    "Unlicense", "CC0-1.0", "0BSD", "Zlib", "BSL-1.0",  # Boost, not Business Source
    "WTFPL", "PostgreSQL", "X11", "Artistic-2.0", "MS-PL",
    "ECL-2.0", "MulanPSL-2.0",
    "CC-BY-4.0",  # Attribution only — permissive
}

COPYLEFT_LICENSES: set[str] = {
    "GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later",
    "GPL-2.0", "GPL-3.0",  # GitHub often returns these without suffixes
    "AGPL-3.0-only", "AGPL-3.0-or-later", "AGPL-3.0",
    "LGPL-2.1-only", "LGPL-2.1-or-later", "LGPL-2.1",
    "LGPL-3.0-only", "LGPL-3.0-or-later", "LGPL-3.0",
    "MPL-2.0", "EUPL-1.1", "EUPL-1.2", "OSL-3.0", "CPAL-1.0", "EPL-2.0",
    "CECILL-2.1", "OFL-1.1",
    "CC-BY-SA-4.0",  # Share-alike = copyleft
}

RESTRICTIVE_LICENSES: set[str] = {
    "BUSL-1.1",      # Business Source License — time-delayed open source
    "SSPL-1.0",      # Server Side Public License (MongoDB)
    "Elastic-2.0",   # Elastic License — no competing SaaS
    "CC-BY-NC-4.0", "CC-BY-NC-SA-4.0", "CC-BY-NC-ND-4.0",  # Non-commercial
    "CC-BY-ND-4.0",  # No derivatives
    "PolyForm-Noncommercial-1.0.0",
    "PolyForm-Small-Business-1.0.0",
    "Commons-Clause",
}


def classify_license(spdx_id: str | None) -> str:
    """Classify a license SPDX ID into a category.

    Returns: "permissive", "copyleft", "restrictive", or "unknown".
    """
    if not spdx_id or spdx_id in ("NOASSERTION", "OTHER"):
        return "unknown"
    if spdx_id in PERMISSIVE_LICENSES:
        return "permissive"
    if spdx_id in COPYLEFT_LICENSES:
        return "copyleft"
    if spdx_id in RESTRICTIVE_LICENSES:
        return "restrictive"
    return "unknown"


# --- Enrichment Cache ---
GITHUB_CACHE_FILE = "data/github_cache.json"
GITHUB_CACHE_MAX_AGE_DAYS = 7  # re-fetch servers older than this

# --- Output ---
OUTPUT_DIR = "output"
DATA_DIR = "data"
