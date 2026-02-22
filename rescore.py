"""Quick rescore — adds badges to existing index.json without re-collecting/enriching.

Usage: python rescore.py
"""

import json
from pathlib import Path


def generate_badges_from_signals(signals: dict, flags: list[str]) -> dict:
    """Generate badge groups from existing signal values and flags."""

    # --- Security ---
    security = []

    FLAG_SEVERITY = {
        "DEAD_ENTRY": "critical",
        "NO_SOURCE": "critical",
        "SENSITIVE_CRED_REQUEST": "critical",
        "HIGH_SECRET_DEMAND": "warning",
        "STAGING_ARTIFACT": "warning",
        "REPO_ARCHIVED": "warning",
        "TEMPLATE_DESCRIPTION": "info",
        "DESCRIPTION_DUPLICATE": "info",
    }
    FLAG_LABELS = {
        "DEAD_ENTRY": "Dead Entry",
        "NO_SOURCE": "No Source",
        "SENSITIVE_CRED_REQUEST": "Sensitive Creds",
        "HIGH_SECRET_DEMAND": "Many Secrets",
        "STAGING_ARTIFACT": "Staging Artifact",
        "REPO_ARCHIVED": "Archived",
        "TEMPLATE_DESCRIPTION": "Template Desc",
        "DESCRIPTION_DUPLICATE": "Duplicate Desc",
    }

    for flag in flags:
        security.append({
            "key": flag,
            "type": "flag",
            "label": FLAG_LABELS.get(flag, flag),
            "severity": FLAG_SEVERITY.get(flag, "info"),
        })

    # Secrets
    sc = signals.get("secret_env_var_count", 0)
    if sc == 0:
        val, lvl = "none", "good"
    elif sc <= 2:
        val, lvl = str(sc), "neutral"
    elif sc <= 4:
        val, lvl = str(sc), "warning"
    else:
        val, lvl = str(sc), "critical"
    security.append({"key": "secrets", "type": "enum", "label": "Secrets", "value": val, "level": lvl})

    # Transport — reverse from point value
    tp = signals.get("transport_type_risk", 5)
    if tp >= 25:
        t_val, t_lvl = "stdio", "good"
    elif tp >= 15:
        t_val, t_lvl = "stdio + remote", "neutral"
    elif tp >= 10:
        t_val, t_lvl = "remote", "neutral"
    else:
        t_val, t_lvl = "unknown", "neutral"
    security.append({"key": "transport", "type": "enum", "label": "Transport", "value": t_val, "level": t_lvl})

    # Credentials
    cp = signals.get("credential_sensitivity", 20)
    if cp >= 20:
        c_val, c_lvl = "none", "good"
    elif cp >= 15:
        c_val, c_lvl = "API keys", "neutral"
    else:
        c_val, c_lvl = "sensitive", "critical"
    security.append({"key": "credentials", "type": "enum", "label": "Credentials", "value": c_val, "level": c_lvl})

    # --- Provenance ---
    PROV = [
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
    provenance = [
        {"key": k, "type": "bool", "label": l, "value": bool(signals.get(k, False))}
        for k, l in PROV
    ]

    # --- Activity ---
    activity = []

    # Repo age — only have boolean, use what we have
    aged = signals.get("repo_age_over_90d", False)
    if aged:
        val, lvl = "> 90 days", "good"
    elif signals.get("has_source_repo", False):
        val, lvl = "< 90 days", "new"
    else:
        val, lvl = "no repo", "neutral"
    activity.append({"key": "repo_age", "type": "enum", "label": "Repo Age", "value": val, "level": lvl})

    # Last push
    rec = signals.get("last_push_recency")
    if rec is not None and rec > 0:
        if rec >= 0.9:
            val, lvl = "< 30 days", "good"
        elif rec >= 0.5:
            val, lvl = "< 6 months", "neutral"
        else:
            val, lvl = "< 1 year", "warning"
    elif rec is not None:
        val, lvl = "> 1 year", "critical"
    else:
        val, lvl = "unknown", "neutral"
    activity.append({"key": "last_push", "type": "enum", "label": "Last Push", "value": val, "level": lvl})

    # Commits
    weeks = signals.get("active_commit_weeks")
    if weeks is not None:
        if weeks >= 27:
            val, lvl = "active", "good"
        elif weeks >= 5:
            val, lvl = "regular", "neutral"
        elif weeks >= 1:
            val, lvl = "sporadic", "warning"
        else:
            val, lvl = "dormant", "critical"
    else:
        val, lvl = "unknown", "neutral"
    activity.append({"key": "commit_activity", "type": "enum", "label": "Commits", "value": val, "level": lvl})

    # Contributors
    contribs = signals.get("contributor_count")
    if contribs is not None:
        if contribs >= 10:
            val, lvl = "community", "good"
        elif contribs >= 4:
            val, lvl = "team", "good"
        elif contribs >= 2:
            val, lvl = "small", "neutral"
        else:
            val, lvl = "solo", "neutral"
    else:
        val, lvl = "unknown", "neutral"
    activity.append({"key": "contributors", "type": "enum", "label": "Contributors", "value": val, "level": lvl})

    # --- Popularity ---
    popularity = {
        "stars": signals.get("github_stars", 0),
        "forks": signals.get("github_forks", 0),
        "watchers": signals.get("github_watchers", 0),
    }

    return {
        "security": security,
        "provenance": provenance,
        "activity": activity,
        "popularity": popularity,
    }


def main():
    idx_path = Path("output/index.json")
    data = json.loads(idx_path.read_text())

    for name, server in data["servers"].items():
        server["badges"] = generate_badges_from_signals(
            server["signals"], server["flags"]
        )

    idx_path.write_text(json.dumps(data, indent=2))
    print(f"Added badges to {len(data['servers'])} servers in {idx_path}")


if __name__ == "__main__":
    main()
