"""GitHub API enricher.

Fetches repo metadata, community profile, and commit activity for each
server that has a GitHub repo URL. Results are cached to data/github_cache.json
so that multiple runs can build up full coverage within rate limits.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

import httpx

from mcp_scorecard import config
from mcp_scorecard.collectors.registry import ServerEntry


class GitHubData(TypedDict, total=False):
    github_stars: int | None
    github_forks: int | None
    github_watchers: int | None
    github_archived: bool | None
    github_license: str | None
    github_created_at: str | None
    github_pushed_at: str | None
    github_owner: str | None
    github_contributors: int | None
    github_commit_weeks_active: int | None
    github_has_security_md: bool | None
    github_has_code_of_conduct: bool | None
    github_health_percentage: int | None


# Matches github.com/owner/repo with optional .git suffix and trailing slash.
_GITHUB_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?/?$"
)


def _parse_repo_url(url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub URL, or None if not a match."""
    m = _GITHUB_RE.match(url.strip())
    if m:
        return m.group("owner"), m.group("repo")
    return None


class _RateLimitExhausted(Exception):
    """Raised when we should stop making GitHub API calls."""


class GitHubEnricher:
    """Fetches GitHub metadata for servers with GitHub repo URLs."""

    def __init__(self) -> None:
        token = os.environ.get("GITHUB_TOKEN")
        self._headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

        self._semaphore = asyncio.Semaphore(config.GITHUB_CONCURRENT_REQUESTS)
        self._rate_remaining: int | None = None
        self._rate_lock = asyncio.Lock()
        self._exhausted = False

    # ------------------------------------------------------------------
    # Rate-limit tracking
    # ------------------------------------------------------------------

    async def _update_rate_limit(self, response: httpx.Response) -> None:
        """Read X-RateLimit-Remaining from response headers and track it."""
        raw = response.headers.get("X-RateLimit-Remaining")
        if raw is None:
            return
        try:
            remaining = int(raw)
        except ValueError:
            return
        async with self._rate_lock:
            self._rate_remaining = remaining
            if remaining < config.GITHUB_RATE_LIMIT_BUFFER:
                self._exhausted = True

    async def _check_rate_limit(self) -> None:
        """Raise _RateLimitExhausted if we are at or below the buffer."""
        async with self._rate_lock:
            if self._exhausted:
                raise _RateLimitExhausted()

    # ------------------------------------------------------------------
    # Low-level API helpers
    # ------------------------------------------------------------------

    async def _get(
        self,
        client: httpx.AsyncClient,
        path: str,
    ) -> httpx.Response | None:
        """GET a GitHub API path with semaphore and rate-limit checks.

        Returns the Response on success, or None if rate-limited / errored.
        """
        await self._check_rate_limit()
        async with self._semaphore:
            try:
                resp = await client.get(
                    f"{config.GITHUB_API_BASE}{path}",
                    headers=self._headers,
                )
            except httpx.HTTPError:
                return None
            await self._update_rate_limit(resp)
            if resp.status_code == 403 and self._exhausted:
                return None
            return resp

    # ------------------------------------------------------------------
    # Per-repo fetchers
    # ------------------------------------------------------------------

    async def _fetch_repo_metadata(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
    ) -> dict | None:
        resp = await self._get(client, f"/repos/{owner}/{repo}")
        if resp is None or resp.status_code != 200:
            return None
        return resp.json()

    async def _fetch_community_profile(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
    ) -> dict | None:
        resp = await self._get(client, f"/repos/{owner}/{repo}/community/profile")
        if resp is None or resp.status_code != 200:
            return None
        return resp.json()

    async def _fetch_participation(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
    ) -> dict | None:
        resp = await self._get(client, f"/repos/{owner}/{repo}/stats/participation")
        if resp is None:
            return None
        # 202 = GitHub is computing stats; retry once after a short wait.
        if resp.status_code == 202:
            await asyncio.sleep(2)
            resp = await self._get(
                client, f"/repos/{owner}/{repo}/stats/participation"
            )
            if resp is None or resp.status_code != 200:
                return None
        if resp.status_code != 200:
            return None
        return resp.json()

    # ------------------------------------------------------------------
    # Single server enrichment
    # ------------------------------------------------------------------

    async def _enrich_one(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
    ) -> GitHubData:
        data = GitHubData()

        # Fire all three requests concurrently.
        try:
            meta_coro = self._fetch_repo_metadata(client, owner, repo)
            community_coro = self._fetch_community_profile(client, owner, repo)
            participation_coro = self._fetch_participation(client, owner, repo)

            meta, community, participation = await asyncio.gather(
                meta_coro, community_coro, participation_coro
            )
        except _RateLimitExhausted:
            return data

        # --- Repo metadata ---
        if meta is not None:
            data["github_stars"] = meta.get("stargazers_count")
            data["github_forks"] = meta.get("forks_count")
            data["github_watchers"] = meta.get("subscribers_count")
            data["github_archived"] = meta.get("archived")
            license_info = meta.get("license")
            data["github_license"] = (
                license_info.get("spdx_id") if isinstance(license_info, dict) else None
            )
            data["github_created_at"] = meta.get("created_at")
            data["github_pushed_at"] = meta.get("pushed_at")
            data["github_owner"] = owner

        # --- Community profile ---
        if community is not None:
            files = community.get("files") or {}
            data["github_has_security_md"] = files.get("security") is not None
            data["github_has_code_of_conduct"] = (
                files.get("code_of_conduct") is not None
            )
            data["github_health_percentage"] = community.get("health_percentage")

        # --- Participation / commit activity ---
        if participation is not None:
            all_weeks: list[int] = participation.get("all") or []
            if all_weeks:
                data["github_commit_weeks_active"] = sum(
                    1 for w in all_weeks if w > 0
                )
                data["github_contributors"] = _estimate_contributors(
                    all_weeks,
                    participation.get("owner") or [],
                )
            else:
                data["github_commit_weeks_active"] = None
                data["github_contributors"] = None
        else:
            data["github_commit_weeks_active"] = None
            data["github_contributors"] = None

        return data

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(
        self, servers: list[ServerEntry], cache: dict | None = None
    ) -> dict[str, GitHubData]:
        """Enrich servers that have a GitHub repo URL, skipping cached ones.

        Returns a dict keyed by server name (only freshly fetched servers).
        """
        cache = cache or {}

        # Build work list, skipping fresh cache entries
        work: list[tuple[str, str, str]] = []
        skipped = 0
        for srv in servers:
            url = srv.get("repo_url")
            if not url:
                continue
            parsed = _parse_repo_url(url)
            if parsed is None:
                continue
            name = srv["name"]
            if name in cache and not _is_stale(cache[name]):
                skipped += 1
                continue
            work.append((name, parsed[0], parsed[1]))

        if skipped:
            print(f"Skipping {skipped} servers with fresh cache entries.")

        if not work:
            print("No servers need enrichment (all cached).")
            return {}

        remaining_str = "unknown"
        if self._rate_remaining is not None:
            remaining_str = str(self._rate_remaining)

        print(
            f"Enriching {len(work)} servers with GitHub repos... "
            f"(rate limit: {remaining_str} remaining)"
        )

        results: dict[str, GitHubData] = {}

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Pre-check rate limit with a lightweight call.
            try:
                probe = await self._get(client, "/rate_limit")
                if probe is not None and probe.status_code == 200:
                    core = probe.json().get("resources", {}).get("core", {})
                    self._rate_remaining = core.get("remaining")
                    if (
                        self._rate_remaining is not None
                        and self._rate_remaining < config.GITHUB_RATE_LIMIT_BUFFER
                    ):
                        self._exhausted = True
                    print(
                        f"Enriching {len(work)} servers with GitHub repos... "
                        f"(rate limit: {self._rate_remaining} remaining)"
                    )
            except _RateLimitExhausted:
                print("Rate limit already exhausted. Skipping GitHub enrichment.")
                return {}

            # Process in batches sized to the semaphore.
            batch_size = config.GITHUB_CONCURRENT_REQUESTS

            for i in range(0, len(work), batch_size):
                if self._exhausted:
                    print(
                        f"Rate limit buffer reached after {len(results)} servers. "
                        "Stopping GitHub enrichment."
                    )
                    break

                batch = work[i : i + batch_size]
                tasks = [
                    self._enrich_one(client, owner, repo)
                    for _, owner, repo in batch
                ]
                batch_results = await asyncio.gather(*tasks)

                for (name, _, _), data in zip(batch, batch_results):
                    if data:
                        results[name] = data

                done = min(i + batch_size, len(work))
                remaining_str = (
                    str(self._rate_remaining)
                    if self._rate_remaining is not None
                    else "unknown"
                )
                print(
                    f"  GitHub enrichment progress: {done}/{len(work)} "
                    f"(rate limit: {remaining_str} remaining)"
                )

        print(f"GitHub enrichment complete: {len(results)} servers enriched.")
        return results


def _estimate_contributors(
    all_weeks: list[int], owner_weeks: list[int]
) -> int | None:
    """Estimate contributor count from participation stats.

    The participation endpoint returns "all" (total commits per week) and
    "owner" (repo owner commits per week). If there are commits in weeks
    where the owner has none, other contributors exist. This is a rough
    heuristic -- the real number requires paginating /contributors.

    We use a simple approach: count weeks where all > owner (someone
    else committed). If there are such weeks, we know there are at
    least 2 contributors. The more such weeks, the more likely there
    are many contributors. But we cap the heuristic and return a
    conservative lower bound.
    """
    if not all_weeks:
        return None

    # If owner_weeks is empty or wrong length, fall back to just
    # checking non-zero weeks in all_weeks.
    if not owner_weeks or len(owner_weeks) != len(all_weeks):
        active = sum(1 for w in all_weeks if w > 0)
        return max(1, active // 10) if active > 0 else None

    other_weeks = sum(
        1 for a, o in zip(all_weeks, owner_weeks) if a > o
    )
    total_active = sum(1 for w in all_weeks if w > 0)

    if total_active == 0:
        return None
    if other_weeks == 0:
        return 1  # solo developer
    # Rough heuristic: more "other" weeks -> more contributors.
    # This is imprecise but avoids an extra API call.
    if other_weeks >= 40:
        return 10
    if other_weeks >= 25:
        return 7
    if other_weeks >= 15:
        return 5
    if other_weeks >= 8:
        return 3
    return 2


def _load_cache() -> dict:
    """Load the GitHub enrichment cache from disk."""
    path = Path(config.GITHUB_CACHE_FILE)
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    """Write the GitHub enrichment cache to disk."""
    path = Path(config.GITHUB_CACHE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(cache, f, separators=(",", ":"))


def _is_stale(entry: dict) -> bool:
    """Check if a cache entry is older than the max age."""
    cached_at = entry.get("_cached_at")
    if cached_at is None:
        return True
    age_days = (time.time() - cached_at) / 86400
    return age_days > config.GITHUB_CACHE_MAX_AGE_DAYS


async def enrich(servers: list[ServerEntry]) -> dict[str, GitHubData]:
    """Main entry point for GitHub enrichment.

    Loads cached data, fetches only new/stale servers, merges, saves cache.

    Args:
        servers: List of ServerEntry dicts from the registry collector.

    Returns:
        Dict keyed by server name with GitHubData values.
    """
    cache = _load_cache()
    cached_count = len(cache)

    enricher = GitHubEnricher()
    fresh = await enricher.run(servers, cache)

    # Merge fresh results into cache with timestamp
    now = time.time()
    for name, data in fresh.items():
        cache[name] = {**data, "_cached_at": now}

    _save_cache(cache)

    # Return all cached data (strip internal _cached_at field)
    results: dict[str, GitHubData] = {}
    for name, entry in cache.items():
        cleaned = {k: v for k, v in entry.items() if not k.startswith("_")}
        results[name] = GitHubData(**cleaned)

    new_count = len(cache) - cached_count
    print(f"Cache: {new_count} new, {len(cache)} total ({cached_count} from previous runs)")

    return results
