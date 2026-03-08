"""Data loading and aggregation for the SSG."""
import json
from pathlib import Path


def load_servers(path: str = "output/index.json") -> dict:
    """Load index.json, return {name: server_data} dict."""
    with open(path) as f:
        data = json.load(f)
    return data["servers"]


def load_posts(path: str = "blog/posts.json") -> list[dict]:
    """Load blog posts array."""
    with open(path) as f:
        return json.load(f)


def load_stats(path: str = "output/stats.json") -> dict:
    """Load aggregate statistics."""
    with open(path) as f:
        return json.load(f)


def load_index_meta(path: str = "output/index.json") -> dict:
    """Load just the top-level metadata (version, generated_at, server_count)."""
    with open(path) as f:
        data = json.load(f)
    return {
        "version": data.get("version", "1.0.0"),
        "generated_at": data.get("generated_at", ""),
        "server_count": data.get("server_count", 0),
    }


def score_band(score: int) -> str:
    """Return trust band key from score."""
    if score >= 80:
        return "high"
    if score >= 60:
        return "mod"
    if score >= 40:
        return "low"
    if score >= 20:
        return "vlow"
    return "unk"


def score_band_label(score: int) -> str:
    """Return human-readable trust band label."""
    if score >= 80:
        return "High Trust"
    if score >= 60:
        return "Moderate Trust"
    if score >= 40:
        return "Low Trust"
    if score >= 20:
        return "Very Low Trust"
    return "Suspicious"


def derive_publishers(servers: dict, posts: list[dict]) -> dict:
    """Group servers by namespace, compute aggregate stats.

    Returns {namespace: {
        ns, servers: [(name, data)], avg_score, total_stars,
        verified, bands, flag_counts, related_posts
    }}
    """
    ns_map: dict[str, dict] = {}

    for name, s in servers.items():
        ns = name.split("/")[0]
        if ns not in ns_map:
            ns_map[ns] = {
                "ns": ns,
                "servers": [],
                "verified": False,
                "total_score": 0,
                "total_stars": 0,
                "bands": {"high": 0, "mod": 0, "low": 0, "vlow": 0, "unk": 0},
                "flag_counts": {},
                "related_posts": [],
            }
        entry = ns_map[ns]
        entry["servers"].append((name, s))
        entry["total_score"] += s.get("trust_score", 0)
        entry["total_stars"] += (s.get("badges", {}).get("popularity", {}).get("stars", 0))
        entry["bands"][score_band(s.get("trust_score", 0))] += 1
        if s.get("verified_publisher"):
            entry["verified"] = True
        for f in s.get("flags", []):
            entry["flag_counts"][f] = entry["flag_counts"].get(f, 0) + 1

    # Sort servers within each publisher by score desc
    for entry in ns_map.values():
        entry["servers"].sort(key=lambda x: x[1].get("trust_score", 0), reverse=True)
        count = len(entry["servers"])
        entry["avg_score"] = round(entry["total_score"] / count) if count else 0
        entry["server_count"] = count
        del entry["total_score"]

    # Map blog posts to publishers
    for post in posts:
        for pub in post.get("publishers", []):
            if pub in ns_map:
                ns_map[pub]["related_posts"].append(post)

    return ns_map


def derive_platforms(servers: dict) -> dict:
    """Group servers by target platform.

    Returns {platform_name: {
        name, slug, servers: [(name, data)], avg_score, server_count,
        bands, flag_counts
    }}
    """
    plat_map: dict[str, dict] = {}

    for name, s in servers.items():
        for target in s.get("targets", []):
            if target not in plat_map:
                plat_map[target] = {
                    "name": target,
                    "slug": slugify(target),
                    "servers": [],
                    "total_score": 0,
                    "bands": {"high": 0, "mod": 0, "low": 0, "vlow": 0, "unk": 0},
                    "flag_counts": {},
                }
            entry = plat_map[target]
            entry["servers"].append((name, s))
            entry["total_score"] += s.get("trust_score", 0)
            entry["bands"][score_band(s.get("trust_score", 0))] += 1
            for f in s.get("flags", []):
                entry["flag_counts"][f] = entry["flag_counts"].get(f, 0) + 1

    for entry in plat_map.values():
        entry["servers"].sort(key=lambda x: x[1].get("trust_score", 0), reverse=True)
        count = len(entry["servers"])
        entry["avg_score"] = round(entry["total_score"] / count) if count else 0
        entry["server_count"] = count
        del entry["total_score"]

    return plat_map


def derive_trust_bands(servers: dict) -> dict:
    """Group servers by trust band.

    Returns {band_key: {
        label, slug, servers: [(name, data)], count
    }}
    """
    bands = {
        "high": {"label": "High Trust", "slug": "high-trust", "servers": [], "min": 80, "max": 100},
        "mod": {"label": "Moderate Trust", "slug": "moderate", "servers": [], "min": 60, "max": 79},
        "low": {"label": "Low Trust", "slug": "low-trust", "servers": [], "min": 40, "max": 59},
        "vlow": {"label": "Very Low Trust", "slug": "very-low", "servers": [], "min": 20, "max": 39},
        "unk": {"label": "Suspicious", "slug": "suspicious", "servers": [], "min": 0, "max": 19},
    }

    for name, s in servers.items():
        band = score_band(s.get("trust_score", 0))
        bands[band]["servers"].append((name, s))

    for entry in bands.values():
        entry["servers"].sort(key=lambda x: x[1].get("trust_score", 0), reverse=True)
        entry["count"] = len(entry["servers"])

    return bands


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    return text.lower().replace(" ", "-").replace("/", "-").replace(".", "-")
