"""Page shell templates for the SSG."""
import html as html_mod
import json

BASE_URL = "https://mcp-scorecard.ai"


def base_page(
    title: str,
    description: str,
    canonical_path: str,
    body_html: str,
    og_type: str = "website",
    json_ld: list[dict] | None = None,
    extra_head: str = "",
    extra_js: str = "",
    page_css: str = "",
    active_nav: str | None = None,
) -> str:
    """Generate a complete HTML page."""
    canonical_url = BASE_URL + canonical_path
    title_esc = html_mod.escape(title)
    desc_esc = html_mod.escape(description)

    # JSON-LD blocks
    ld_html = ""
    if json_ld:
        for ld in json_ld:
            ld_html += f'<script type="application/ld+json">{json.dumps(ld, separators=(",", ":"))}</script>\n'

    # Page-specific CSS
    style_block = f"<style>{page_css}</style>" if page_css else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_esc}</title>
<meta name="description" content="{desc_esc}">
<link rel="canonical" href="{canonical_url}">
<meta property="og:title" content="{title_esc}">
<meta property="og:description" content="{desc_esc}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{canonical_url}">
<meta property="og:image" content="{BASE_URL}/og-default.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title_esc}">
<meta name="twitter:description" content="{desc_esc}">
<meta name="twitter:image" content="{BASE_URL}/og-default.png">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="/css/style.css">
{extra_head}
{ld_html}{style_block}
</head>
<body>
{header(active_nav)}
{body_html}
{footer()}
{f"<script>{extra_js}</script>" if extra_js else ""}
</body>
</html>"""


def header(active_nav: str | None = None) -> str:
    """Site header with navigation."""
    def nav_link(href: str, label: str, key: str) -> str:
        cls = ' class="active"' if active_nav == key else ""
        return f'<a href="{href}"{cls}>{label}</a>'

    return (
        '<div class="header">'
        '<h1><a href="/">MCP Scorecard</a></h1>'
        '<div class="nav">'
        f'{nav_link("/", "Servers", "servers")}'
        f'{nav_link("/publishers/", "Publishers", "publishers")}'
        f'{nav_link("/platforms/", "Platforms", "platforms")}'
        f'{nav_link("/blog/", "Blog", "blog")}'
        f'{nav_link("/api/", "API", "api")}'
        '</div>'
        '<div class="meta">'
        '<a href="/about/" style="color:#58a6ff;font-weight:600;text-decoration:none;">Mission Statement</a>'
        '<a href="https://github.com/gigabrainobserver/mcp-scorecard" style="color:#e6edf3;text-decoration:none;">GitHub</a>'
        '</div>'
        '</div>'
    )


def footer() -> str:
    """Site footer."""
    return (
        '<div class="footer">'
        '<div class="footer-squig">~ ~ ~</div>'
        '<div class="footer-text">'
        '<a href="https://mcp-scorecard.ai">mcp-scorecard.ai</a>'
        ' &nbsp;&middot;&nbsp; '
        '<a href="/privacy/">2026</a>'
        '</div>'
        '</div>'
    )


def breadcrumb_nav(crumbs: list[tuple[str, str]]) -> str:
    """Render breadcrumb navigation.

    Args:
        crumbs: List of (label, url) tuples. Last item has no link.
    """
    parts = []
    for i, (label, url) in enumerate(crumbs):
        label_esc = html_mod.escape(label)
        if i < len(crumbs) - 1:
            parts.append(f'<a href="{url}" style="color:#7d8590;text-decoration:none">{label_esc}</a>')
            parts.append('<span style="color:#484f58;margin:0 6px">/</span>')
        else:
            parts.append(f'<span style="color:#e6edf3">{label_esc}</span>')
    return (
        '<nav class="breadcrumb" role="navigation" aria-label="Breadcrumb" '
        'style="padding:8px 32px;font-size:12px;border-bottom:1px solid #21262d">'
        f'{"".join(parts)}'
        '</nav>'
    )


TOGGLE_DETAIL_JS = """
function toggleDetail(idx) {
  var row = document.querySelector('.row[data-idx="' + idx + '"]');
  var detail = document.getElementById('detail-' + idx);
  var wasOpen = detail.classList.contains('open');
  document.querySelectorAll('.detail.open').forEach(function(d) { d.classList.remove('open'); });
  document.querySelectorAll('.row.expanded').forEach(function(r) { r.classList.remove('expanded'); });
  if (!wasOpen) { detail.classList.add('open'); row.classList.add('expanded'); }
}
"""
