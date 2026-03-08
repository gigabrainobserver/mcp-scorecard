"""SEO generators: JSON-LD, sitemap, RSS, llms.txt, robots.txt."""
import html
from datetime import datetime

BASE_URL = "https://mcp-scorecard.ai"


# --- JSON-LD Schema Generators ---

def organization_jsonld() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "MCP Scorecard",
        "url": BASE_URL,
        "logo": f"{BASE_URL}/favicon.svg",
        "description": "Independent trust scoring for the MCP server ecosystem.",
    }


def website_jsonld() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "MCP Scorecard",
        "url": BASE_URL,
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{BASE_URL}/?q={{search_term_string}}",
            },
            "query-input": "required name=search_term_string",
        },
    }


def software_application_jsonld(name: str, server: dict, canonical_path: str) -> dict:
    ns = name.split("/")[0]
    server_id = "/".join(name.split("/")[1:])
    score = server.get("trust_score", 0)
    install = server.get("install", {})

    result: dict = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": server_id,
        "applicationCategory": "MCP Server",
        "url": BASE_URL + canonical_path,
        "author": {
            "@type": "Organization",
            "name": ns,
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": str(score),
            "bestRating": "100",
            "worstRating": "0",
            "ratingCount": "1",
        },
    }

    repo_url = install.get("repo_url") or (server.get("signals") or {}).get("repo_url")
    if repo_url:
        result["codeRepository"] = repo_url

    license_id = (server.get("signals") or {}).get("github_license")
    if license_id and license_id != "NOASSERTION":
        result["license"] = license_id

    return result


def blog_posting_jsonld(post: dict, canonical_path: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post.get("title", ""),
        "description": post.get("summary", ""),
        "datePublished": post.get("date", ""),
        "url": BASE_URL + canonical_path,
        "author": {
            "@type": "Organization",
            "name": "MCP Scorecard",
            "url": BASE_URL,
        },
        "publisher": {
            "@type": "Organization",
            "name": "MCP Scorecard",
            "url": BASE_URL,
            "logo": {
                "@type": "ImageObject",
                "url": f"{BASE_URL}/favicon.svg",
            },
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": BASE_URL + canonical_path,
        },
    }


def breadcrumb_jsonld(crumbs: list[tuple[str, str]]) -> dict:
    items = []
    for i, (label, url) in enumerate(crumbs, 1):
        items.append({
            "@type": "ListItem",
            "position": i,
            "name": label,
            "item": BASE_URL + url if not url.startswith("http") else url,
        })
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }


# --- Sitemap ---

def generate_sitemap(urls: list[dict]) -> str:
    """Generate XML sitemap.

    Args:
        urls: List of {loc, lastmod, changefreq, priority}
    """
    entries = []
    for u in urls:
        parts = [f"<loc>{html.escape(BASE_URL + u['loc'])}</loc>"]
        if u.get("lastmod"):
            parts.append(f"<lastmod>{u['lastmod']}</lastmod>")
        if u.get("changefreq"):
            parts.append(f"<changefreq>{u['changefreq']}</changefreq>")
        if u.get("priority"):
            parts.append(f"<priority>{u['priority']}</priority>")
        entries.append(f"<url>{''.join(parts)}</url>")

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries) + "\n"
        '</urlset>'
    )


# --- RSS ---

def generate_rss(posts: list[dict]) -> str:
    """Generate RSS 2.0 feed for blog posts."""
    items = []
    for p in posts:
        title = html.escape(p.get("title", ""))
        link = f"{BASE_URL}/blog/{p.get('slug', '')}/"
        desc = html.escape(p.get("summary", ""))
        # Convert YYYY-MM-DD to RFC 822
        try:
            dt = datetime.strptime(p.get("date", ""), "%Y-%m-%d")
            pub_date = dt.strftime("%a, %d %b %Y 00:00:00 +0000")
        except ValueError:
            pub_date = ""
        items.append(
            f"<item>"
            f"<title>{title}</title>"
            f"<link>{link}</link>"
            f"<description>{desc}</description>"
            f"<pubDate>{pub_date}</pubDate>"
            f"<guid>{link}</guid>"
            f"</item>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '<channel>\n'
        f'<title>MCP Scorecard Blog</title>\n'
        f'<link>{BASE_URL}/blog/</link>\n'
        f'<description>Analysis and reporting on the MCP server ecosystem.</description>\n'
        f'<atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>\n'
        + "\n".join(items) + "\n"
        '</channel>\n'
        '</rss>'
    )


# --- llms.txt ---

def generate_llms_txt(server_count: int) -> str:
    return f"""# MCP Scorecard
> Trust scoring index for {server_count:,}+ MCP (Model Context Protocol) servers.

## About
MCP Scorecard provides independent, transparent trust scores for every MCP server in the ecosystem. Scores range 0-100 across provenance, maintenance, popularity, and permissions.

## Key Pages
- /about/ — Mission, methodology, scoring model
- /blog/ — Analysis articles, ecosystem pulse reports
- /publishers/ — Browse by publisher namespace
- /platforms/ — Browse by target platform
- /api/ — REST API documentation (free tier: 100 req/day)

## API
Base URL: https://api.mcp-scorecard.ai/v1
- GET /v1/servers — Paginated server list
- GET /v1/servers/:name — Individual server detail
- GET /v1/search?q= — Full-text search
- GET /v1/stats — Ecosystem statistics

## Contact
Website: https://mcp-scorecard.ai
GitHub: https://github.com/gigabrainobserver/mcp-scorecard
"""


# --- robots.txt ---

def generate_robots_txt() -> str:
    return f"""User-agent: *
Allow: /

Sitemap: {BASE_URL}/sitemap.xml
"""
