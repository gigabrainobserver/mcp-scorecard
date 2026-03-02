-- MCP Scorecard — API Key Signup Analytics
-- Run this in Supabase SQL Editor after api_keys.sql.

-- ============================================================
-- Table: api_key_signups
-- Tracks provisioning events for analytics.
-- ============================================================
CREATE TABLE api_key_signups (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email       TEXT NOT NULL,
    use_case    TEXT,
    country     TEXT,              -- from CF-IPCountry header
    ip_hash     TEXT,              -- SHA-256 of IP, not raw IP
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_signups_email ON api_key_signups(email);
CREATE INDEX idx_signups_created ON api_key_signups(created_at);

-- ============================================================
-- Row-Level Security
-- Service role only — Worker uses service key to insert.
-- ============================================================
ALTER TABLE api_key_signups ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role manages signups"
    ON api_key_signups FOR ALL
    USING (auth.role() = 'service_role');
