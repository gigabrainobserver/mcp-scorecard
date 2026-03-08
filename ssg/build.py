"""Main SSG build orchestrator."""
import shutil
import time
from pathlib import Path

from ssg.assets import copy_static_assets, copy_css
from ssg.data import (
    load_servers,
    load_posts,
    load_stats,
    load_index_meta,
    derive_publishers,
    derive_platforms,
    derive_trust_bands,
    score_band,
)
from ssg.seo import (
    generate_sitemap,
    generate_rss,
    generate_llms_txt,
    generate_robots_txt,
)


SITE_DIR = Path("site")


def build() -> None:
    """Run the full SSG build."""
    start = time.time()
    print("MCP Scorecard SSG Build")
    print("=" * 40)

    # 1. Clean output
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir()
    print(f"  Output: {SITE_DIR.resolve()}")

    # 2. Load data
    print("\nLoading data...")
    t0 = time.time()
    servers = load_servers()
    posts = load_posts()
    stats = load_stats()
    meta = load_index_meta()
    print(f"  {len(servers):,} servers, {len(posts)} posts loaded in {time.time()-t0:.1f}s")

    # 3. Derive aggregates
    print("\nDeriving aggregates...")
    t0 = time.time()
    publishers = derive_publishers(servers, posts)
    platforms = derive_platforms(servers)
    trust_bands = derive_trust_bands(servers)
    print(f"  {len(publishers):,} publishers, {len(platforms)} platforms, 5 trust bands in {time.time()-t0:.1f}s")

    # Compute global stats for sitemap/templates
    total_flagged = sum(1 for s in servers.values() if s.get("flags"))
    global_bands = {}
    for key in ["high", "mod", "low", "vlow", "unk"]:
        global_bands[key] = trust_bands[key]["count"]

    # 4. Copy assets
    print("\nCopying assets...")
    copy_static_assets(SITE_DIR)
    copy_css(SITE_DIR)
    print("  Static files copied")

    # 5. Generate pages
    # Track all URLs for sitemap
    sitemap_urls: list[dict] = []
    lastmod = meta["generated_at"][:10] if meta.get("generated_at") else "2026-03-08"

    # --- Blog post pages ---
    print("\nGenerating blog post pages...")
    t0 = time.time()
    from ssg.pages.blog_post import generate_blog_posts
    blog_count = generate_blog_posts(SITE_DIR, posts, sitemap_urls, lastmod)
    print(f"  {blog_count} blog pages in {time.time()-t0:.1f}s")

    # --- Server detail pages ---
    print("\nGenerating server detail pages...")
    t0 = time.time()
    from ssg.pages.server import generate_server_pages
    server_count = generate_server_pages(SITE_DIR, servers, publishers, posts, sitemap_urls, lastmod)
    print(f"  {server_count:,} server pages in {time.time()-t0:.1f}s")

    # --- Publisher pages ---
    print("\nGenerating publisher pages...")
    t0 = time.time()
    from ssg.pages.publisher import generate_publisher_pages
    pub_count = generate_publisher_pages(SITE_DIR, publishers, sitemap_urls, lastmod)
    print(f"  {pub_count:,} publisher pages in {time.time()-t0:.1f}s")

    # --- Platform pages ---
    print("\nGenerating platform pages...")
    t0 = time.time()
    from ssg.pages.platform import generate_platform_pages
    plat_count = generate_platform_pages(SITE_DIR, platforms, sitemap_urls, lastmod)
    print(f"  {plat_count} platform pages in {time.time()-t0:.1f}s")

    # --- Listing pages ---
    print("\nGenerating listing pages...")
    t0 = time.time()
    from ssg.pages.listings import (
        generate_home_page, generate_publishers_page,
        generate_platforms_page, generate_blog_index,
    )
    generate_home_page(SITE_DIR, servers, trust_bands, total_flagged)
    generate_publishers_page(SITE_DIR, publishers)
    generate_platforms_page(SITE_DIR, platforms)
    generate_blog_index(SITE_DIR, posts)
    listing_count = 4
    print(f"  {listing_count} listing pages in {time.time()-t0:.1f}s")

    # --- Static pages ---
    print("\nGenerating static pages...")
    t0 = time.time()
    from ssg.pages.static_pages import generate_static_pages
    # Compute flag counts
    all_flag_counts: dict[str, int] = {}
    for s in servers.values():
        for f in s.get("flags", []):
            all_flag_counts[f] = all_flag_counts.get(f, 0) + 1
    static_count = generate_static_pages(
        SITE_DIR, len(servers), len(publishers), total_flagged,
        all_flag_counts, sitemap_urls, lastmod,
    )
    print(f"  {static_count} static pages in {time.time()-t0:.1f}s")

    # --- Risk band pages ---
    print("\nGenerating risk band pages...")
    t0 = time.time()
    from ssg.pages.risk import generate_risk_pages
    risk_count = generate_risk_pages(SITE_DIR, trust_bands, sitemap_urls, lastmod)
    print(f"  {risk_count} risk pages in {time.time()-t0:.1f}s")

    # --- Top/listicle pages ---
    print("\nGenerating top pages...")
    t0 = time.time()
    from ssg.pages.top import generate_top_pages
    top_count = generate_top_pages(SITE_DIR, servers, sitemap_urls, lastmod)
    print(f"  {top_count} top pages in {time.time()-t0:.1f}s")

    # 6. Add listing/static page URLs to sitemap
    sitemap_urls.insert(0, {"loc": "/", "changefreq": "daily", "priority": "1.0", "lastmod": lastmod})
    for path, freq, pri in [
        ("/publishers/", "daily", "0.8"),
        ("/platforms/", "daily", "0.8"),
        ("/blog/", "daily", "0.8"),
        ("/about/", "weekly", "0.7"),
        ("/api/", "weekly", "0.6"),
        ("/privacy/", "monthly", "0.3"),
    ]:
        sitemap_urls.append({"loc": path, "changefreq": freq, "priority": pri, "lastmod": lastmod})

    # 7. Generate SEO files
    print("\nGenerating SEO files...")
    _write(SITE_DIR / "sitemap.xml", generate_sitemap(sitemap_urls))
    _write(SITE_DIR / "feed.xml", generate_rss(posts))
    _write(SITE_DIR / "llms.txt", generate_llms_txt(len(servers)))
    _write(SITE_DIR / "robots.txt", generate_robots_txt())
    print(f"  sitemap.xml ({len(sitemap_urls):,} URLs), feed.xml, llms.txt, robots.txt")

    # 8. Summary
    elapsed = time.time() - start
    total_pages = blog_count + server_count + pub_count + plat_count + listing_count + static_count + risk_count + top_count
    print(f"\n{'=' * 40}")
    print(f"Build complete: {total_pages:,} pages in {elapsed:.1f}s")
    print(f"  Servers: {server_count:,}")
    print(f"  Publishers: {pub_count:,}")
    print(f"  Platforms: {plat_count}")
    print(f"  Blog posts: {blog_count}")
    print(f"  Listings: {listing_count}")
    print(f"  Static: {static_count}")
    print(f"  Risk bands: {risk_count}")
    print(f"  Top lists: {top_count}")
    print(f"  Sitemap URLs: {len(sitemap_urls):,}")
    print(f"\nServe locally: python -m http.server -d site/ -b localhost 8091")


def _write(path: Path, content: str) -> None:
    """Write content to file, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
