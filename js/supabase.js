/**
 * MCP Scorecard — Supabase data client.
 * Fetches scored server data from the latest_scores materialized view
 * and transforms it into the format the site expects.
 */
const SUPABASE_URL = 'https://xvjkjlkohlmdwciyjcoc.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_A9V4liX4mxR2vkqTComCfg_ZfDIQMoF';

/**
 * Fetch all servers from Supabase and return in the same shape as index.json:
 *   { servers: { "namespace/name": { trust_score, scores: {...}, signals, flags, badges, ... } } }
 */
async function fetchServers() {
  const resp = await fetch(
    `${SUPABASE_URL}/rest/v1/latest_scores?select=*`,
    { headers: { 'apikey': SUPABASE_ANON_KEY } }
  );
  if (!resp.ok) throw new Error(`Supabase fetch failed: ${resp.status}`);
  const rows = await resp.json();

  const servers = {};
  for (const row of rows) {
    servers[row.name] = {
      trust_score: row.trust_score,
      trust_label: row.trust_label,
      scores: {
        provenance: row.provenance,
        maintenance: row.maintenance,
        popularity: row.popularity,
        permissions: row.permissions,
      },
      signals: row.signals || {},
      flags: row.flags || [],
      badges: row.badges || {},
      verified_publisher: row.verified_publisher || false,
      targets: row.targets || [],
    };
  }
  return { servers, server_count: rows.length };
}
