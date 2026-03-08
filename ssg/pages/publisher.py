"""Generate static publisher detail pages."""
import html
from pathlib import Path

from ssg.render import (
    render_stats_bar, render_flag_summary, render_server_row,
    render_related_articles, VERIFIED_SVG_20,
)
from ssg.templates import base_page, breadcrumb_nav, TOGGLE_DETAIL_JS
from ssg.seo import breadcrumb_jsonld, organization_jsonld


PUBLISHER_PAGE_CSS = """
  .pub-hero { padding: 32px 32px 24px; border-bottom: 1px solid #21262d; }
  .pub-name { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .pub-name h2 { font-size: 24px; font-weight: 700; }
  .pub-name .verified-label { font-size: 12px; color: #58a6ff; font-weight: 600; }
  .pub-links { display: flex; gap: 16px; font-size: 13px; }
  .pub-links a { color: #58a6ff; text-decoration: none; }
  .pub-links a:hover { text-decoration: underline; }
  .articles { padding: 24px 32px; border-top: 1px solid #21262d; }
  .articles-label { font-size: 13px; font-weight: 600; color: #7d8590; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
  .article-card { display: block; padding: 10px 14px; border: 1px solid #21262d; border-radius: 6px; margin-bottom: 8px; text-decoration: none; transition: border-color 0.15s; }
  .article-card:hover { border-color: #58a6ff; text-decoration: none; }
  .article-card-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
  .article-tag { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 1px 6px; border-radius: 3px; }
  .article-tag-pulse { background: rgba(88,166,255,0.15); color: #58a6ff; }
  .article-tag-spotlight { background: rgba(63,185,80,0.15); color: #3fb950; }
  .article-tag-trend { background: rgba(210,153,34,0.15); color: #d29922; }
  .article-tag-investigation { background: rgba(248,81,73,0.15); color: #f85149; }
  .article-tag-interview { background: rgba(163,113,247,0.15); color: #a371f7; }
  .article-title { font-size: 14px; font-weight: 600; color: #e6edf3; }
  .article-date { font-size: 11px; color: #484f58; }
  .article-summary { font-size: 12px; color: #7d8590; line-height: 1.4; }
"""


def generate_publisher_pages(
    site_dir: Path,
    publishers: dict,
    sitemap_urls: list[dict],
    lastmod: str,
) -> int:
    """Generate individual publisher pages. Returns count."""
    count = 0

    for ns, pub in publishers.items():
        canonical_path = f"/publisher/{ns}/"
        servers = pub["servers"]
        avg_score = pub["avg_score"]
        total_stars = pub["total_stars"]
        bands = pub["bands"]
        flag_counts = pub["flag_counts"]
        verified = pub["verified"]
        related_posts = pub["related_posts"]

        ns_esc = html.escape(ns)

        # Derive GitHub org link from first server with a repo
        org_url = None
        for sname, s in servers:
            repo = (s.get("signals") or {}).get("repo_url", "")
            if repo and "github.com/" in repo:
                owner = repo.replace("https://github.com/", "").split("/")[0]
                if owner:
                    org_url = f"https://github.com/{owner}"
                    break

        # Hero
        verified_html = ""
        if verified:
            verified_html = (
                f'<span class="verified-badge" title="Verified Publisher">{VERIFIED_SVG_20}</span>'
                '<span class="verified-label">Verified Publisher</span>'
            )

        links = []
        if org_url:
            links.append(f'<a href="{html.escape(org_url)}" target="_blank" rel="noopener">GitHub</a>')
        links.append(f'<a href="/">View in main listing</a>')

        hero_html = (
            '<div class="pub-hero">'
            f'<div class="pub-name"><h2>{ns_esc}</h2>{verified_html}</div>'
            f'<div class="pub-links">{"".join(links)}</div>'
            '</div>'
        )

        # Stats bar
        stats_html = render_stats_bar(
            len(servers), bands, avg_score=avg_score,
            total_stars=total_stars, mode="publisher"
        )

        # Flag summary
        flag_html = render_flag_summary(flag_counts)

        # Server list
        rows = []
        for i, (sname, s) in enumerate(servers):
            rows.append(render_server_row(sname, s, i, show_ns=False))
        list_html = f'<div class="list">{"".join(rows)}</div>'

        # Related articles
        articles_html = render_related_articles(related_posts)

        # Breadcrumbs
        crumbs = [("Home", "/"), ("Publishers", "/publishers/"), (ns, canonical_path)]

        # JSON-LD
        json_ld = [
            organization_jsonld(),
            breadcrumb_jsonld(crumbs),
        ]

        body_html = (
            breadcrumb_nav(crumbs)
            + hero_html
            + stats_html
            + flag_html
            + list_html
            + articles_html
        )

        page_html = base_page(
            title=f"{ns} MCP Servers — Trust Scores | MCP Scorecard",
            description=f"{len(servers)} MCP servers by {ns}. Average trust score: {avg_score}/100. Browse trust scores and security review.",
            canonical_path=canonical_path,
            body_html=body_html,
            json_ld=json_ld,
            page_css=PUBLISHER_PAGE_CSS,
            active_nav="publishers",
            extra_js=TOGGLE_DETAIL_JS,
        )

        out_path = site_dir / "publisher" / ns / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page_html, encoding="utf-8")

        sitemap_urls.append({"loc": canonical_path, "lastmod": lastmod, "changefreq": "weekly", "priority": "0.4"})
        count += 1

    return count
