"""Seed Supabase from existing index.json and github_cache.json.

Usage:
    uv run python scripts/seed_db.py

Requires SUPABASE_URL and SUPABASE_KEY (service role) in .env or environment.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
BATCH_SIZE = 100


def load_env():
    """Load .env file if present."""
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def load_index() -> dict:
    """Load output/index.json."""
    path = ROOT / "output" / "index.json"
    if not path.exists():
        print(f"ERROR: {path} not found. Run the pipeline first.")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def load_github_cache() -> dict:
    """Load data/github_cache.json."""
    path = ROOT / "data" / "github_cache.json"
    if not path.exists():
        print(f"WARNING: {path} not found. Skipping enrichment seed.")
        return {}
    with open(path) as f:
        return json.load(f)


def batch_upsert(table, rows: list[dict], client, on_conflict: str):
    """Upsert rows in batches."""
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        client.table(table).upsert(batch, on_conflict=on_conflict).execute()
        total += len(batch)
        print(f"  {table}: {total}/{len(rows)}", end="\r")
    print(f"  {table}: {total}/{len(rows)} done")


def main():
    load_env()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_KEY in .env or environment.")
        sys.exit(1)

    client = create_client(url, key)

    # Load data
    print("Loading index.json...")
    index_data = load_index()
    servers_data = index_data["servers"]
    generated_at = index_data["generated_at"]
    print(f"  {len(servers_data)} servers loaded")

    print("Loading github_cache.json...")
    github_cache = load_github_cache()
    print(f"  {len(github_cache)} enrichment entries loaded")

    # Step 1: Create pipeline run for the seed
    print("\nCreating seed pipeline run...")
    run_result = (
        client.table("pipeline_runs")
        .insert(
            {
                "started_at": generated_at,
                "completed_at": generated_at,
                "server_count": len(servers_data),
                "status": "completed",
                "metadata": {"source": "seed_from_index_json", "version": index_data["version"]},
            }
        )
        .execute()
    )
    run_id = run_result.data[0]["id"]
    print(f"  Pipeline run created: {run_id}")

    # Step 2: Upsert servers
    print("\nUpserting servers...")
    server_rows = []
    for name in servers_data:
        parts = name.split("/", 1)
        namespace = parts[0]
        server_id = parts[1] if len(parts) > 1 else name
        server_data = servers_data[name]
        server_rows.append(
            {
                "name": name,
                "namespace": namespace,
                "server_id": server_id,
                "title": None,
                "description": None,
            }
        )
    batch_upsert("servers", server_rows, client, on_conflict="name")

    # Step 3: Fetch server UUIDs for FK lookups
    print("\nFetching server UUIDs...")
    name_to_uuid = {}
    # Fetch in pages since there are ~2800 rows
    offset = 0
    page_size = 1000
    while True:
        result = (
            client.table("servers")
            .select("id, name")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        for row in result.data:
            name_to_uuid[row["name"]] = row["id"]
        if len(result.data) < page_size:
            break
        offset += page_size
    print(f"  {len(name_to_uuid)} UUIDs fetched")

    # Step 4: Upsert github enrichments
    if github_cache:
        print("\nUpserting github enrichments...")
        enrichment_rows = []
        skipped = 0
        for name, gh in github_cache.items():
            uuid = name_to_uuid.get(name)
            if not uuid:
                skipped += 1
                continue

            cached_at = gh.get("_cached_at")
            enriched_at = (
                datetime.fromtimestamp(cached_at, tz=timezone.utc).isoformat()
                if cached_at
                else None
            )

            enrichment_rows.append(
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
                    "enriched_at": enriched_at,
                }
            )
        batch_upsert("github_enrichments", enrichment_rows, client, on_conflict="server_id")
        if skipped:
            print(f"  Skipped {skipped} cache entries (server not in index)")

    # Step 5: Insert score snapshots
    print("\nInserting score snapshots...")
    snapshot_rows = []
    for name, server in servers_data.items():
        uuid = name_to_uuid.get(name)
        if not uuid:
            continue

        scores = server["scores"]
        snapshot_rows.append(
            {
                "server_id": uuid,
                "run_id": run_id,
                "trust_score": server["trust_score"],
                "trust_label": server["trust_label"],
                "provenance": scores["provenance"],
                "maintenance": scores["maintenance"],
                "popularity": scores["popularity"],
                "permissions": scores["permissions"],
                "signals": server.get("signals", {}),
                "flags": server.get("flags", []),
                "badges": server.get("badges", {}),
                "verified_publisher": server.get("verified_publisher", False),
                "targets": server.get("targets", []),
                "scored_at": generated_at,
            }
        )
    batch_upsert("score_snapshots", snapshot_rows, client, on_conflict="server_id,run_id")

    # Step 6: Refresh materialized view
    print("\nRefreshing latest_scores materialized view...")
    client.rpc("refresh_latest_scores", {}).execute()

    # Step 7: Verification
    print("\n--- Verification ---")
    for table in ["servers", "score_snapshots", "github_enrichments", "pipeline_runs"]:
        result = client.table(table).select("id", count="exact").limit(0).execute()
        print(f"  {table}: {result.count} rows")

    # Spot check a known server
    print("\nSpot check (top server by trust_score):")
    result = (
        client.table("score_snapshots")
        .select("trust_score, trust_label, server_id")
        .order("trust_score", desc=True)
        .limit(5)
        .execute()
    )
    for row in result.data:
        # Look up name
        srv = client.table("servers").select("name").eq("id", row["server_id"]).single().execute()
        print(f"  {srv.data['name']}: {row['trust_score']} ({row['trust_label']})")

    print("\nSeed complete!")


if __name__ == "__main__":
    main()
