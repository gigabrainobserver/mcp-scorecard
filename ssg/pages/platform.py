"""Generate static platform detail pages."""
import html
from pathlib import Path

from ssg.render import (
    render_stats_bar, render_flag_summary, render_server_row,
)
from ssg.templates import base_page, breadcrumb_nav, TOGGLE_DETAIL_JS
from ssg.seo import breadcrumb_jsonld, organization_jsonld


PLATFORM_PAGE_CSS = """
  .plat-hero { padding: 32px 32px 24px; border-bottom: 1px solid #21262d; }
  .plat-hero h2 { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
  .plat-hero .plat-desc { font-size: 14px; color: #7d8590; }
"""


def generate_platform_pages(
    site_dir: Path,
    platforms: dict,
    sitemap_urls: list[dict],
    lastmod: str,
) -> int:
    """Generate individual platform pages. Returns count."""
    count = 0

    for target_name, plat in platforms.items():
        slug = plat["slug"]
        canonical_path = f"/platform/{slug}/"
        servers = plat["servers"]
        avg_score = plat["avg_score"]
        bands = plat["bands"]
        flag_counts = plat["flag_counts"]
        server_count = plat["server_count"]

        name_esc = html.escape(target_name)

        # Hero
        hero_html = (
            '<div class="plat-hero">'
            f'<h2>{name_esc} MCP Servers</h2>'
            f'<div class="plat-desc">{server_count} servers targeting {name_esc}</div>'
            '</div>'
        )

        # Stats bar
        stats_html = render_stats_bar(
            server_count, bands, avg_score=avg_score,
            total_stars=0, mode="publisher"
        )

        # Flag summary
        flag_html = render_flag_summary(flag_counts)

        # Server list
        rows = []
        for i, (sname, s) in enumerate(servers):
            rows.append(render_server_row(sname, s, i, show_ns=True))
        list_html = f'<div class="list">{"".join(rows)}</div>'

        # Breadcrumbs
        crumbs = [("Home", "/"), ("Platforms", "/platforms/"), (target_name, canonical_path)]

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
        )

        page_html = base_page(
            title=f"{target_name} MCP Servers — Trust Scores | MCP Scorecard",
            description=f"{server_count} MCP servers for {target_name}. Trust scores and security review.",
            canonical_path=canonical_path,
            body_html=body_html,
            json_ld=json_ld,
            page_css=PLATFORM_PAGE_CSS,
            active_nav="platforms",
            extra_js=TOGGLE_DETAIL_JS,
        )

        out_path = site_dir / "platform" / slug / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page_html, encoding="utf-8")

        sitemap_urls.append({"loc": canonical_path, "lastmod": lastmod, "changefreq": "weekly", "priority": "0.5"})
        count += 1

    return count
