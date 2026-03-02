"""Supabase database writer — writes pipeline results to Postgres.

Only active when SUPABASE_URL is set in the environment. The pipeline
continues to write JSON files regardless; this is an additional output.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp_scorecard.collectors.registry import ServerEntry
from mcp_scorecard.config import VERIFIED_PUBLISHERS
from mcp_scorecard.enrichers.github import GitHubData
from mcp_scorecard.scoring.targets import infer_targets

BATCH_SIZE = 100


def _load_env() -> None:
    """Load .env file from project root if present."""
    # Walk up from this file to find project root
    root = Path(__file__).resolve().parent.parent.parent.parent
    env_path = root / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


class DatabaseWriter:
    """Writes pipeline data to Supabase."""

    def __init__(self, url: str, key: str) -> None:
        from supabase import create_client

        self._client = create_client(url, key)
        self._run_id: str | None = None

    @classmethod
    def from_env(cls) -> DatabaseWriter | None:
        """Create a DatabaseWriter from environment variables.

        Returns None if SUPABASE_URL is not set.
        """
        _load_env()
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            return None
        return cls(url, key)

    # ------------------------------------------------------------------
    # Pipeline run bookkeeping
    # ------------------------------------------------------------------

    def create_run(self) -> str:
        """Create a new pipeline_runs row. Returns the run UUID."""
        result = (
            self._client.table("pipeline_runs")
            .insert({"status": "running"})
            .execute()
        )
        self._run_id = result.data[0]["id"]
        return self._run_id

    def complete_run(self, server_count: int, flagged: int, avg_score: float, median_score: int) -> None:
        """Mark the current pipeline run as completed with stats."""
        if not self._run_id:
            return
        (
            self._client.table("pipeline_runs")
            .update(
                {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "server_count": server_count,
                    "servers_flagged": flagged,
                    "average_score": avg_score,
                    "median_score": median_score,
                    "status": "completed",
                }
            )
            .eq("id", self._run_id)
            .execute()
        )

    # ------------------------------------------------------------------
    # Server identity upserts
    # ------------------------------------------------------------------

    def upsert_servers(self, servers: list[ServerEntry]) -> None:
        """Upsert canonical server identity rows."""
        rows = [
            {
                "name": s["name"],
                "namespace": s["namespace"],
                "server_id": s["server_id"],
                "title": s.get("title"),
                "description": s.get("description"),
            }
            for s in servers
        ]
        self._batch_upsert("servers", rows, on_conflict="name")

    def upsert_registry_entries(self, servers: list[ServerEntry]) -> None:
        """Upsert registry entry data for each server."""
        name_to_uuid = self._fetch_server_uuids()

        rows = []
        for s in servers:
            uuid = name_to_uuid.get(s["name"])
            if not uuid:
                continue
            rows.append(
                {
                    "server_id": uuid,
                    "registry_source": "mcp_official",
                    "version": s.get("version"),
                    "repo_url": s.get("repo_url"),
                    "repo_source": s.get("repo_source"),
                    "has_packages": s.get("has_packages", False),
                    "package_types": s.get("package_types", []),
                    "package_identifiers": s.get("package_identifiers", []),
                    "has_remotes": s.get("has_remotes", False),
                    "transport_types": s.get("transport_types", []),
                    "env_vars": s.get("env_vars", []),
                    "has_website": s.get("has_website", False),
                    "has_icon": s.get("has_icon", False),
                    "published_at": s.get("published_at") or None,
                    "updated_at": s.get("updated_at") or None,
                }
            )
        self._batch_upsert("registry_entries", rows, on_conflict="server_id,registry_source")

    # ------------------------------------------------------------------
    # GitHub enrichment upserts
    # ------------------------------------------------------------------

    def upsert_enrichments(self, github_data: dict[str, GitHubData]) -> None:
        """Upsert GitHub enrichment data."""
        if not github_data:
            return

        name_to_uuid = self._fetch_server_uuids()
        now = datetime.now(timezone.utc).isoformat()

        rows = []
        for name, gh in github_data.items():
            uuid = name_to_uuid.get(name)
            if not uuid:
                continue
            rows.append(
                {
                    "server_id": uuid,
                    "github_stars": gh.get("github_stars"),
                    "github_forks": gh.get("github_forks"),
                    "github_watchers": gh.get("github_watchers"),
                    "github_archived": gh.get("github_archived"),
                    "github_license": gh.get("github_license"),
                    "github_created_at": gh.get("github_created_at"),
                    "github_pushed_at": gh.get("github_pushed_at"),
                    "github_owner": gh.get("github_owner"),
                    "github_contributors": gh.get("github_contributors"),
                    "github_commit_weeks_active": gh.get("github_commit_weeks_active"),
                    "github_has_security_md": gh.get("github_has_security_md"),
                    "github_has_code_of_conduct": gh.get("github_has_code_of_conduct"),
                    "github_health_percentage": gh.get("github_health_percentage"),
                    "enriched_at": now,
                }
            )
        self._batch_upsert("github_enrichments", rows, on_conflict="server_id")

    # ------------------------------------------------------------------
    # Score snapshot writes
    # ------------------------------------------------------------------

    def write_scores(self, scored: dict[str, dict]) -> None:
        """Insert score snapshots for the current pipeline run."""
        if not self._run_id:
            raise RuntimeError("No active pipeline run. Call create_run() first.")

        name_to_uuid = self._fetch_server_uuids()
        now = datetime.now(timezone.utc).isoformat()

        rows = []
        for name, data in scored.items():
            uuid = name_to_uuid.get(name)
            if not uuid:
                continue

            ns = name.split("/")[0] if "/" in name else ""
            scores = data["scores"]
            rows.append(
                {
                    "server_id": uuid,
                    "run_id": self._run_id,
                    "trust_score": data["trust_score"],
                    "trust_label": data["trust_label"],
                    "provenance": scores["provenance"],
                    "maintenance": scores["maintenance"],
                    "popularity": scores["popularity"],
                    "permissions": scores["permissions"],
                    "signals": data.get("signals", {}),
                    "flags": data.get("flags", []),
                    "badges": data.get("badges", {}),
                    "verified_publisher": ns in VERIFIED_PUBLISHERS,
                    "targets": infer_targets(name),
                    "scored_at": now,
                }
            )
        self._batch_upsert("score_snapshots", rows, on_conflict="server_id,run_id")

    # ------------------------------------------------------------------
    # Materialized view refresh
    # ------------------------------------------------------------------

    def refresh_latest_scores(self) -> None:
        """Refresh the latest_scores materialized view."""
        self._client.rpc("refresh_latest_scores", {}).execute()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_server_uuids(self) -> dict[str, str]:
        """Fetch all server name→UUID mappings."""
        name_to_uuid: dict[str, str] = {}
        offset = 0
        page_size = 1000
        while True:
            result = (
                self._client.table("servers")
                .select("id, name")
                .range(offset, offset + page_size - 1)
                .execute()
            )
            for row in result.data:
                name_to_uuid[row["name"]] = row["id"]
            if len(result.data) < page_size:
                break
            offset += page_size
        return name_to_uuid

    def _batch_upsert(self, table: str, rows: list[dict], on_conflict: str) -> None:
        """Upsert rows in batches."""
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            self._client.table(table).upsert(batch, on_conflict=on_conflict).execute()
