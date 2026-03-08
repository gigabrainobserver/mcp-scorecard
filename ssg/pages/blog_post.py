"""Generate static blog post pages."""
import html
from datetime import datetime
from pathlib import Path

from ssg.templates import base_page, breadcrumb_nav
from ssg.seo import blog_posting_jsonld, breadcrumb_jsonld, organization_jsonld


BLOG_PAGE_CSS = """
  .layout { display: flex; max-width: 1000px; margin: 0 auto; padding: 0 24px; gap: 48px; }
  .main { flex: 1; min-width: 0; padding: 48px 0; }
  .post-view .back { font-size: 13px; color: #7d8590; margin-bottom: 24px; display: inline-block; text-decoration: none; }
  .post-view .back:hover { color: #58a6ff; }
  .post-header { margin-bottom: 32px; }
  .post-header .post-date { margin-bottom: 8px; }
  .post-date { font-size: 12px; color: #7d8590; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
  .post-header h2 { font-size: 32px; font-weight: 700; line-height: 1.2; margin-bottom: 12px; }
  .post-header .post-summary { font-size: 17px; color: #8b949e; }
  .byline { font-size: 13px; color: #484f58; margin-top: 8px; }
  .post-pubs { margin-top: 8px; display: flex; gap: 4px; flex-wrap: wrap; }
  .post-pub { font-size: 10px; padding: 1px 6px; border-radius: 3px; background: rgba(88,166,255,0.08); color: #58a6ff; font-family: monospace; text-decoration: none; }
  .post-pub:hover { background: rgba(88,166,255,0.18); text-decoration: none; }
  .tag { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.5px; vertical-align: middle; }
  .tag-pulse { background: rgba(88,166,255,0.15); color: #58a6ff; }
  .tag-spotlight { background: rgba(63,185,80,0.15); color: #3fb950; }
  .tag-trend { background: rgba(210,153,34,0.15); color: #d29922; }
  .tag-investigation { background: rgba(248,81,73,0.15); color: #f85149; }
  .tag-interview { background: rgba(163,113,247,0.15); color: #a371f7; }
  .tag-comparison { background: rgba(88,166,255,0.15); color: #58a6ff; }
  .tag-incident { background: rgba(248,81,73,0.15); color: #f85149; }
  .post-body { line-height: 1.7; font-size: 16px; color: #b1bac4; }
  .post-body h3 { font-size: 20px; font-weight: 600; color: #e6edf3; margin: 32px 0 12px; }
  .post-body p { margin-bottom: 16px; }
  .post-body strong { color: #e6edf3; }
  .post-body code { background: #161b22; padding: 2px 6px; border-radius: 4px; font-size: 14px; color: #e6edf3; }
  .post-body a { color: #58a6ff; }
  .post-body ul, .post-body ol { margin: 0 0 16px 24px; }
  .post-body li { margin-bottom: 6px; }
  .post-body em { color: #8b949e; }
  .post-body table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }
  .post-body th { text-align: left; padding: 8px 12px; border-bottom: 2px solid #21262d; color: #7d8590; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
  .post-body td { padding: 8px 12px; border-bottom: 1px solid #21262d; }
  .post-body .traceback { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px; font-size: 13px; color: #7d8590; margin-top: 32px; }
  .post-body .traceback strong { color: #8b949e; }
  .post-body .traceback a { color: #58a6ff; }
  .post-body blockquote { border-left: 3px solid #30363d; padding: 12px 20px; margin: 20px 0; background: rgba(88,166,255,0.04); border-radius: 0 8px 8px 0; }
  .post-body blockquote p { color: #8b949e; margin: 0; font-style: italic; }
  .post-body blockquote cite { display: block; margin-top: 8px; font-size: 13px; font-style: normal; color: #484f58; }
  .post-nav { display: flex; justify-content: space-between; margin-top: 48px; padding-top: 24px; border-top: 1px solid #21262d; font-size: 13px; }
  .post-nav a { color: #58a6ff; text-decoration: none; }
  .post-nav a:hover { text-decoration: underline; }
"""


def _fmt_date(date_str: str) -> str:
    """Format YYYY-MM-DD to 'March 6, 2026'."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y").replace(" 0", " ")
    except ValueError:
        return date_str


def generate_blog_posts(site_dir: Path, posts: list[dict], sitemap_urls: list[dict], lastmod: str) -> int:
    """Generate individual blog post pages. Returns count."""
    count = 0

    # Rewrite internal links in post body: blog.html#slug → /blog/slug/, publisher.html#ns → /publisher/ns/
    def rewrite_links(body: str) -> str:
        body = body.replace('href="blog.html#', 'href="/blog/')
        body = body.replace('href="publisher.html#', 'href="/publisher/')
        # Close the links properly — the hash links become /path/ links
        # Pattern: /blog/slug" → /blog/slug/"
        # This is tricky since the original has blog.html#slug" which becomes /blog/slug"
        # We need to add trailing slash before the closing quote
        import re
        body = re.sub(r'href="/blog/([^"]+)"', lambda m: f'href="/blog/{m.group(1)}/"', body)
        body = re.sub(r'href="/publisher/([^"]+)"', lambda m: f'href="/publisher/{m.group(1)}/"', body)
        return body

    for i, post in enumerate(posts):
        slug = post.get("slug", "")
        title = post.get("title", "")
        tag = post.get("tag", "")
        date = post.get("date", "")
        summary = post.get("summary", "")
        body = post.get("body", "")
        publishers = post.get("publishers", [])

        canonical_path = f"/blog/{slug}/"

        # Rewrite internal links
        body = rewrite_links(body)

        # Publisher pills
        pub_pills = "".join(
            f'<a class="post-pub" href="/publisher/{html.escape(pub)}/">{html.escape(pub)}</a>'
            for pub in publishers
        )
        pub_html = f'<div class="post-pubs" style="margin-top:12px">{pub_pills}</div>' if pub_pills else ""

        # Previous/next navigation
        nav_parts = []
        if i < len(posts) - 1:
            prev = posts[i + 1]
            nav_parts.append(f'<a href="/blog/{html.escape(prev["slug"])}/">&larr; {html.escape(prev["title"])}</a>')
        else:
            nav_parts.append("<span></span>")
        if i > 0:
            nxt = posts[i - 1]
            nav_parts.append(f'<a href="/blog/{html.escape(nxt["slug"])}/">{html.escape(nxt["title"])} &rarr;</a>')
        else:
            nav_parts.append("<span></span>")
        post_nav = f'<div class="post-nav">{nav_parts[0]}{nav_parts[1]}</div>'

        tag_lower = tag.lower() if tag else ""

        # Breadcrumbs
        crumbs = [("Home", "/"), ("Blog", "/blog/"), (title, canonical_path)]

        # JSON-LD
        json_ld = [
            organization_jsonld(),
            blog_posting_jsonld(post, canonical_path),
            breadcrumb_jsonld(crumbs),
        ]

        body_html = (
            breadcrumb_nav(crumbs)
            + '<div class="layout"><div class="main">'
            + '<div class="post-view">'
            + f'<a href="/blog/" class="back">&larr; All posts</a>'
            + '<div class="post-header">'
            + f'<div class="post-date"><span class="tag tag-{tag_lower}">{html.escape(tag)}</span> &nbsp;{_fmt_date(date)}</div>'
            + f'<h2>{html.escape(title)}</h2>'
            + f'<div class="post-summary">{html.escape(summary)}</div>'
            + '<div class="byline">MCP Scorecard Research</div>'
            + pub_html
            + '</div>'
            + f'<div class="post-body">{body}</div>'
            + post_nav
            + '</div>'
            + '</div></div>'
        )

        page_html = base_page(
            title=f"{title} | MCP Scorecard Blog",
            description=summary,
            canonical_path=canonical_path,
            body_html=body_html,
            og_type="article",
            json_ld=json_ld,
            page_css=BLOG_PAGE_CSS,
            active_nav="blog",
            extra_head='<link rel="alternate" type="application/rss+xml" title="MCP Scorecard Blog" href="/feed.xml">',
        )

        out_path = site_dir / "blog" / slug / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page_html, encoding="utf-8")

        sitemap_urls.append({"loc": canonical_path, "lastmod": date or lastmod, "changefreq": "monthly", "priority": "0.6"})
        count += 1

    return count
