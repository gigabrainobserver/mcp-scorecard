"""Infer platform targets from server name and namespace."""

from __future__ import annotations

import re

# Canonical platform name → keywords to match in server name/namespace.
# Order matters: longer/more-specific patterns first to avoid partial matches.
PLATFORM_KEYWORDS: dict[str, list[str]] = {
    # Services
    "GitHub": ["github"],
    "Slack": ["slack"],
    "Notion": ["notion"],
    "Google Calendar": ["google-calendar", "gcal", "google_calendar"],
    "Google Docs": ["google-docs", "google_docs", "googledocs"],
    "Google Sheets": ["google-sheets", "google_sheets", "googlesheets"],
    "Google Drive": ["google-drive", "google_drive", "googledrive", "gdrive"],
    "Gmail": ["gmail"],
    "Jira": ["jira"],
    "Confluence": ["confluence"],
    "Linear": ["linear"],
    "Discord": ["discord"],
    "Telegram": ["telegram"],
    "Twitter/X": ["twitter", "x-mcp"],
    "Trello": ["trello"],
    "Asana": ["asana"],
    "ClickUp": ["clickup"],
    "Salesforce": ["salesforce"],
    "HubSpot": ["hubspot"],
    "Stripe": ["stripe"],
    "Shopify": ["shopify"],
    "Airtable": ["airtable"],
    "YouTube": ["youtube"],
    "Spotify": ["spotify"],
    "Obsidian": ["obsidian"],
    "WordPress": ["wordpress"],
    "Todoist": ["todoist"],
    # Databases
    "PostgreSQL": ["postgres", "postgresql", "pg-mcp"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb", "mongo"],
    "SQLite": ["sqlite"],
    "Redis": ["redis"],
    "Elasticsearch": ["elasticsearch", "elastic"],
    "Supabase": ["supabase"],
    "Firebase": ["firebase"],
    "Neo4j": ["neo4j"],
    "Pinecone": ["pinecone"],
    "Qdrant": ["qdrant"],
    "ChromaDB": ["chroma"],
    "Weaviate": ["weaviate"],
    # Infra
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws"],
    "Azure": ["azure"],
    "Cloudflare": ["cloudflare"],
    "Vercel": ["vercel"],
    "Terraform": ["terraform"],
    # Dev Tools
    "Git": [],  # too generic — handled as special case
    "Puppeteer": ["puppeteer"],
    "Playwright": ["playwright"],
    "Sentry": ["sentry"],
    "Datadog": ["datadog"],
    "Grafana": ["grafana"],
    "GitLab": ["gitlab"],
    "Bitbucket": ["bitbucket"],
}

# Namespace prefixes that are hosting platforms, not targets.
# e.g. io.github.user/slack-mcp → "github" in namespace is NOT a target.
_HOSTING_NS_PREFIXES = ("io.github.", "ai.smithery")

# Known namespace → platform mappings (e.g. com.notion/mcp → Notion).
_NS_PLATFORMS: dict[str, str] = {
    "com.notion": "Notion",
    "com.stripe": "Stripe",
    "com.supabase": "Supabase",
    "app.linear": "Linear",
    "com.gitlab": "GitLab",
    "com.shopify": "Shopify",
    "com.microsoft": "Azure",
}


def infer_targets(name: str) -> list[str]:
    """Return a list of platform target names for a server.

    Args:
        name: Full server name like "io.github.user/slack-mcp-server".
    """
    parts = name.split("/", 1)
    ns = parts[0] if len(parts) == 2 else ""
    server_id = (parts[1] if len(parts) == 2 else name).lower()

    # Build the text to match against.
    # Exclude hosting namespace prefixes from matching.
    ns_lower = ns.lower()
    ns_for_match = ""
    if not any(ns_lower.startswith(p) for p in _HOSTING_NS_PREFIXES):
        ns_for_match = ns_lower

    match_text = f"{ns_for_match} {server_id}"

    targets: list[str] = []

    # Check namespace-based platforms first
    for ns_key, platform in _NS_PLATFORMS.items():
        if ns_lower == ns_key:
            targets.append(platform)

    # Keyword matching
    for platform, keywords in PLATFORM_KEYWORDS.items():
        if platform in targets:
            continue
        for kw in keywords:
            # Word-boundary match to avoid partial matches
            # e.g. "linear" shouldn't match "bilinear"
            if re.search(rf'(?:^|[-_./\s]){re.escape(kw)}(?:[-_./\s]|$)', match_text):
                targets.append(platform)
                break

    # Special case: "Git" (too generic) — only match exact patterns
    if "Git" not in targets:
        if re.search(r'(?:^|[-_./\s])git(?:[-_./\s]|$)', server_id) and not any(
            p in targets for p in ("GitHub", "GitLab", "Bitbucket")
        ):
            targets.append("Git")

    return targets
