"""Red flag detection — 12 binary flags independent of the trust score.

Flags indicate structural or behavioral anomalies that warrant manual review,
regardless of the server's numeric score.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from mcp_scorecard.config import (
    SENSITIVE_CREDENTIAL_PATTERNS,
    STAGING_PATTERNS,
    TEMPLATE_DESCRIPTIONS,
)

# Type aliases
ServerEntry = dict[str, Any]
GitHubData = dict[str, Any]


class FlagContext:
    """Pre-computed lookups for flags that need corpus-wide context.

    Build once via build_flag_context(), then pass to detect_flags()
    for each server.
    """

    __slots__ = ("namespace_counts", "namespace_repo_rates", "description_ns_counts")

    def __init__(
        self,
        namespace_counts: dict[str, int],
        namespace_repo_rates: dict[str, float],
        description_ns_counts: dict[str, int],
    ) -> None:
        self.namespace_counts = namespace_counts
        self.namespace_repo_rates = namespace_repo_rates
        self.description_ns_counts = description_ns_counts


def build_flag_context(all_servers: list[ServerEntry]) -> FlagContext:
    """Pre-compute corpus-wide data needed by BULK_PUBLISHER and
    DESCRIPTION_DUPLICATE flags.

    Args:
        all_servers: Full list of ServerEntry dicts from the registry.

    Returns:
        FlagContext with namespace counts, repo rates, and description
        namespace counts.
    """
    # namespace -> total count
    ns_total: dict[str, int] = defaultdict(int)
    # namespace -> count with repo_url
    ns_with_repo: dict[str, int] = defaultdict(int)
    # description (lowered, stripped) -> set of namespaces
    desc_namespaces: dict[str, set[str]] = defaultdict(set)

    for s in all_servers:
        ns = s.get("namespace", "")
        ns_total[ns] += 1
        if s.get("repo_url"):
            ns_with_repo[ns] += 1

        desc = (s.get("description") or "").lower().strip()
        if desc:
            desc_namespaces[desc].add(ns)

    # Compute rates
    namespace_repo_rates: dict[str, float] = {}
    for ns, total in ns_total.items():
        with_repo = ns_with_repo.get(ns, 0)
        namespace_repo_rates[ns] = with_repo / total if total > 0 else 0.0

    # Distinct namespace count per description
    description_ns_counts: dict[str, int] = {
        desc: len(ns_set) for desc, ns_set in desc_namespaces.items()
    }

    return FlagContext(
        namespace_counts=dict(ns_total),
        namespace_repo_rates=namespace_repo_rates,
        description_ns_counts=description_ns_counts,
    )


def _is_template_description(desc: str) -> bool:
    """Check if description matches any template pattern (case-insensitive)."""
    lowered = desc.lower().strip()
    if not lowered:
        return False
    return any(lowered.startswith(t) for t in TEMPLATE_DESCRIPTIONS)


def _matches_staging_pattern(text: str) -> bool:
    """Check if text matches any staging/test name pattern."""
    lowered = text.lower()
    return any(pat in lowered for pat in STAGING_PATTERNS)


def detect_flags(
    server: ServerEntry,
    github: GitHubData | None,
    ctx: FlagContext,
) -> list[str]:
    """Detect red flags for a single server.

    Args:
        server: The ServerEntry dict.
        github: Optional GitHub enrichment data dict.
        ctx: Pre-computed FlagContext from build_flag_context().

    Returns:
        List of flag name strings (e.g. ["DEAD_ENTRY", "NO_SOURCE"]).
    """
    flags: list[str] = []

    # 1. DEAD_ENTRY — no packages and no remotes, AND no active source repo
    if not server.get("has_packages") and not server.get("has_remotes"):
        has_active_repo = (
            server.get("repo_url")
            and github is not None
            and not github.get("github_archived", False)
            and (github.get("github_commit_weeks_active") or 0) > 0
        )
        if not has_active_repo:
            flags.append("DEAD_ENTRY")

    # 2. TEMPLATE_DESCRIPTION
    desc = server.get("description") or ""
    if _is_template_description(desc):
        flags.append("TEMPLATE_DESCRIPTION")

    # 3. VERSION_FLOOD — stub for v0.1 (only latest version available)
    # Will be implemented when multi-version data is collected.

    # 6. STAGING_ARTIFACT — name or server_id matches staging pattern AND
    #    description matches template
    name = server.get("name", "")
    server_id = server.get("server_id", "")
    if (
        _matches_staging_pattern(name) or _matches_staging_pattern(server_id)
    ) and _is_template_description(desc):
        flags.append("STAGING_ARTIFACT")

    # 7. HIGH_SECRET_DEMAND — 5+ secret env vars
    env_vars = server.get("env_vars") or []
    secret_count = sum(1 for ev in env_vars if ev.get("is_secret"))
    if secret_count >= 5:
        flags.append("HIGH_SECRET_DEMAND")

    # 8. SENSITIVE_CRED_REQUEST — any env var name matches sensitive patterns
    for ev in env_vars:
        var_name = (ev.get("name") or "").lower()
        if any(pat in var_name for pat in SENSITIVE_CREDENTIAL_PATTERNS):
            flags.append("SENSITIVE_CRED_REQUEST")
            break

    # 9. REPO_ARCHIVED
    if github is not None and github.get("github_archived"):
        flags.append("REPO_ARCHIVED")

    # 10. NO_SOURCE — no repo_url and no package_identifiers
    pkg_ids = server.get("package_identifiers") or []
    if not server.get("repo_url") and not pkg_ids:
        flags.append("NO_SOURCE")

    # 11. KNOWN_VULN — stub for v0.1 (requires separate vulnerability API)
    # Will be implemented when OSV/advisory data source is integrated.

    # 12. DESCRIPTION_DUPLICATE — same description used by >=3 different namespaces
    desc_key = desc.lower().strip()
    if desc_key and ctx.description_ns_counts.get(desc_key, 0) >= 3:
        flags.append("DESCRIPTION_DUPLICATE")

    return flags
