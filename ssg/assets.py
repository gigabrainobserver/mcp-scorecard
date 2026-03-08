"""Asset management: copy static files, CSS extraction."""
import shutil
from pathlib import Path


# Files to copy from repo root to site/
STATIC_FILES = [
    "favicon.svg",
    "CNAME",
    "js/supabase.js",
    "blog/posts.json",
    "output/index.json",
    "output/stats.json",
    "output/flags.json",
]

# Optional files (copy if they exist)
OPTIONAL_FILES = [
    "og-default.png",
]


def copy_static_assets(site_dir: Path, root_dir: Path = Path(".")) -> None:
    """Copy static assets from repo root to site output."""
    for rel_path in STATIC_FILES:
        src = root_dir / rel_path
        dst = site_dir / rel_path
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    for rel_path in OPTIONAL_FILES:
        src = root_dir / rel_path
        dst = site_dir / rel_path
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def copy_css(site_dir: Path, root_dir: Path = Path(".")) -> None:
    """Copy extracted CSS to site output."""
    src = root_dir / "css" / "style.css"
    dst = site_dir / "css" / "style.css"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst)
    else:
        print(f"  WARNING: {src} not found — CSS will be missing")
