"""Category scorers — provenance, maintenance, popularity, permissions.

Each scorer takes a ServerEntry dict and optional GitHub data dict,
returning (score: int 0-100, signals: dict).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from mcp_scorecard.config import (
    API_KEY_PATTERNS,
    CONTRIBUTOR_TIERS,
    FORKS_LOG_BRACKETS,
    PACKAGE_TYPE_RISK,
    PACKAGE_TYPE_RISK_DEFAULT,
    POPULARITY_GITHUB_ONLY_POINTS,
    PROVENANCE_POINTS,
    PUSH_RECENCY_FULL_DAYS,
    PUSH_RECENCY_MAX_DAYS,
    SENSITIVE_CREDENTIAL_PATTERNS,
    STARS_LOG_BRACKETS,
    TEMPLATE_DESCRIPTIONS,
    TRANSPORT_RISK,
    TRANSPORT_RISK_DEFAULT,
    WATCHERS_LOG_BRACKETS,
)

# Type aliases for readability
ServerEntry = dict[str, Any]
GitHubData = dict[str, Any]


def _parse_iso(dt_str: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string, returning None on failure."""
    if not dt_str:
        return None
    try:
        # Handle trailing Z and various ISO formats
        cleaned = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


def _days_since(dt_str: str | None) -> float | None:
    """Return days between now(UTC) and the given ISO datetime string."""
    dt = _parse_iso(dt_str)
    if dt is None:
        return None
    now = datetime.now(UTC)
    # Ensure both are offset-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = now - dt
    return max(delta.total_seconds() / 86400, 0)


def _bracket_score(count: int | None, brackets: list[tuple[int, float]]) -> float:
    """Find the first bracket where count >= threshold, return its fraction."""
    if count is None:
        return 0.0
    for threshold, fraction in brackets:
        if count >= threshold:
            return fraction
    return 0.0


def _normalize_for_comparison(s: str) -> str:
    """Lowercase and strip dots/hyphens for fuzzy namespace matching."""
    return re.sub(r"[.\-_]", "", s.lower().strip())


# ---------------------------------------------------------------------------
# Provenance (30%)
# ---------------------------------------------------------------------------


def score_provenance(
    server: ServerEntry, github: GitHubData | None
) -> tuple[int, dict]:
    """Score provenance signals. Returns (score 0-100, signals dict)."""
    signals: dict[str, Any] = {}
    points = 0

    # has_source_repo
    has_repo = bool(server.get("repo_url"))
    signals["has_source_repo"] = has_repo
    if has_repo:
        points += PROVENANCE_POINTS["has_source_repo"]

    # repo_not_archived
    if github is not None:
        not_archived = not github.get("github_archived", False)
    else:
        not_archived = False
    signals["repo_not_archived"] = not_archived
    if not_archived:
        points += PROVENANCE_POINTS["repo_not_archived"]

    # has_license
    has_license = github is not None and bool(github.get("github_license"))
    signals["has_license"] = has_license
    if has_license:
        points += PROVENANCE_POINTS["has_license"]

    # has_installable_package
    has_pkg = bool(server.get("has_packages"))
    signals["has_installable_package"] = has_pkg
    if has_pkg:
        points += PROVENANCE_POINTS["has_installable_package"]

    # has_website_url
    has_site = bool(server.get("has_website"))
    signals["has_website_url"] = has_site
    if has_site:
        points += PROVENANCE_POINTS["has_website_url"]

    # has_icon
    has_icon = bool(server.get("has_icon"))
    signals["has_icon"] = has_icon
    if has_icon:
        points += PROVENANCE_POINTS["has_icon"]

    # namespace_matches_owner
    ns_match = False
    if github is not None and github.get("github_owner"):
        norm_ns = _normalize_for_comparison(server.get("namespace", ""))
        norm_owner = _normalize_for_comparison(github["github_owner"])
        if norm_ns and norm_owner:
            ns_match = norm_owner in norm_ns or norm_ns in norm_owner
    signals["namespace_matches_owner"] = ns_match
    if ns_match:
        points += PROVENANCE_POINTS["namespace_matches_owner"]

    # has_security_md
    has_sec = github is not None and bool(github.get("github_has_security_md"))
    signals["has_security_md"] = has_sec
    if has_sec:
        points += PROVENANCE_POINTS["has_security_md"]

    # has_code_of_conduct
    has_coc = github is not None and bool(github.get("github_has_code_of_conduct"))
    signals["has_code_of_conduct"] = has_coc
    if has_coc:
        points += PROVENANCE_POINTS["has_code_of_conduct"]

    # unique_description
    desc = (server.get("description") or "").lower().strip()
    is_template = any(desc.startswith(t) for t in TEMPLATE_DESCRIPTIONS)
    unique_desc = bool(desc) and not is_template
    signals["unique_description"] = unique_desc
    if unique_desc:
        points += PROVENANCE_POINTS["unique_description"]

    return (min(points, 100), signals)


# ---------------------------------------------------------------------------
# Maintenance (25%)
# ---------------------------------------------------------------------------


def score_maintenance(
    server: ServerEntry, github: GitHubData | None
) -> tuple[int, dict]:
    """Score maintenance signals. Returns (score 0-100, signals dict)."""
    signals: dict[str, Any] = {}
    points = 0.0

    # repo_age_over_90d
    age_days = (
        _days_since(github.get("github_created_at")) if github is not None else None
    )
    aged = age_days is not None and age_days > 90
    signals["repo_age_over_90d"] = aged
    if aged:
        points += 10

    # last_push_recency — linear scale
    push_days = (
        _days_since(github.get("github_pushed_at")) if github is not None else None
    )
    if push_days is not None:
        if push_days <= PUSH_RECENCY_FULL_DAYS:
            recency_frac = 1.0
        elif push_days >= PUSH_RECENCY_MAX_DAYS:
            recency_frac = 0.0
        else:
            recency_frac = 1.0 - (push_days - PUSH_RECENCY_FULL_DAYS) / (
                PUSH_RECENCY_MAX_DAYS - PUSH_RECENCY_FULL_DAYS
            )
    else:
        recency_frac = 0.0
    signals["last_push_recency"] = round(recency_frac, 3)
    points += recency_frac * 25

    # active_commit_weeks — linear (max 52)
    commit_weeks = (
        github.get("github_commit_weeks_active") if github is not None else None
    )
    if commit_weeks is not None and commit_weeks > 0:
        weeks_frac = min(commit_weeks / 52, 1.0)
    else:
        weeks_frac = 0.0
    signals["active_commit_weeks"] = commit_weeks
    points += weeks_frac * 20

    # contributor_count — tiered
    contributors = (
        github.get("github_contributors") if github is not None else None
    )
    contrib_frac = 0.0
    if contributors is not None:
        for threshold, frac in CONTRIBUTOR_TIERS:
            if contributors >= threshold:
                contrib_frac = frac
                break
    signals["contributor_count"] = contributors
    points += contrib_frac * 15

    # version_count — v0.1 stub: server exists = 1 version = 5 pts
    signals["version_count"] = 1
    points += 5

    # releases_past_year — use commit_weeks as proxy
    if commit_weeks is not None:
        if commit_weeks > 26:
            release_pts = 15
        elif commit_weeks > 13:
            release_pts = 10
        elif commit_weeks > 4:
            release_pts = 5
        else:
            release_pts = 0
    else:
        release_pts = 0
    signals["releases_past_year"] = release_pts
    points += release_pts

    return (min(round(points), 100), signals)


# ---------------------------------------------------------------------------
# Popularity (20%)
# ---------------------------------------------------------------------------


def score_popularity(
    server: ServerEntry, github: GitHubData | None
) -> tuple[int, dict]:
    """Score popularity via GitHub metrics (v0.1, no npm/pypi).

    Returns (score 0-100, signals dict).
    """
    signals: dict[str, Any] = {}

    if github is None:
        signals["github_stars"] = 0
        signals["github_forks"] = 0
        signals["github_watchers"] = 0
        return (0, signals)

    pts = POPULARITY_GITHUB_ONLY_POINTS

    stars = github.get("github_stars", 0) or 0
    star_frac = _bracket_score(stars, STARS_LOG_BRACKETS)
    signals["github_stars"] = stars

    forks = github.get("github_forks", 0) or 0
    fork_frac = _bracket_score(forks, FORKS_LOG_BRACKETS)
    signals["github_forks"] = forks

    watchers = github.get("github_watchers", 0) or 0
    watcher_frac = _bracket_score(watchers, WATCHERS_LOG_BRACKETS)
    signals["github_watchers"] = watchers

    total = (
        star_frac * pts["github_stars"]
        + fork_frac * pts["github_forks"]
        + watcher_frac * pts["github_watchers"]
    )

    return (min(round(total), 100), signals)


# ---------------------------------------------------------------------------
# Permissions (25%) — inverse risk scoring
# ---------------------------------------------------------------------------


def score_permissions(
    server: ServerEntry, github: GitHubData | None
) -> tuple[int, dict]:
    """Score permissions risk (higher = safer). Returns (score 0-100, signals dict)."""
    signals: dict[str, Any] = {}
    points = 0

    env_vars = server.get("env_vars") or []

    # --- secret_env_var_count ---
    secret_count = sum(1 for ev in env_vars if ev.get("is_secret"))
    signals["secret_env_var_count"] = secret_count
    secret_score_map = {0: 40, 1: 30, 2: 20, 3: 10}
    points += secret_score_map.get(secret_count, 0)

    # --- transport_type_risk ---
    transport_types = server.get("transport_types") or []
    if not transport_types:
        transport_pts = TRANSPORT_RISK_DEFAULT
    elif "stdio" in transport_types and len(transport_types) == 1:
        transport_pts = TRANSPORT_RISK["stdio"]
    elif "stdio" in transport_types:
        # Mixed: stdio + remote
        transport_pts = 15
    else:
        # All remote — pick best (highest score) from known types
        remote_scores = [
            TRANSPORT_RISK.get(t, TRANSPORT_RISK_DEFAULT) for t in transport_types
        ]
        transport_pts = max(remote_scores) if remote_scores else TRANSPORT_RISK_DEFAULT
    signals["transport_type_risk"] = transport_pts
    points += transport_pts

    # --- credential_sensitivity ---
    # Check all env var names. Worst (lowest score) across all vars wins.
    if not env_vars:
        cred_score = 20  # No env vars = safest
    else:
        cred_score = 20  # Start with best; degrade per var
        for ev in env_vars:
            var_name = (ev.get("name") or "").lower()
            if any(pat in var_name for pat in SENSITIVE_CREDENTIAL_PATTERNS):
                cred_score = min(cred_score, 5)
                break  # Can't get worse
            if any(pat in var_name for pat in API_KEY_PATTERNS):
                cred_score = min(cred_score, 15)
    signals["credential_sensitivity"] = cred_score
    points += cred_score

    # --- package_type_risk ---
    pkg_types = server.get("package_types") or []
    if not pkg_types:
        pkg_score = PACKAGE_TYPE_RISK_DEFAULT
    else:
        # Pick best (highest) risk score from known package types
        pkg_scores = [
            PACKAGE_TYPE_RISK.get(t, PACKAGE_TYPE_RISK_DEFAULT) for t in pkg_types
        ]
        pkg_score = max(pkg_scores) if pkg_scores else PACKAGE_TYPE_RISK_DEFAULT
    signals["package_type_risk"] = pkg_score
    points += pkg_score

    return (min(points, 100), signals)
