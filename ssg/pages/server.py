"""Generate static server detail pages."""
import html
from pathlib import Path

from ssg.data import score_band_label
from ssg.render import (
    score_class, score_color, render_score_pill, render_badge_groups,
    render_popularity_detail, render_install_section, render_flags_inline,
    render_targets, render_server_row, FLAG_SEV, FLAG_SHORT,
    VERIFIED_SVG_20,
)
from ssg.templates import base_page, breadcrumb_nav, TOGGLE_DETAIL_JS
from ssg.seo import software_application_jsonld, breadcrumb_jsonld, organization_jsonld


SERVER_PAGE_CSS = """
  .server-hero { padding: 32px; border-bottom: 1px solid #21262d; }
  .server-title { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
  .server-title h2 { font-size: 24px; font-weight: 700; }
  .server-title .ns-link { color: #7d8590; font-weight: 400; text-decoration: none; }
  .server-title .ns-link:hover { color: #58a6ff; text-decoration: underline; }
  .server-meta { display: flex; gap: 16px; font-size: 13px; color: #7d8590; flex-wrap: wrap; }
  .server-meta a { color: #58a6ff; text-decoration: none; }
  .server-meta a:hover { text-decoration: underline; }
  .score-hero { display: flex; align-items: center; gap: 16px; margin: 16px 0; }
  .score-hero .score-big { font-size: 48px; font-weight: 800; }
  .score-hero .score-label { font-size: 16px; font-weight: 600; }
  .score-breakdown { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 16px 0; }
  .score-cat { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 12px 16px; }
  .score-cat-label { font-size: 11px; color: #7d8590; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
  .score-cat-val { font-size: 24px; font-weight: 700; }
  .section { padding: 16px 32px; border-bottom: 1px solid #21262d; }
  .section-label { font-size: 13px; font-weight: 600; color: #7d8590; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
  .flags-section { display: flex; gap: 6px; flex-wrap: wrap; }
  .flag-item { display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
  .flag-critical { background: rgba(248,81,73,0.18); color: #f85149; }
  .flag-warning { background: rgba(210,153,34,0.18); color: #d29922; }
  .flag-info { background: rgba(110,118,129,0.12); color: #7d8590; }
  .related-servers { display: flex; flex-direction: column; }
  .related-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; }
  .related-row a { color: #58a6ff; text-decoration: none; }
  .related-row a:hover { text-decoration: underline; }
  .article-card { display: block; padding: 10px 14px; border: 1px solid #21262d; border-radius: 6px; margin-bottom: 8px; text-decoration: none; transition: border-color 0.15s; }
  .article-card:hover { border-color: #58a6ff; text-decoration: none; }
  .article-card-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
  .article-tag { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 1px 6px; border-radius: 3px; }
  .article-tag-pulse { background: rgba(88,166,255,0.15); color: #58a6ff; }
  .article-tag-spotlight { background: rgba(63,185,80,0.15); color: #3fb950; }
  .article-tag-trend { background: rgba(210,153,34,0.15); color: #d29922; }
  .article-title { font-size: 14px; font-weight: 600; color: #e6edf3; }
  .article-date { font-size: 11px; color: #484f58; }
  .article-summary { font-size: 12px; color: #7d8590; line-height: 1.4; }
"""


def generate_server_pages(
    site_dir: Path,
    servers: dict,
    publishers: dict,
    posts: list[dict],
    sitemap_urls: list[dict],
    lastmod: str,
) -> int:
    """Generate individual server detail pages. Returns count."""
    # Pre-index posts by publisher namespace for fast lookup
    posts_by_ns: dict[str, list[dict]] = {}
    for post in posts:
        for pub in post.get("publishers", []):
            posts_by_ns.setdefault(pub, []).append(post)

    count = 0

    for name, s in servers.items():
        parts = name.split("/")
        ns = parts[0]
        server_id = "/".join(parts[1:])
        canonical_path = f"/server/{name}/"

        score = s.get("trust_score", 0)
        scores = s.get("scores", {})
        signals = s.get("signals", {})
        flags = s.get("flags", [])
        badges = s.get("badges", {})
        install = s.get("install", {})
        targets = s.get("targets", [])
        verified = s.get("verified_publisher", False)

        band_label = score_band_label(score)
        color = score_color(score)

        # Repo URL
        repo_url = install.get("repo_url") or signals.get("repo_url")

        # --- Hero section ---
        verified_html = ""
        if verified:
            verified_html = f'<span class="verified-badge" title="Verified Publisher">{VERIFIED_SVG_20}</span>'

        meta_parts = []
        if repo_url:
            repo_esc = html.escape(repo_url)
            meta_parts.append(f'<a href="{repo_esc}" target="_blank" rel="noopener">Source Repository</a>')
        meta_parts.append(f'<a href="/publisher/{ns}/">View all {html.escape(ns)} servers</a>')
        meta_html = "".join(f'<span>{p}</span>' for p in meta_parts)

        # Score breakdown
        breakdown_html = ""
        for cat_key, cat_label in [("provenance", "Provenance"), ("maintenance", "Maintenance"), ("popularity", "Popularity"), ("permissions", "Permissions")]:
            cat_score = scores.get(cat_key, 0)
            cat_color = score_color(cat_score)
            breakdown_html += (
                f'<div class="score-cat">'
                f'<div class="score-cat-label">{cat_label}</div>'
                f'<div class="score-cat-val" style="color:{cat_color}">{cat_score}</div>'
                f'</div>'
            )

        hero_html = (
            '<div class="server-hero">'
            f'<div class="server-title">'
            f'<h2><a class="ns-link" href="/publisher/{ns}/">{html.escape(ns)}</a> / {html.escape(server_id)}</h2>'
            f'{verified_html}'
            f'</div>'
            f'<div class="server-meta">{meta_html}</div>'
            f'<div class="score-hero">'
            f'<span class="score-big" style="color:{color}">{score}</span>'
            f'<span class="score-label" style="color:{color}">{band_label}</span>'
            f'</div>'
            f'<div class="score-breakdown">{breakdown_html}</div>'
            '</div>'
        )

        # --- Badges section ---
        badges_html = render_badge_groups(badges)
        pop_html = render_popularity_detail(badges.get("popularity", {}))
        install_html = render_install_section(install)

        detail_section = ""
        if badges_html or pop_html or install_html:
            detail_section = (
                '<div class="section">'
                f'{badges_html}{pop_html}{install_html}'
                '</div>'
            )

        # --- Flags section ---
        flags_section = ""
        if flags:
            flag_items = []
            for f in flags:
                sev = FLAG_SEV.get(f, "info")
                short = html.escape(FLAG_SHORT.get(f, f))
                flag_items.append(f'<span class="flag-item flag-{sev}">{short}</span>')
            flags_section = (
                '<div class="section">'
                '<div class="section-label">Flags</div>'
                f'<div class="flags-section">{"".join(flag_items)}</div>'
                '</div>'
            )

        # --- Targets section ---
        targets_section = ""
        if targets:
            target_pills = render_targets(targets, link=True)
            targets_section = (
                '<div class="section">'
                '<div class="section-label">Platforms</div>'
                f'<div style="display:flex;gap:4px;flex-wrap:wrap">{target_pills}</div>'
                '</div>'
            )

        # --- Related servers (same publisher, up to 10) ---
        related_section = ""
        pub_data = publishers.get(ns)
        if pub_data and len(pub_data["servers"]) > 1:
            related = [(n, sv) for n, sv in pub_data["servers"] if n != name][:10]
            if related:
                rows = []
                for rname, rs in related:
                    r_id = "/".join(rname.split("/")[1:])
                    r_cls = score_class(rs.get("trust_score", 0))
                    rows.append(
                        f'<div class="related-row">'
                        f'<span class="score-pill score-{r_cls}">{rs.get("trust_score", 0)}</span>'
                        f'<a href="/server/{rname}/">{html.escape(r_id)}</a>'
                        f'</div>'
                    )
                related_section = (
                    '<div class="section">'
                    f'<div class="section-label">Other servers by {html.escape(ns)}</div>'
                    f'<div class="related-servers">{"".join(rows)}</div>'
                    '</div>'
                )

        # --- Related articles ---
        articles_section = ""
        ns_posts = posts_by_ns.get(ns, [])
        if ns_posts:
            cards = []
            for p in ns_posts:
                tag = html.escape(p.get("tag", ""))
                tag_cls = f"article-tag-{tag.lower()}" if tag else ""
                cards.append(
                    f'<a class="article-card" href="/blog/{html.escape(p.get("slug", ""))}/">'
                    f'<div class="article-card-top">'
                    f'{f"""<span class="article-tag {tag_cls}">{tag}</span>""" if tag else ""}'
                    f'<span class="article-date">{html.escape(p.get("date", ""))}</span>'
                    f'</div>'
                    f'<div class="article-title">{html.escape(p.get("title", ""))}</div>'
                    f'<div class="article-summary">{html.escape(p.get("summary", ""))}</div>'
                    f'</a>'
                )
            articles_section = (
                '<div class="section">'
                '<div class="section-label">Related Articles</div>'
                f'{"".join(cards)}'
                '</div>'
            )

        # Breadcrumbs
        crumbs = [("Home", "/"), ("Servers", "/"), (ns, f"/publisher/{ns}/"), (server_id, canonical_path)]

        # JSON-LD
        json_ld = [
            organization_jsonld(),
            software_application_jsonld(name, s, canonical_path),
            breadcrumb_jsonld(crumbs),
        ]

        body_html = (
            breadcrumb_nav(crumbs)
            + hero_html
            + detail_section
            + flags_section
            + targets_section
            + related_section
            + articles_section
        )

        page_html = base_page(
            title=f"{server_id} MCP Server Trust Score & Review | MCP Scorecard",
            description=f"Trust score: {score}/100. {server_id} by {ns} — {band_label}. See the full security breakdown.",
            canonical_path=canonical_path,
            body_html=body_html,
            json_ld=json_ld,
            page_css=SERVER_PAGE_CSS,
            active_nav="servers",
        )

        out_path = site_dir / "server" / ns / server_id / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page_html, encoding="utf-8")

        sitemap_urls.append({"loc": canonical_path, "lastmod": lastmod, "changefreq": "weekly", "priority": "0.5"})
        count += 1

    return count
