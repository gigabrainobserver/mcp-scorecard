"""Tests for scoring engine — categories and aggregate calculation."""

from __future__ import annotations

import json
from pathlib import Path

from mcp_scorecard.scoring.calculator import calculate_scores, get_trust_label
from mcp_scorecard.scoring.categories import (
    score_maintenance,
    score_permissions,
    score_popularity,
    score_provenance,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixtures() -> list[dict]:
    with open(FIXTURES / "sample_registry.json") as f:
        return json.load(f)


GOOD_SERVER_GITHUB = {
    "github_stars": 250,
    "github_forks": 40,
    "github_watchers": 15,
    "github_archived": False,
    "github_license": "MIT",
    "github_created_at": "2025-01-15T00:00:00Z",
    "github_pushed_at": "2026-02-10T00:00:00Z",
    "github_owner": "example",
    "github_contributors": 5,
    "github_commit_weeks_active": 30,
    "github_has_security_md": True,
    "github_has_code_of_conduct": True,
    "github_health_percentage": 85,
}


# --- Trust Label Tests ---


def test_trust_label_high():
    assert get_trust_label(85) == "High Trust"


def test_trust_label_moderate():
    assert get_trust_label(65) == "Moderate Trust"


def test_trust_label_low():
    assert get_trust_label(45) == "Low Trust"


def test_trust_label_very_low():
    assert get_trust_label(25) == "Very Low Trust"


def test_trust_label_suspicious():
    assert get_trust_label(10) == "Unknown/Suspicious"


# --- Provenance Tests ---


def test_provenance_good_server():
    servers = _load_fixtures()
    good = servers[0]
    score, signals = score_provenance(good, GOOD_SERVER_GITHUB)

    assert score >= 80, f"Good server provenance should be high, got {score}"
    assert signals["has_source_repo"] is True
    assert signals["repo_not_archived"] is True
    assert signals["has_license"] is True
    assert signals["has_installable_package"] is True
    assert signals["has_website_url"] is True
    assert signals["has_icon"] is True
    assert signals["has_security_md"] is True
    assert signals["has_code_of_conduct"] is True
    assert signals["unique_description"] is True


def test_provenance_spam_server():
    servers = _load_fixtures()
    spam = servers[1]  # ai.spammy/test-mcp
    score, signals = score_provenance(spam, None)

    assert score <= 10, f"Spam server provenance should be very low, got {score}"
    assert signals["has_source_repo"] is False
    assert signals["has_installable_package"] is False
    assert signals["unique_description"] is False


# --- Maintenance Tests ---


def test_maintenance_with_github():
    servers = _load_fixtures()
    good = servers[0]
    score, signals = score_maintenance(good, GOOD_SERVER_GITHUB)

    assert score >= 50, f"Active repo should score well on maintenance, got {score}"
    assert signals["repo_age_over_90d"] is True
    assert signals["active_commit_weeks"] == 30


def test_maintenance_without_github():
    servers = _load_fixtures()
    spam = servers[1]
    score, signals = score_maintenance(spam, None)

    # Only gets version_count stub points (5)
    assert score <= 10, f"No-github maintenance should be very low, got {score}"


# --- Popularity Tests ---


def test_popularity_with_github():
    servers = _load_fixtures()
    good = servers[0]
    score, signals = score_popularity(good, GOOD_SERVER_GITHUB)

    assert score > 0, "Server with 250 stars should have some popularity score"
    assert signals["github_stars"] == 250
    assert signals["github_forks"] == 40


def test_popularity_without_github():
    servers = _load_fixtures()
    spam = servers[1]
    score, signals = score_popularity(spam, None)

    assert score == 0
    assert signals["github_stars"] == 0


# --- Permissions Tests ---


def test_permissions_safe_server():
    servers = _load_fixtures()
    good = servers[0]  # 1 secret (API_KEY), stdio, api_key pattern
    score, signals = score_permissions(good, GOOD_SERVER_GITHUB)

    assert score >= 60, f"Server with 1 API key + stdio should be decent, got {score}"
    assert signals["secret_env_var_count"] == 1
    assert signals["transport_type_risk"] == 25  # stdio


def test_permissions_dangerous_server():
    servers = _load_fixtures()
    db = servers[2]  # 5 secrets, DB_PASSWORD, MASTER_KEY, mixed transport
    score, signals = score_permissions(db, None)

    assert score <= 40, f"Server with 5 secrets + DB passwords should score low, got {score}"
    assert signals["secret_env_var_count"] == 5
    assert signals["credential_sensitivity"] == 5  # MASTER_KEY = sensitive


def test_permissions_no_env_vars():
    servers = _load_fixtures()
    smithery = servers[3]  # no env vars, remote only
    score, signals = score_permissions(smithery, None)

    assert signals["secret_env_var_count"] == 0
    assert signals["credential_sensitivity"] == 20  # no vars = safest


# --- Aggregate Tests ---


def test_aggregate_good_server():
    servers = _load_fixtures()
    good = servers[0]
    result = calculate_scores(good, GOOD_SERVER_GITHUB)

    assert "trust_score" in result
    assert "trust_label" in result
    assert "scores" in result
    assert "signals" in result
    assert 0 <= result["trust_score"] <= 100
    assert result["trust_score"] >= 50, f"Good server should score decently, got {result['trust_score']}"


def test_aggregate_spam_server():
    servers = _load_fixtures()
    spam = servers[1]
    result = calculate_scores(spam, None)

    assert result["trust_score"] <= 30, f"Spam server should score very low, got {result['trust_score']}"
