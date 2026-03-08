"""Generate static risk band pages."""
import html
from pathlib import Path

from ssg.render import render_server_row, render_stats_bar, render_flag_summary, score_color
from ssg.templates import base_page, breadcrumb_nav, TOGGLE_DETAIL_JS
from ssg.seo import breadcrumb_jsonld, organization_jsonld


RISK_PAGE_CSS = """
  .risk-hero { padding: 32px 32px 24px; border-bottom: 1px solid #21262d; }
  .risk-hero h2 { font-size: 24px; font-weight: 700; margin-bottom: 8px; }
  .risk-range { font-size: 14px; color: #7d8590; margin-bottom: 12px; }
  .risk-desc { font-size: 14px; color: #8b949e; line-height: 1.5; max-width: 640px; }
  .risk-nav { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
  .risk-nav a { padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; text-decoration: none; border: 1px solid #30363d; color: #8b949e; }
  .risk-nav a:hover { border-color: #58a6ff; color: #58a6ff; text-decoration: none; }
  .risk-nav a.active { border-color: currentColor; }
"""

BAND_DESCRIPTIONS = {
    "high": "Servers scoring 80–100 demonstrate strong provenance, active maintenance, meaningful community adoption, and appropriate permission scoping. These are the most trustworthy servers in the MCP ecosystem.",
    "mod": "Servers scoring 60–79 show solid fundamentals — identifiable source code, reasonable maintenance signals — but may lack community validation or have minor permission concerns.",
    "low": "Servers scoring 40–59 have significant gaps in trust signals. They may lack source code visibility, show limited maintenance activity, or request broad permissions without clear justification.",
    "vlow": "Servers scoring 20–39 have multiple trust concerns. Missing source code, no maintenance activity, or problematic permission patterns. Use with caution.",
    "unk": "Servers scoring 0–19 lack nearly all trust signals. Many are dead entries, have no verifiable source, or exhibit patterns consistent with placeholder or test registrations.",
}


def generate_risk_pages(
    site_dir: Path,
    trust_bands: dict,
    sitemap_urls: list[dict],
    lastmod: str,
) -> int:
    """Generate /risk/{band}/ pages. Returns count."""
    count = 0
    band_order = ["high", "mod", "low", "vlow", "unk"]

    for band_key in band_order:
        band = trust_bands[band_key]
        slug = band["slug"]
        label = band["label"]
        servers = band["servers"]
        server_count = band["count"]
        canonical_path = f"/risk/{slug}/"

        color = score_color(band["min"])
        desc = BAND_DESCRIPTIONS.get(band_key, "")

        # Band navigation links
        nav_links = []
        for bk in band_order:
            b = trust_bands[bk]
            active = ' class="active"' if bk == band_key else ""
            nav_links.append(
                f'<a href="/risk/{b["slug"]}/" style="color:{score_color(b["min"])}"{active}>'
                f'{b["label"]} ({b["count"]})</a>'
            )

        hero_html = (
            '<div class="risk-hero">'
            f'<h2 style="color:{color}">{html.escape(label)} Servers</h2>'
            f'<div class="risk-range">Score range: {band["min"]}–{band["max"]} &middot; {server_count:,} servers</div>'
            f'<div class="risk-desc">{html.escape(desc)}</div>'
            f'<div class="risk-nav">{"".join(nav_links)}</div>'
            '</div>'
        )

        # Aggregate flags for this band
        flag_counts: dict[str, int] = {}
        for _, s in servers:
            for f in s.get("flags", []):
                flag_counts[f] = flag_counts.get(f, 0) + 1
        flag_html = render_flag_summary(flag_counts)

        # Server list (cap at 200 for page size, with count note)
        max_display = 200
        rows = []
        for i, (sname, s) in enumerate(servers[:max_display]):
            rows.append(render_server_row(sname, s, i, show_ns=True))

        overflow = ""
        if server_count > max_display:
            overflow = f'<div style="padding:16px 32px;color:#7d8590;font-size:13px">Showing {max_display} of {server_count:,} servers. Use the <a href="/">main listing</a> to search and filter.</div>'

        list_html = f'<div class="list">{"".join(rows)}</div>{overflow}'

        crumbs = [("Home", "/"), ("Risk Bands", "/risk/high-trust/"), (label, canonical_path)]

        json_ld = [
            organization_jsonld(),
            breadcrumb_jsonld(crumbs),
        ]

        body_html = breadcrumb_nav(crumbs) + hero_html + flag_html + list_html

        page_html = base_page(
            title=f"{label} MCP Servers | MCP Scorecard",
            description=f"{server_count:,} MCP servers rated {label} (score {band['min']}–{band['max']}). Browse trust scores and security review.",
            canonical_path=canonical_path,
            body_html=body_html,
            json_ld=json_ld,
            page_css=RISK_PAGE_CSS,
            active_nav="servers",
            extra_js=TOGGLE_DETAIL_JS,
        )

        out_path = site_dir / "risk" / slug / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page_html, encoding="utf-8")

        sitemap_urls.append({"loc": canonical_path, "lastmod": lastmod, "changefreq": "weekly", "priority": "0.6"})
        count += 1

    return count
