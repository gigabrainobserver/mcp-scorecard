"""Generate static top/listicle pages."""
import html
from pathlib import Path

from ssg.render import render_server_row, render_score_pill, score_class, fmt_num
from ssg.templates import base_page, breadcrumb_nav, TOGGLE_DETAIL_JS
from ssg.seo import breadcrumb_jsonld, organization_jsonld


TOP_PAGE_CSS = """
  .top-hero { padding: 32px 32px 24px; border-bottom: 1px solid #21262d; }
  .top-hero h2 { font-size: 24px; font-weight: 700; margin-bottom: 8px; }
  .top-hero .top-desc { font-size: 14px; color: #7d8590; line-height: 1.5; max-width: 640px; }
  .top-nav { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
  .top-nav a { padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; text-decoration: none; border: 1px solid #30363d; color: #8b949e; }
  .top-nav a:hover { border-color: #58a6ff; color: #58a6ff; text-decoration: none; }
  .top-nav a.active { border-color: #58a6ff; color: #58a6ff; }
"""


def generate_top_pages(
    site_dir: Path,
    servers: dict,
    sitemap_urls: list[dict],
    lastmod: str,
) -> int:
    """Generate /top/{category}/ pages. Returns count."""
    # Build the top lists
    all_sorted = sorted(servers.items(), key=lambda x: x[1].get("trust_score", 0), reverse=True)

    top_lists = {
        "overall": {
            "title": "Top 25 Most Trusted MCP Servers",
            "desc": "The 25 highest-scoring MCP servers by trust score. Updated with each pipeline run.",
            "entries": all_sorted[:25],
        },
        "verified": {
            "title": "Verified Publisher Servers",
            "desc": "MCP servers from verified publishers, sorted by trust score.",
            "entries": [(n, s) for n, s in all_sorted if s.get("verified_publisher")][:50],
        },
        "github-stars": {
            "title": "Top MCP Servers by GitHub Stars",
            "desc": "The most popular MCP servers ranked by GitHub stars.",
            "entries": sorted(
                [(n, s) for n, s in servers.items()
                 if (s.get("badges", {}).get("popularity", {}).get("stars", 0) or 0) > 0],
                key=lambda x: x[1].get("badges", {}).get("popularity", {}).get("stars", 0),
                reverse=True,
            )[:50],
        },
        "new": {
            "title": "Recently Added MCP Servers",
            "desc": "The newest MCP servers added to the registry, sorted by trust score.",
            "entries": [(n, s) for n, s in all_sorted
                        if any(b.get("level") == "new" for b in s.get("badges", {}).get("activity", []))][:50],
        },
    }

    # Navigation
    nav_items = [
        ("overall", "Top 25"),
        ("verified", "Verified"),
        ("github-stars", "Most Stars"),
        ("new", "Newest"),
    ]

    count = 0
    for slug, data in top_lists.items():
        canonical_path = f"/top/{slug}/"
        entries = data["entries"]
        if not entries:
            continue

        nav_links = []
        for nav_slug, nav_label in nav_items:
            active = ' class="active"' if nav_slug == slug else ""
            nav_links.append(f'<a href="/top/{nav_slug}/"{active}>{nav_label}</a>')

        hero_html = (
            '<div class="top-hero">'
            f'<h2>{html.escape(data["title"])}</h2>'
            f'<div class="top-desc">{html.escape(data["desc"])}</div>'
            f'<div class="top-nav">{"".join(nav_links)}</div>'
            '</div>'
        )

        rows = []
        for i, (sname, s) in enumerate(entries):
            rows.append(render_server_row(sname, s, i, show_ns=True))
        list_html = f'<div class="list">{"".join(rows)}</div>'

        crumbs = [("Home", "/"), ("Top Lists", "/top/overall/"), (data["title"], canonical_path)]

        json_ld = [
            organization_jsonld(),
            breadcrumb_jsonld(crumbs),
        ]

        body_html = breadcrumb_nav(crumbs) + hero_html + list_html

        page_html = base_page(
            title=f"{data['title']} | MCP Scorecard",
            description=data["desc"],
            canonical_path=canonical_path,
            body_html=body_html,
            json_ld=json_ld,
            page_css=TOP_PAGE_CSS,
            active_nav="servers",
            extra_js=TOGGLE_DETAIL_JS,
        )

        out_path = site_dir / "top" / slug / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page_html, encoding="utf-8")

        sitemap_urls.append({"loc": canonical_path, "lastmod": lastmod, "changefreq": "weekly", "priority": "0.6"})
        count += 1

    return count
