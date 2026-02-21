"""Tests for red flag detection."""

from __future__ import annotations

import json
from pathlib import Path

from mcp_scorecard.scoring.flags import build_flag_context, detect_flags

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixtures() -> list[dict]:
    with open(FIXTURES / "sample_registry.json") as f:
        return json.load(f)


def _ctx():
    return build_flag_context(_load_fixtures())


# --- Individual Flag Tests ---


def test_dead_entry():
    servers = _load_fixtures()
    spam = servers[1]  # no packages, no remotes
    ctx = _ctx()
    flags = detect_flags(spam, None, ctx)
    assert "DEAD_ENTRY" in flags


def test_not_dead_with_packages():
    servers = _load_fixtures()
    good = servers[0]  # has packages
    ctx = _ctx()
    flags = detect_flags(good, None, ctx)
    assert "DEAD_ENTRY" not in flags


def test_not_dead_with_remotes():
    servers = _load_fixtures()
    smithery = servers[3]  # has remotes
    ctx = _ctx()
    flags = detect_flags(smithery, None, ctx)
    assert "DEAD_ENTRY" not in flags


def test_template_description():
    servers = _load_fixtures()
    spam = servers[1]  # "A model context protocol server"
    ctx = _ctx()
    flags = detect_flags(spam, None, ctx)
    assert "TEMPLATE_DESCRIPTION" in flags


def test_no_template_description():
    servers = _load_fixtures()
    good = servers[0]
    ctx = _ctx()
    flags = detect_flags(good, None, ctx)
    assert "TEMPLATE_DESCRIPTION" not in flags


def test_high_secret_demand():
    servers = _load_fixtures()
    db = servers[2]  # 5 secret env vars
    ctx = _ctx()
    flags = detect_flags(db, None, ctx)
    assert "HIGH_SECRET_DEMAND" in flags


def test_no_high_secret_demand():
    servers = _load_fixtures()
    good = servers[0]  # 1 secret env var
    ctx = _ctx()
    flags = detect_flags(good, None, ctx)
    assert "HIGH_SECRET_DEMAND" not in flags


def test_sensitive_cred_request():
    servers = _load_fixtures()
    db = servers[2]  # DB_PASSWORD, MASTER_KEY
    ctx = _ctx()
    flags = detect_flags(db, None, ctx)
    assert "SENSITIVE_CRED_REQUEST" in flags


def test_repo_archived():
    servers = _load_fixtures()
    good = servers[0]
    github = {"github_archived": True}
    ctx = _ctx()
    flags = detect_flags(good, github, ctx)
    assert "REPO_ARCHIVED" in flags


def test_no_source():
    servers = _load_fixtures()
    spam = servers[1]  # no repo_url, no package_identifiers
    ctx = _ctx()
    flags = detect_flags(spam, None, ctx)
    assert "NO_SOURCE" in flags


def test_no_source_not_flagged_with_packages():
    servers = _load_fixtures()
    good = servers[0]  # has repo_url
    ctx = _ctx()
    flags = detect_flags(good, None, ctx)
    assert "NO_SOURCE" not in flags


# --- Multiple Flags ---


def test_spam_server_gets_multiple_flags():
    servers = _load_fixtures()
    spam = servers[1]
    ctx = _ctx()
    flags = detect_flags(spam, None, ctx)
    assert "DEAD_ENTRY" in flags
    assert "TEMPLATE_DESCRIPTION" in flags
    assert "NO_SOURCE" in flags


# --- Bulk Publisher (needs >20 in namespace, not testable with 4 fixtures) ---


# --- Flag Context ---


def test_flag_context_namespace_counts():
    ctx = _ctx()
    assert ctx.namespace_counts["io.github.example"] == 1
    assert ctx.namespace_counts["ai.spammy"] == 1


def test_flag_context_description_ns_counts():
    ctx = _ctx()
    # "a model context protocol server" appears in 2 namespaces (ai.spammy, ai.smithery)
    assert ctx.description_ns_counts["a model context protocol server"] == 2
