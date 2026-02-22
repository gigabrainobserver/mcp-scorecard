"""Badge generation — structured, contextual signal groups.

Converts raw signals and flags into presentational badge groups:
- Security: red flags and permission concerns
- Provenance: identity and source verification
- Activity: state-based maturity indicators
- Popularity: adoption metrics
"""

from __future__ import annotations

from typing import Any

ServerEntry = dict[str, Any]
GitHubData = dict[str, Any]

# Flag severity mapping
_FLAG_SEVERITY = {
    "DEAD_ENTRY": "critical",
    "NO_SOURCE": "critical",
    "SENSITIVE_CRED_REQUEST": "critical",
    "HIGH_SECRET_DEMAND": "warning",
    "STAGING_ARTIFACT": "warning",
    "REPO_ARCHIVED": "warning",
    "TEMPLATE_DESCRIPTION": "info",
    "DESCRIPTION_DUPLICATE": "info",
}

# Human-readable flag labels
_FLAG_LABELS = {
    "DEAD_ENTRY": "Dead Entry",
    "NO_SOURCE": "No Source",
    "SENSITIVE_CRED_REQUEST": "Sensitive Creds",
    "HIGH_SECRET_DEMAND": "Many Secrets",
    "STAGING_ARTIFACT": "Staging Artifact",
    "REPO_ARCHIVED": "Archived",
    "TEMPLATE_DESCRIPTION": "Template Desc",
    "DESCRIPTION_DUPLICATE": "Duplicate Desc",
}

# Provenance signal → display label
_PROVENANCE_SIGNALS = [
    ("has_source_repo", "Source Repo"),
    ("has_license", "License"),
    ("has_installable_package", "Package"),
    ("namespace_matches_owner", "NS Match"),
    ("repo_not_archived", "Active Repo"),
    ("has_website_url", "Website"),
    ("has_icon", "Icon"),
    ("has_security_md", "SECURITY.md"),
    ("has_code_of_conduct", "Code of Conduct"),
    ("unique_description", "Unique Desc"),
]


def generate_badges(
    signals: dict[str, Any],
    flags: list[str],
    server: ServerEntry,
    github: GitHubData | None,
) -> dict[str, Any]:
    """Generate badge groups from scoring signals, flags, and raw data."""
    return {
        "security": _security_badges(signals, flags, server),
        "provenance": _provenance_badges(signals),
        "activity": _activity_badges(signals, github),
        "popularity": _popularity_metrics(signals),
    }


def _security_badges(
    signals: dict, flags: list[str], server: ServerEntry
) -> list[dict]:
    """Red flags and permission concerns."""
    badges: list[dict] = []

    # Red flags as badges
    for flag in flags:
        badges.append({
            "key": flag,
            "type": "flag",
            "label": _FLAG_LABELS.get(flag, flag),
            "severity": _FLAG_SEVERITY.get(flag, "info"),
        })

    # Secret count
    secret_count = signals.get("secret_env_var_count", 0)
    if secret_count == 0:
        val, level = "none", "good"
    elif secret_count <= 2:
        val, level = str(secret_count), "neutral"
    elif secret_count <= 4:
        val, level = str(secret_count), "warning"
    else:
        val, level = str(secret_count), "critical"
    badges.append({
        "key": "secrets",
        "type": "enum",
        "label": "Secrets",
        "value": val,
        "level": level,
    })

    # Transport type — use actual types from server entry
    transport_types = server.get("transport_types") or []
    if not transport_types:
        t_val, t_level = "unknown", "neutral"
    elif transport_types == ["stdio"]:
        t_val, t_level = "stdio", "good"
    elif "stdio" in transport_types:
        t_val, t_level = "stdio + remote", "neutral"
    else:
        t_val, t_level = "remote", "neutral"
    badges.append({
        "key": "transport",
        "type": "enum",
        "label": "Transport",
        "value": t_val,
        "level": t_level,
    })

    # Credential sensitivity
    cred_pts = signals.get("credential_sensitivity", 20)
    if cred_pts >= 20:
        c_val, c_level = "none", "good"
    elif cred_pts >= 15:
        c_val, c_level = "API keys", "neutral"
    else:
        c_val, c_level = "sensitive", "critical"
    badges.append({
        "key": "credentials",
        "type": "enum",
        "label": "Credentials",
        "value": c_val,
        "level": c_level,
    })

    return badges


def _provenance_badges(signals: dict) -> list[dict]:
    """Identity and source verification badges (all boolean)."""
    return [
        {
            "key": key,
            "type": "bool",
            "label": label,
            "value": bool(signals.get(key, False)),
        }
        for key, label in _PROVENANCE_SIGNALS
    ]


def _activity_badges(signals: dict, github: GitHubData | None) -> list[dict]:
    """State-based maturity indicators (enum badges)."""
    badges: list[dict] = []

    # Repo age — derive from github data for granularity
    if github and github.get("github_created_at"):
        from mcp_scorecard.scoring.categories import _days_since

        age_days = _days_since(github.get("github_created_at"))
        if age_days is not None:
            if age_days > 365:
                val, level = "> 1 year", "good"
            elif age_days > 90:
                val, level = "> 90 days", "good"
            elif age_days > 30:
                val, level = "> 30 days", "neutral"
            else:
                val, level = "< 30 days", "new"
        else:
            val, level = "unknown", "neutral"
    else:
        val, level = "no repo", "neutral"
    badges.append({
        "key": "repo_age",
        "type": "enum",
        "label": "Repo Age",
        "value": val,
        "level": level,
    })

    # Last push recency — derive from the 0-1 fraction in signals
    recency = signals.get("last_push_recency")
    if recency is not None and recency > 0:
        if recency >= 0.9:  # ~within 30 days
            val, level = "< 30 days", "good"
        elif recency >= 0.5:  # ~within 6 months
            val, level = "< 6 months", "neutral"
        else:  # within a year but old
            val, level = "< 1 year", "warning"
    elif recency is not None:
        val, level = "> 1 year", "critical"
    else:
        val, level = "unknown", "neutral"
    badges.append({
        "key": "last_push",
        "type": "enum",
        "label": "Last Push",
        "value": val,
        "level": level,
    })

    # Commit frequency
    weeks = signals.get("active_commit_weeks")
    if weeks is not None:
        if weeks >= 27:
            val, level = "active", "good"
        elif weeks >= 5:
            val, level = "regular", "neutral"
        elif weeks >= 1:
            val, level = "sporadic", "warning"
        else:
            val, level = "dormant", "critical"
    else:
        val, level = "unknown", "neutral"
    badges.append({
        "key": "commit_activity",
        "type": "enum",
        "label": "Commits",
        "value": val,
        "level": level,
    })

    # Contributors
    contribs = signals.get("contributor_count")
    if contribs is not None:
        if contribs >= 10:
            val, level = "community", "good"
        elif contribs >= 4:
            val, level = "team", "good"
        elif contribs >= 2:
            val, level = "small", "neutral"
        else:
            val, level = "solo", "neutral"
    else:
        val, level = "unknown", "neutral"
    badges.append({
        "key": "contributors",
        "type": "enum",
        "label": "Contributors",
        "value": val,
        "level": level,
    })

    return badges


def _popularity_metrics(signals: dict) -> dict:
    """Adoption metrics — raw numbers, not badges."""
    return {
        "stars": signals.get("github_stars", 0),
        "forks": signals.get("github_forks", 0),
        "watchers": signals.get("github_watchers", 0),
    }
