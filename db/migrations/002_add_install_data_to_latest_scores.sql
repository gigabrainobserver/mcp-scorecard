-- Migration: Add install data to latest_scores materialized view
-- Run in Supabase SQL Editor. Brief downtime (~seconds) while view rebuilds.

DROP MATERIALIZED VIEW latest_scores;

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
    ss.run_id,
    -- Install data from registry
    re.repo_url,
    re.version,
    re.package_types,
    re.package_identifiers,
    re.transport_types,
    re.env_vars
FROM score_snapshots ss
JOIN servers s ON s.id = ss.server_id
LEFT JOIN registry_entries re ON re.server_id = s.id
ORDER BY ss.server_id, ss.scored_at DESC;

-- Recreate indexes
CREATE UNIQUE INDEX idx_latest_server_uuid ON latest_scores(server_uuid);
CREATE INDEX idx_latest_name ON latest_scores(name);
CREATE INDEX idx_latest_trust ON latest_scores(trust_score DESC);
CREATE INDEX idx_latest_namespace ON latest_scores(namespace);
CREATE INDEX idx_latest_flags ON latest_scores USING gin(flags);
CREATE INDEX idx_latest_targets ON latest_scores USING gin(targets);

-- Populate
REFRESH MATERIALIZED VIEW latest_scores;
