# MCP Scorecard

Trust scoring index for [MCP servers](https://modelcontextprotocol.io/). Like [OpenSSF Scorecard](https://securityscorecards.dev/) but for the MCP ecosystem.

The [MCP registry](https://registry.modelcontextprotocol.io/) has 2,000+ servers with zero trust signals — no download counts, no verification, no quality scoring. Agents are increasingly auto-selecting MCP servers and handing them credentials with no way to evaluate trustworthiness.

MCP Scorecard aggregates publicly available signals from the MCP registry and GitHub into a scored JSON index that MCP clients can consume.

## Scoring Model

**4 categories, each 0–100. Aggregate = weighted average.**

### Provenance (30%) — Is this real?
Has source repo, license, installable package, website, icon, namespace matches repo owner, SECURITY.md, code of conduct, unique description.

### Maintenance (25%) — Is it alive?
Repo age, last push recency, active commit weeks, contributor count, version history.

### Popularity (20%) — Does anyone use it?
GitHub stars, forks, watchers. (npm/PyPI download counts planned for v0.2.)

### Permissions (25%) — What does it want?
Secret env var count, transport type risk (stdio vs remote), credential sensitivity, package type.

### Score Bands
| Range | Label |
|-------|-------|
| 80–100 | High Trust |
| 60–79 | Moderate Trust |
| 40–59 | Low Trust |
| 20–39 | Very Low Trust |
| 0–19 | Unknown/Suspicious |

## Red Flags

Binary flags independent of score:

| Flag | Rule |
|------|------|
| `DEAD_ENTRY` | No packages and no remotes |
| `TEMPLATE_DESCRIPTION` | Matches known boilerplate |
| `STAGING_ARTIFACT` | Test/staging name pattern + template description |
| `HIGH_SECRET_DEMAND` | 5+ secret env vars |
| `SENSITIVE_CRED_REQUEST` | Requests wallet keys, DB passwords, etc. |
| `REPO_ARCHIVED` | GitHub repo archived |
| `NO_SOURCE` | No repo and no package source |
| `DESCRIPTION_DUPLICATE` | Same description used by 3+ unrelated servers |

## Output

The pipeline produces three JSON files:

- **`index.json`** — Per-server scores, signals, and flags
- **`stats.json`** — Ecosystem summary (score distribution, flag counts, top servers)
- **`flags.json`** — Servers grouped by flag type

```json
{
  "version": "0.1.0",
  "generated_at": "2026-02-22T06:00:00Z",
  "server_count": 2278,
  "servers": {
    "io.github.example/server": {
      "trust_score": 82,
      "trust_label": "High Trust",
      "scores": { "provenance": 90, "maintenance": 85, "popularity": 78, "permissions": 72 },
      "signals": { "has_source_repo": true, "github_stars": 1500, "..." : "..." },
      "flags": []
    }
  }
}
```

## Usage

```bash
git clone https://github.com/gigabrainobserver/mcp-scorecard.git
cd mcp-scorecard
pip install -e .
```

Run a full scan:

```bash
# Optional: set GITHUB_TOKEN for 5000 req/hr (vs 60 unauthenticated)
export GITHUB_TOKEN=ghp_...

python -m mcp_scorecard
```

Output goes to `./output/` by default. Use `-o` to specify a different directory.

## How it works

```
COLLECT (2min)     ENRICH (65min)      SCORE (10sec)     PUBLISH
MCP Registry  -->  GitHub API     -->  Calculator   -->  index.json
  ~2,300 servers   ~5,600 API calls    4 categories      stats.json
                   (5000/hr limit)     8 red flags       flags.json
```

Runs daily via GitHub Actions. ~70 min total runtime. All free APIs.

## Development

```bash
git clone https://github.com/gigabrainobserver/mcp-scorecard.git
cd mcp-scorecard
pip install -e .
pytest
```

## License

MIT
