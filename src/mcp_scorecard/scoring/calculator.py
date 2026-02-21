"""Aggregate score computation — combines category scores into a trust score."""

from __future__ import annotations

from typing import Any

from mcp_scorecard.config import CATEGORY_WEIGHTS, SCORE_BANDS

from .categories import (
    score_maintenance,
    score_permissions,
    score_popularity,
    score_provenance,
)

# Type aliases
ServerEntry = dict[str, Any]
GitHubData = dict[str, Any]


def get_trust_label(score: int) -> str:
    """Map a 0-100 trust score to a human-readable label via SCORE_BANDS."""
    for low, high, label in SCORE_BANDS:
        if low <= score <= high:
            return label
    return "Unknown/Suspicious"


def calculate_scores(
    server: ServerEntry, github_data: GitHubData | None
) -> dict[str, Any]:
    """Run all category scorers and compute weighted aggregate.

    Returns:
        {
            "trust_score": int,
            "trust_label": str,
            "scores": {"provenance": int, ...},
            "signals": {merged signals dict},
        }
    """
    # Run each category scorer
    prov_score, prov_signals = score_provenance(server, github_data)
    maint_score, maint_signals = score_maintenance(server, github_data)
    pop_score, pop_signals = score_popularity(server, github_data)
    perm_score, perm_signals = score_permissions(server, github_data)

    scores = {
        "provenance": prov_score,
        "maintenance": maint_score,
        "popularity": pop_score,
        "permissions": perm_score,
    }

    # Weighted aggregate
    weighted = sum(
        scores[cat] * CATEGORY_WEIGHTS[cat] for cat in CATEGORY_WEIGHTS
    )
    trust_score = min(round(weighted), 100)

    # Merge all signals
    signals: dict[str, Any] = {}
    signals.update(prov_signals)
    signals.update(maint_signals)
    signals.update(pop_signals)
    signals.update(perm_signals)

    return {
        "trust_score": trust_score,
        "trust_label": get_trust_label(trust_score),
        "scores": scores,
        "signals": signals,
    }
