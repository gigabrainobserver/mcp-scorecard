"""Rendering functions — Python port of the JS template logic."""
import html


# --- Constants (ported from index.html JS) ---

FLAG_SEV = {
    "DEAD_ENTRY": "critical",
    "NO_SOURCE": "critical",
    "SENSITIVE_CRED_REQUEST": "critical",
    "HIGH_SECRET_DEMAND": "warning",
    "STAGING_ARTIFACT": "warning",
    "REPO_ARCHIVED": "warning",
    "TEMPLATE_DESCRIPTION": "info",
    "DESCRIPTION_DUPLICATE": "info",
}

FLAG_SHORT = {
    "SENSITIVE_CRED_REQUEST": "Sensitive Creds",
    "DEAD_ENTRY": "Dead Entry",
    "NO_SOURCE": "No Source",
    "HIGH_SECRET_DEMAND": "Many Secrets",
    "REPO_ARCHIVED": "Archived",
    "STAGING_ARTIFACT": "Staging",
    "DESCRIPTION_DUPLICATE": "Dup Desc",
    "TEMPLATE_DESCRIPTION": "Template",
}

LINK_ICON_SVG = '<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M7.775 3.275a.75.75 0 001.06 1.06l1.25-1.25a2 2 0 112.83 2.83l-2.5 2.5a2 2 0 01-2.83 0 .75.75 0 00-1.06 1.06 3.5 3.5 0 004.95 0l2.5-2.5a3.5 3.5 0 00-4.95-4.95l-1.25 1.25zm-4.69 9.64a2 2 0 010-2.83l2.5-2.5a2 2 0 012.83 0 .75.75 0 001.06-1.06 3.5 3.5 0 00-4.95 0l-2.5 2.5a3.5 3.5 0 004.95 4.95l1.25-1.25a.75.75 0 00-1.06-1.06l-1.25 1.25a2 2 0 01-2.83 0z"/></svg>'

VERIFIED_SVG_14 = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#58a6ff"/><path d="M9 12l2 2 4-4" stroke="#0d1117" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M9 12l2 2 4-4" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>'

VERIFIED_SVG_20 = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#58a6ff"/><path d="M9 12l2 2 4-4" stroke="#0d1117" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M9 12l2 2 4-4" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>'

UNID_LIC_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M12 2L1 21h22L12 2z" fill="#d29922"/><text x="12" y="18" text-anchor="middle" font-size="14" font-weight="bold" fill="#0d1117">!</text></svg>'


# --- Core functions ---

def score_class(score: int) -> str:
    """Return CSS class suffix for a trust score."""
    if score >= 80:
        return "high"
    if score >= 60:
        return "mod"
    if score >= 40:
        return "low"
    if score >= 20:
        return "vlow"
    return "unk"


def score_color(score: int) -> str:
    """Return hex color for a trust score."""
    cls = score_class(score)
    return {
        "high": "#3fb950",
        "mod": "#58a6ff",
        "low": "#d29922",
        "vlow": "#f85149",
        "unk": "#6e7681",
    }[cls]


def fmt_num(n: int) -> str:
    """Format large numbers: 1.2M, 3.4k, or plain."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def render_badge(b: dict) -> str:
    """Render a single badge span."""
    btype = b.get("type", "")
    if btype == "flag":
        sev = html.escape(b.get("severity", "info"))
        label = html.escape(b.get("label", ""))
        return f'<span class="badge badge-flag-{sev}">{label}</span>'
    if btype == "bool":
        cls = "badge-bool-true" if b.get("value") else "badge-bool-false"
        label = html.escape(b.get("label", ""))
        return f'<span class="badge {cls}">{label}</span>'
    if btype == "enum":
        level = html.escape(b.get("level", "neutral"))
        label = html.escape(b.get("label", ""))
        value = html.escape(str(b.get("value", "")))
        return f'<span class="badge badge-enum-{level}">{label}: {value}</span>'
    return ""


def render_score_pill(score: int) -> str:
    """Render the colored score pill."""
    cls = score_class(score)
    return f'<span class="score-pill score-{cls}">{score}</span>'


def render_flags_inline(flags: list[str], show_info: bool = False) -> str:
    """Render inline flag pills for a row."""
    parts = []
    for f in flags:
        sev = FLAG_SEV.get(f, "info")
        if not show_info and sev == "info":
            continue
        short = html.escape(FLAG_SHORT.get(f, f))
        parts.append(f'<span class="row-flag row-flag-{sev}">{short}</span>')
    return "".join(parts)


def render_targets(targets: list[str], link: bool = True) -> str:
    """Render target platform pills."""
    parts = []
    for t in targets:
        t_esc = html.escape(t)
        if link:
            slug = t.lower().replace(" ", "-")
            parts.append(f'<a href="/platform/{slug}/" class="row-target" style="text-decoration:none">{t_esc}</a>')
        else:
            parts.append(f'<span class="row-target">{t_esc}</span>')
    return "".join(parts)


def render_popularity_inline(pop: dict) -> str:
    """Render inline popularity metrics (stars, forks, watchers)."""
    parts = []
    stars = pop.get("stars", 0)
    forks = pop.get("forks", 0)
    watchers = pop.get("watchers", 0)
    if stars > 0:
        parts.append(f'<span>&#9733; <span class="val">{fmt_num(stars)}</span></span>')
    if forks > 0:
        parts.append(f'<span>&#9741; <span class="val">{fmt_num(forks)}</span></span>')
    if watchers > 0:
        parts.append(f'<span>&#9737; <span class="val">{fmt_num(watchers)}</span></span>')
    return "".join(parts)


def render_popularity_detail(pop: dict) -> str:
    """Render detail-view popularity section."""
    stars = pop.get("stars", 0)
    forks = pop.get("forks", 0)
    watchers = pop.get("watchers", 0)
    if not (stars > 0 or forks > 0):
        return ""
    parts = []
    if stars > 0:
        parts.append(f'<span>&#9733; <span class="val">{fmt_num(stars)}</span> stars</span>')
    if forks > 0:
        parts.append(f'<span>&#9741; <span class="val">{fmt_num(forks)}</span> forks</span>')
    if watchers > 0:
        parts.append(f'<span>&#9737; <span class="val">{fmt_num(watchers)}</span> watchers</span>')
    return f'<div class="detail-pop">{"".join(parts)}</div>'


def render_badge_groups(badges: dict) -> str:
    """Render Security, Provenance, Activity badge groups."""
    parts = []
    for group_key, group_label in [("security", "Security"), ("provenance", "Provenance"), ("activity", "Activity")]:
        items = badges.get(group_key, [])
        if not items:
            continue
        badge_html = "".join(render_badge(b) for b in items)
        parts.append(
            f'<div class="badge-group">'
            f'<span class="badge-group-label">{group_label}</span>'
            f'<div class="badge-row">{badge_html}</div>'
            f'</div>'
        )
    return "".join(parts)


def render_install_section(install: dict) -> str:
    """Render install info (packages, transports, env vars)."""
    pkg_types = install.get("package_types", [])
    pkg_ids = install.get("package_identifiers", [])
    transports = install.get("transport_types", [])
    env_vars = install.get("env_vars", [])
    version = install.get("version")

    if not (pkg_types or transports or env_vars):
        return ""

    parts = []
    for i, ptype in enumerate(pkg_types):
        pid = pkg_ids[i] if i < len(pkg_ids) else ""
        pid_esc = html.escape(pid)
        if ptype == "npm":
            parts.append(f'<span class="badge badge-enum-good">npm: npx -y {pid_esc}</span>')
        elif ptype == "pypi":
            parts.append(f'<span class="badge badge-enum-good">pypi: uvx {pid_esc}</span>')
        else:
            parts.append(f'<span class="badge badge-enum-neutral">{html.escape(ptype)}: {pid_esc}</span>')

    for t in transports:
        lvl = "good" if t == "stdio" else "neutral"
        parts.append(f'<span class="badge badge-enum-{lvl}">{html.escape(t)}</span>')

    if version:
        parts.append(f'<span class="badge badge-enum-neutral">v{html.escape(version)}</span>')

    result = (
        '<div class="badge-group">'
        '<span class="badge-group-label">Install</span>'
        f'<div class="badge-row">{"".join(parts)}</div>'
        '</div>'
    )

    if env_vars:
        ev_parts = []
        for ev in env_vars:
            name = html.escape(ev.get("name", ""))
            req = ev.get("is_required", False)
            sec = ev.get("is_secret", False)
            title = ("required" if req else "optional") + (", secret" if sec else "")
            lvl = "warning" if (sec and req) else ("neutral" if req else "good")
            ev_parts.append(f'<span class="badge badge-enum-{lvl}" title="{title}">{name}</span>')
        result += (
            '<div class="badge-group">'
            '<span class="badge-group-label">Env Vars</span>'
            f'<div class="badge-row">{"".join(ev_parts)}</div>'
            '</div>'
        )

    return result


def render_server_row(name: str, s: dict, idx: int, show_ns: bool = True) -> str:
    """Render a complete server row + detail panel.

    Args:
        name: Full server name (namespace/id)
        s: Server data dict
        idx: Row index for expand/collapse
        show_ns: Whether to show namespace prefix as link
    """
    cls = score_class(s.get("trust_score", 0))
    parts = name.split("/")
    ns = parts[0]
    server_id = "/".join(parts[1:])

    badges = s.get("badges", {})
    pop = badges.get("popularity", {})
    repo_url = (s.get("install") or {}).get("repo_url") or (s.get("signals") or {}).get("repo_url")

    # Link icon
    link_icon = ""
    if repo_url:
        repo_esc = html.escape(repo_url)
        link_icon = f'<a class="row-link" href="{repo_esc}" target="_blank" rel="noopener" title="{repo_esc}" onclick="event.stopPropagation()">{LINK_ICON_SVG}</a>'

    # Verified badge
    verified_icon = ""
    if s.get("verified_publisher"):
        verified_icon = f'<span class="verified-badge" title="Verified Publisher">{VERIFIED_SVG_14}</span>'

    # Unidentified license
    unid_lic = ""
    if (s.get("signals") or {}).get("github_license") == "NOASSERTION":
        unid_lic = f'<span class="unid-lic-badge" title="Unidentified License">{UNID_LIC_SVG}</span>'

    # Row flags (critical/warning only in condensed view)
    row_flags = render_flags_inline(s.get("flags", []))

    # Row targets
    row_targets = render_targets(s.get("targets", []))

    # Row popularity
    pop_html = render_popularity_inline(pop)

    # Name display
    ns_esc = html.escape(ns)
    id_esc = html.escape(server_id)
    if show_ns:
        name_html = f'{link_icon}<a class="ns" href="/publisher/{ns}/">{ns_esc}/</a>{id_esc}{verified_icon}{unid_lic}'
    else:
        name_html = f'{link_icon}{id_esc}{verified_icon}{unid_lic}'

    # Detail panel content
    detail_badges = render_badge_groups(badges)
    detail_pop = render_popularity_detail(pop)
    install_html = render_install_section(s.get("install", {}))

    verified_detail = ""
    if s.get("verified_publisher"):
        verified_detail = (
            '<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px">'
            f'<span class="verified-badge" title="Verified Publisher">{VERIFIED_SVG_14}</span>'
            '<span style="font-size:11px;color:#58a6ff;font-weight:600">Verified Publisher</span>'
            '</div>'
        )

    score_val = s.get("trust_score", 0)

    return (
        f'<div class="row" data-idx="{idx}" onclick="toggleDetail({idx})">'
        f'<span class="row-chevron">&#9654;</span>'
        f'<span class="score-pill score-{cls}">{score_val}</span>'
        f'<span class="row-name">{name_html}</span>'
        f'<span class="row-flags">{row_flags}</span>'
        f'<span class="row-targets">{row_targets}</span>'
        f'<span class="row-pop">{pop_html}</span>'
        f'</div>'
        f'<div class="detail" id="detail-{idx}">'
        f'{verified_detail}'
        f'{detail_badges}'
        f'{detail_pop}'
        f'{install_html}'
        f'</div>'
    )


def render_stats_bar(server_count: int, bands: dict, flagged: int = 0, avg_score: int = 0, total_stars: int = 0, mode: str = "full") -> str:
    """Render the stats bar.

    mode='full': shows all bands + flagged count (homepage)
    mode='publisher': shows server count, avg score, total stars, then bands
    """
    if mode == "publisher":
        avg_color = score_color(avg_score)
        parts = [
            f'<div class="stat"><div class="num">{server_count}</div><div class="label">Servers</div></div>',
            f'<div class="stat"><div class="num" style="color:{avg_color}">{avg_score}</div><div class="label">Avg Score</div></div>',
            f'<div class="stat"><div class="num" style="color:#e6edf3">{fmt_num(total_stars)}</div><div class="label">Total Stars</div></div>',
            '<div class="stat-sep"></div>',
        ]
        for key, label in [("high", "High"), ("mod", "Moderate"), ("low", "Low"), ("vlow", "Very Low"), ("unk", "Suspicious")]:
            if bands.get(key, 0) > 0:
                parts.append(f'<div class="stat band-{key}"><div class="num">{bands[key]}</div><div class="label">{label}</div></div>')
        return f'<div class="stats-bar">{"".join(parts)}</div>'

    # Full mode (homepage)
    return (
        '<div class="stats-bar">'
        f'<div class="stat"><div class="num">{server_count}</div><div class="label">Servers</div></div>'
        '<div class="stat-sep"></div>'
        f'<div class="stat band-high"><div class="num">{bands.get("high", 0)}</div><div class="label">High Trust</div></div>'
        f'<div class="stat band-mod"><div class="num">{bands.get("mod", 0)}</div><div class="label">Moderate</div></div>'
        f'<div class="stat band-low"><div class="num">{bands.get("low", 0)}</div><div class="label">Low Trust</div></div>'
        f'<div class="stat band-vlow"><div class="num">{bands.get("vlow", 0)}</div><div class="label">Very Low</div></div>'
        '<div class="stat-sep"></div>'
        f'<div class="stat band-unk"><div class="num">{bands.get("unk", 0)}</div><div class="label">Suspicious</div></div>'
        f'<div class="stat"><div class="num" style="color:#f85149">{flagged}</div><div class="label">Flagged</div></div>'
        '</div>'
    )


def render_flag_summary(flag_counts: dict) -> str:
    """Render the flag summary bar (used on publisher/platform pages)."""
    if not flag_counts:
        return ""
    entries = sorted(flag_counts.items(), key=lambda x: x[1], reverse=True)
    pills = []
    for f, count in entries:
        sev = FLAG_SEV.get(f, "info")
        short = html.escape(FLAG_SHORT.get(f, f))
        pills.append(f'<span class="row-flag row-flag-{sev}">{short} ({count})</span>')
    return (
        '<div class="flag-summary">'
        '<span class="flag-summary-label">Flags</span>'
        f'{"".join(pills)}'
        '</div>'
    )


def render_related_articles(posts: list[dict]) -> str:
    """Render related articles section (used on publisher pages)."""
    if not posts:
        return ""
    cards = []
    for p in posts:
        tag = html.escape(p.get("tag", ""))
        tag_cls = f"article-tag-{tag.lower()}" if tag else ""
        slug = html.escape(p.get("slug", ""))
        title = html.escape(p.get("title", ""))
        date = html.escape(p.get("date", ""))
        summary = html.escape(p.get("summary", ""))
        cards.append(
            f'<a class="article-card" href="/blog/{slug}/">'
            f'<div class="article-card-top">'
            f'{f"""<span class="article-tag {tag_cls}">{tag}</span>""" if tag else ""}'
            f'<span class="article-date">{date}</span>'
            f'</div>'
            f'<div class="article-title">{title}</div>'
            f'<div class="article-summary">{summary}</div>'
            f'</a>'
        )
    return (
        '<div class="articles">'
        '<div class="articles-label">Related Articles</div>'
        f'{"".join(cards)}'
        '</div>'
    )
