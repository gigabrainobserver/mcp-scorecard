-- MCP Scorecard — Supabase Schema
-- Run this in Supabase SQL Editor after enabling pg_trgm extension.

-- Enable trigram extension for fuzzy name search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- Table: pipeline_runs
-- One row per pipeline execution. Groups score_snapshots.
-- ============================================================
CREATE TABLE pipeline_runs (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    started_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    server_count    INTEGER,
    servers_enriched INTEGER,
    servers_flagged INTEGER,
    average_score   REAL,
    median_score    SMALLINT,
    status          TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_runs_completed ON pipeline_runs(completed_at DESC);

-- ============================================================
-- Table: servers
-- Canonical identity. One row per unique server across all registries.
-- ============================================================
CREATE TABLE servers (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,        -- "io.github.user/server-name"
    namespace       TEXT NOT NULL,               -- "io.github.user"
    server_id       TEXT NOT NULL,               -- "server-name"
    title           TEXT,
    description     TEXT,
    first_seen_at   TIMESTAMPTZ DEFAULT now(),

    -- Dedup support: canonical pointer for when duplicates are identified
    canonical_id    UUID REFERENCES servers(id),

    UNIQUE(namespace, server_id)
);

CREATE INDEX idx_servers_namespace ON servers(namespace);
CREATE INDEX idx_servers_name_trgm ON servers USING gin(name gin_trgm_ops);

-- ============================================================
-- Table: registry_entries
-- Raw data from each registry source. Supports multi-registry.
-- ============================================================
CREATE TABLE registry_entries (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    server_id           UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    registry_source     TEXT NOT NULL DEFAULT 'mcp_official',

    version             TEXT,
    repo_url            TEXT,
    repo_source         TEXT,
    has_packages        BOOLEAN DEFAULT FALSE,
    package_types       TEXT[] DEFAULT '{}',
    package_identifiers TEXT[] DEFAULT '{}',
    has_remotes         BOOLEAN DEFAULT FALSE,
    transport_types     TEXT[] DEFAULT '{}',
    env_vars            JSONB DEFAULT '[]',
    has_website         BOOLEAN DEFAULT FALSE,
    has_icon            BOOLEAN DEFAULT FALSE,
    published_at        TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ,

    collected_at        TIMESTAMPTZ DEFAULT now(),
    raw_data            JSONB,

    UNIQUE(server_id, registry_source)
);

CREATE INDEX idx_registry_server ON registry_entries(server_id);
CREATE INDEX idx_registry_source ON registry_entries(registry_source);

-- ============================================================
-- Table: github_enrichments
-- GitHub API data. Replaces data/github_cache.json.
-- ============================================================
CREATE TABLE github_enrichments (
    id                          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    server_id                   UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE UNIQUE,

    github_stars                INTEGER,
    github_forks                INTEGER,
    github_watchers             INTEGER,
    github_archived             BOOLEAN,
    github_license              TEXT,
    github_created_at           TIMESTAMPTZ,
    github_pushed_at            TIMESTAMPTZ,
    github_owner                TEXT,
    github_contributors         INTEGER,
    github_commit_weeks_active  INTEGER,
    github_has_security_md      BOOLEAN,
    github_has_code_of_conduct  BOOLEAN,
    github_health_percentage    INTEGER,

    enriched_at                 TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_enrichment_server ON github_enrichments(server_id);
CREATE INDEX idx_enrichment_stale ON github_enrichments(enriched_at);

-- ============================================================
-- Table: score_snapshots
-- Historical scores. One row per server per pipeline run.
-- ============================================================
CREATE TABLE score_snapshots (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    server_id           UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    run_id              UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,

    trust_score         SMALLINT NOT NULL CHECK (trust_score BETWEEN 0 AND 100),
    trust_label         TEXT NOT NULL,

    provenance          SMALLINT NOT NULL CHECK (provenance BETWEEN 0 AND 100),
    maintenance         SMALLINT NOT NULL CHECK (maintenance BETWEEN 0 AND 100),
    popularity          SMALLINT NOT NULL CHECK (popularity BETWEEN 0 AND 100),
    permissions         SMALLINT NOT NULL CHECK (permissions BETWEEN 0 AND 100),

    signals             JSONB NOT NULL DEFAULT '{}',
    flags               TEXT[] DEFAULT '{}',
    badges              JSONB NOT NULL DEFAULT '{}',

    verified_publisher  BOOLEAN DEFAULT FALSE,
    targets             TEXT[] DEFAULT '{}',

    scored_at           TIMESTAMPTZ DEFAULT now(),

    UNIQUE(server_id, run_id)
);

CREATE INDEX idx_snapshots_server ON score_snapshots(server_id);
CREATE INDEX idx_snapshots_run ON score_snapshots(run_id);
CREATE INDEX idx_snapshots_trust ON score_snapshots(trust_score DESC);
CREATE INDEX idx_snapshots_scored ON score_snapshots(scored_at DESC);
CREATE INDEX idx_snapshots_flags ON score_snapshots USING gin(flags);
CREATE INDEX idx_snapshots_targets ON score_snapshots USING gin(targets);

-- ============================================================
-- Materialized View: latest_scores
-- Most recent snapshot per server. Primary read path for API.
-- ============================================================
CREATE MATERIALIZED VIEW latest_scores AS
SELECT DISTINCT ON (ss.server_id)
    s.id AS server_uuid,
    s.name,
    s.namespace,
    s.server_id AS sid,
    s.title,
    s.description,
    ss.trust_score,
    ss.trust_label,
    ss.provenance,
    ss.maintenance,
    ss.popularity,
    ss.permissions,
    ss.signals,
    ss.flags,
    ss.badges,
    ss.verified_publisher,
    ss.targets,
    ss.scored_at,
    ss.run_id
FROM score_snapshots ss
JOIN servers s ON s.id = ss.server_id
ORDER BY ss.server_id, ss.scored_at DESC;

CREATE UNIQUE INDEX idx_latest_server_uuid ON latest_scores(server_uuid);
CREATE INDEX idx_latest_name ON latest_scores(name);
CREATE INDEX idx_latest_trust ON latest_scores(trust_score DESC);
CREATE INDEX idx_latest_namespace ON latest_scores(namespace);
CREATE INDEX idx_latest_flags ON latest_scores USING gin(flags);
CREATE INDEX idx_latest_targets ON latest_scores USING gin(targets);

-- ============================================================
-- Row-Level Security
-- Scores + server identity: public read
-- Registry entries + enrichments: service role only (private)
-- ============================================================

-- pipeline_runs: public read
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public can read pipeline runs"
    ON pipeline_runs FOR SELECT
    USING (true);
CREATE POLICY "Service role manages pipeline runs"
    ON pipeline_runs FOR ALL
    USING (auth.role() = 'service_role');

-- servers: public read
ALTER TABLE servers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public can read servers"
    ON servers FOR SELECT
    USING (true);
CREATE POLICY "Service role manages servers"
    ON servers FOR ALL
    USING (auth.role() = 'service_role');

-- registry_entries: service role only
ALTER TABLE registry_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only on registry entries"
    ON registry_entries FOR ALL
    USING (auth.role() = 'service_role');

-- github_enrichments: service role only
ALTER TABLE github_enrichments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only on enrichments"
    ON github_enrichments FOR ALL
    USING (auth.role() = 'service_role');

-- score_snapshots: public read
ALTER TABLE score_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public can read score snapshots"
    ON score_snapshots FOR SELECT
    USING (true);
CREATE POLICY "Service role manages score snapshots"
    ON score_snapshots FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================
-- Function: refresh_latest_scores
-- Callable via RPC to refresh the materialized view.
-- ============================================================
CREATE OR REPLACE FUNCTION refresh_latest_scores()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW latest_scores;
END;
$$;
