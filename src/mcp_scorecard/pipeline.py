"""Pipeline orchestrator — collect → enrich → score → publish."""

from __future__ import annotations

import asyncio
import time
from statistics import median

from mcp_scorecard.collectors.registry import collect
from mcp_scorecard.enrichers.github import enrich
from mcp_scorecard.output.database import DatabaseWriter
from mcp_scorecard.output.writer import write_all
from mcp_scorecard.scoring.calculator import calculate_scores
from mcp_scorecard.scoring.flags import build_flag_context, detect_flags


async def run(output_dir: str | None = None) -> None:
    t0 = time.monotonic()

    # Optional database writer (active when SUPABASE_URL is set)
    db = DatabaseWriter.from_env()
    if db:
        print("Database writer: ENABLED (Supabase)")
        run_id = db.create_run()
    else:
        print("Database writer: disabled (set SUPABASE_URL to enable)")

    # Stage 1: Collect
    print("=" * 60)
    print("STAGE 1: COLLECT")
    print("=" * 60)
    servers = await collect()
    print(f"Collected {len(servers)} servers")

    if db:
        print("  Writing servers to database...")
        db.upsert_servers(servers)
        db.upsert_registry_entries(servers)
        print(f"  Upserted {len(servers)} servers + registry entries")

    # Stage 2: Enrich
    print()
    print("=" * 60)
    print("STAGE 2: ENRICH")
    print("=" * 60)
    github_data = await enrich(servers)
    print(f"Enriched {len(github_data)} servers with GitHub data")

    if db:
        print("  Writing enrichments to database...")
        db.upsert_enrichments(github_data)
        print(f"  Upserted {len(github_data)} enrichment records")

    # Stage 3: Score
    print()
    print("=" * 60)
    print("STAGE 3: SCORE")
    print("=" * 60)
    flag_context = build_flag_context(servers)
    scored: dict[str, dict] = {}

    for server in servers:
        name = server["name"]
        gh = github_data.get(name)
        flags = detect_flags(server, gh, flag_context)
        result = calculate_scores(server, gh, flags=flags)
        result["flags"] = flags
        result["install"] = {
            "repo_url": server.get("repo_url"),
            "version": server.get("version"),
            "package_types": server.get("package_types", []),
            "package_identifiers": server.get("package_identifiers", []),
            "transport_types": server.get("transport_types", []),
            "env_vars": server.get("env_vars", []),
        }
        scored[name] = result

    flagged = sum(1 for s in scored.values() if s["flags"])
    print(f"Scored {len(scored)} servers, {flagged} flagged")

    # Stage 4: Publish
    print()
    print("=" * 60)
    print("STAGE 4: PUBLISH")
    print("=" * 60)
    write_all(scored, output_dir)

    if db:
        print("  Writing scores to database...")
        db.write_scores(scored)
        scores_list = [s["trust_score"] for s in scored.values()]
        avg = round(sum(scores_list) / len(scores_list), 1) if scores_list else 0
        med = int(median(scores_list)) if scores_list else 0
        db.complete_run(
            server_count=len(scored),
            flagged=flagged,
            avg_score=avg,
            median_score=med,
        )
        db.refresh_latest_scores()
        print(f"  Database updated: {len(scored)} scores, view refreshed")

    elapsed = time.monotonic() - t0
    print(f"\nPipeline complete in {elapsed:.1f}s")
