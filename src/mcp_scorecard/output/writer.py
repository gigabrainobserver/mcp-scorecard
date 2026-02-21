"""JSON output writer — produces index.json, stats.json, flags.json."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from mcp_scorecard.config import OUTPUT_DIR, SCORE_BANDS
from mcp_scorecard.output.models import (
    CategoryScores,
    FlagGroup,
    FlagsIndex,
    ScoreBand,
    ScorecardIndex,
    ServerScore,
    StatsIndex,
    TopServer,
)


def write_all(
    scored_servers: dict[str, dict],
    output_dir: str | None = None,
) -> None:
    out = Path(output_dir or OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)

    index = _build_index(scored_servers, now)
    stats = _build_stats(scored_servers, now)
    flags = _build_flags(scored_servers, now)

    _write_json(out / "index.json", index)
    _write_json(out / "stats.json", stats)
    _write_json(out / "flags.json", flags)

    print(f"Wrote {len(scored_servers)} servers to {out}/")


def _build_index(
    scored_servers: dict[str, dict], now: datetime
) -> ScorecardIndex:
    servers = {}
    for name, data in scored_servers.items():
        servers[name] = ServerScore(
            trust_score=data["trust_score"],
            trust_label=data["trust_label"],
            scores=CategoryScores(**data["scores"]),
            signals=data["signals"],
            flags=data["flags"],
        )
    return ScorecardIndex(
        generated_at=now,
        server_count=len(servers),
        servers=servers,
    )


def _build_stats(
    scored_servers: dict[str, dict], now: datetime
) -> StatsIndex:
    scores = [d["trust_score"] for d in scored_servers.values()]
    flag_counter: Counter[str] = Counter()
    servers_with_repo = 0
    servers_with_packages = 0

    for data in scored_servers.values():
        for f in data["flags"]:
            flag_counter[f] += 1
        if data["signals"].get("has_source_repo"):
            servers_with_repo += 1
        if data["signals"].get("has_installable_package"):
            servers_with_packages += 1

    # Score distribution by band
    distribution = []
    for low, high, label in SCORE_BANDS:
        count = sum(1 for s in scores if low <= s <= high)
        distribution.append(
            ScoreBand(label=label, min_score=low, max_score=high, count=count)
        )

    # Top 25 servers by score
    sorted_servers = sorted(
        scored_servers.items(), key=lambda x: x[1]["trust_score"], reverse=True
    )
    top = [
        TopServer(
            name=name,
            trust_score=data["trust_score"],
            trust_label=data["trust_label"],
        )
        for name, data in sorted_servers[:25]
    ]

    return StatsIndex(
        generated_at=now,
        server_count=len(scores),
        servers_with_repo=servers_with_repo,
        servers_with_packages=servers_with_packages,
        score_distribution=distribution,
        flag_summary=dict(flag_counter.most_common()),
        top_servers=top,
        average_trust_score=round(sum(scores) / len(scores), 1) if scores else 0,
        median_trust_score=int(median(scores)) if scores else 0,
    )


def _build_flags(
    scored_servers: dict[str, dict], now: datetime
) -> FlagsIndex:
    flag_groups: dict[str, list[str]] = {}
    for name, data in scored_servers.items():
        for f in data["flags"]:
            flag_groups.setdefault(f, []).append(name)

    groups = [
        FlagGroup(flag=flag, count=len(servers), servers=sorted(servers))
        for flag, servers in sorted(flag_groups.items())
    ]

    return FlagsIndex(generated_at=now, flags=groups)


def _write_json(path: Path, model) -> None:
    with open(path, "w") as f:
        f.write(model.model_dump_json(indent=2))
