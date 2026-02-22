"""Pipeline orchestrator — collect → enrich → score → publish."""

from __future__ import annotations

import asyncio
import time

from mcp_scorecard.collectors.registry import collect
from mcp_scorecard.enrichers.github import enrich
from mcp_scorecard.output.writer import write_all
from mcp_scorecard.scoring.calculator import calculate_scores
from mcp_scorecard.scoring.flags import build_flag_context, detect_flags


async def run(output_dir: str | None = None) -> None:
    t0 = time.monotonic()

    # Stage 1: Collect
    print("=" * 60)
    print("STAGE 1: COLLECT")
    print("=" * 60)
    servers = await collect()
    print(f"Collected {len(servers)} servers")

    # Stage 2: Enrich
    print()
    print("=" * 60)
    print("STAGE 2: ENRICH")
    print("=" * 60)
    github_data = await enrich(servers)
    print(f"Enriched {len(github_data)} servers with GitHub data")

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
        scored[name] = result

    flagged = sum(1 for s in scored.values() if s["flags"])
    print(f"Scored {len(scored)} servers, {flagged} flagged")

    # Stage 4: Publish
    print()
    print("=" * 60)
    print("STAGE 4: PUBLISH")
    print("=" * 60)
    write_all(scored, output_dir)

    elapsed = time.monotonic() - t0
    print(f"\nPipeline complete in {elapsed:.1f}s")
