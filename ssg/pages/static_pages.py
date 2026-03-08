"""Generate static content pages: about, api, privacy, 404."""
from pathlib import Path

from ssg.templates import base_page, breadcrumb_nav
from ssg.seo import organization_jsonld, breadcrumb_jsonld


# ── About page ──────────────────────────────────────────────

ABOUT_CSS = """
  .container { max-width: 860px; margin: 0 auto; padding: 0 24px; }
  .hero { padding: 80px 0 48px; text-align: center; }
  .hero h1 { font-size: 40px; font-weight: 700; margin-bottom: 16px; }
  .hero h1 span { color: #58a6ff; }
  .hero .tagline { font-size: 20px; color: #7d8590; max-width: 600px; margin: 0 auto 12px; }
  .hero .sub { font-size: 15px; color: #484f58; max-width: 500px; margin: 0 auto 36px; }
  .hero .cta { display: inline-flex; gap: 12px; flex-wrap: wrap; justify-content: center; }
  .btn { padding: 10px 24px; border-radius: 8px; font-size: 15px; font-weight: 600; display: inline-block; }
  .btn-primary { background: #58a6ff; color: #0d1117; }
  .btn-primary:hover { background: #79b8ff; text-decoration: none; }
  .btn-secondary { background: #21262d; color: #e6edf3; border: 1px solid #30363d; }
  .btn-secondary:hover { background: #30363d; text-decoration: none; }
  .scale-banner { border-top: 1px solid #21262d; border-bottom: 1px solid #21262d; padding: 28px 0; margin-bottom: 56px; }
  .scale-row { display: flex; justify-content: center; gap: 48px; flex-wrap: wrap; }
  .scale-item { text-align: center; }
  .scale-item .num { font-size: 32px; font-weight: 700; color: #58a6ff; }
  .scale-item .label { font-size: 12px; color: #7d8590; text-transform: uppercase; letter-spacing: 0.5px; }
  section { margin-bottom: 56px; }
  section h2 { font-size: 24px; font-weight: 600; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #21262d; }
  section h3 { font-size: 16px; font-weight: 600; margin: 20px 0 8px; }
  section p { color: #b1bac4; margin-bottom: 14px; font-size: 15px; }
  section p strong { color: #e6edf3; }
  .manifesto { background: #161b22; border: 1px solid #21262d; border-radius: 12px; padding: 32px; margin: 32px 0; text-align: center; }
  .manifesto p { font-size: 20px; color: #e6edf3; font-weight: 600; line-height: 1.5; margin: 0; }
  .manifesto p span { color: #58a6ff; }
  .principles { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 20px 0; }
  .principle { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 20px; }
  .principle h4 { font-size: 15px; font-weight: 600; margin-bottom: 6px; color: #e6edf3; }
  .principle p { font-size: 13px; color: #7d8590; margin: 0; }
  blockquote { border-left: 3px solid #58a6ff; padding: 12px 20px; margin: 20px 0; background: rgba(88,166,255,0.04); border-radius: 0 8px 8px 0; }
  blockquote p { color: #b1bac4; margin: 0; font-style: italic; font-size: 15px; }
  .timeline { margin: 20px 0; }
  .timeline-item { display: flex; gap: 16px; margin-bottom: 20px; }
  .timeline-dot { width: 12px; height: 12px; border-radius: 50%; background: #58a6ff; margin-top: 6px; flex-shrink: 0; }
  .timeline-content h4 { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
  .timeline-content p { font-size: 13px; color: #7d8590; margin: 0; }
  .section-divider { border: none; border-top: 2px solid #21262d; margin: 64px 0; }
  .cat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin: 20px 0; }
  .cat-card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px; }
  .cat-card .weight { font-size: 12px; color: #7d8590; margin-bottom: 4px; }
  .cat-card .cat-name { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
  .cat-card .cat-q { font-size: 13px; color: #7d8590; font-style: italic; }
  .cat-prov .cat-name { color: #3fb950; }
  .cat-maint .cat-name { color: #58a6ff; }
  .cat-pop .cat-name { color: #d29922; }
  .cat-perm .cat-name { color: #f0883e; }
  .bands { display: flex; gap: 2px; margin: 16px 0; border-radius: 6px; overflow: hidden; }
  .band { padding: 10px; text-align: center; flex: 1; }
  .band .range { font-size: 14px; font-weight: 700; }
  .band .blabel { font-size: 11px; }
  .band-high { background: rgba(63,185,80,0.15); color: #3fb950; }
  .band-mod { background: rgba(88,166,255,0.15); color: #58a6ff; }
  .band-low { background: rgba(210,153,34,0.15); color: #d29922; }
  .band-vlow { background: rgba(248,81,73,0.15); color: #f85149; }
  .band-unk { background: rgba(110,118,129,0.15); color: #6e7681; }
  .flags-table { width: 100%; border-collapse: collapse; margin: 16px 0; }
  .flags-table th, .flags-table td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #21262d; }
  .flags-table th { font-size: 12px; color: #7d8590; text-transform: uppercase; font-weight: 600; }
  .flags-table td { font-size: 14px; }
  .flags-table .flag-name { font-weight: 600; color: #f85149; font-family: monospace; font-size: 13px; }
  .flags-table .flag-count { color: #7d8590; font-size: 13px; }
  .endpoint { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px; margin: 12px 0; font-family: monospace; }
  .endpoint .method { color: #3fb950; font-weight: 700; }
  .endpoint .url { color: #e6edf3; font-size: 14px; word-break: break-all; }
  .endpoint .desc { color: #7d8590; font-size: 13px; margin-top: 4px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; }
"""


def _about_body(server_count: int, publisher_count: int, total_flags: int, flag_counts: dict) -> str:
    """Build the about page body HTML."""
    # Flag table rows
    flag_defs = [
        ("DEAD_ENTRY", "No packages and no remotes — server can't be installed or reached"),
        ("TEMPLATE_DESCRIPTION", "Description matches common boilerplate (\"A model context protocol server\")"),
        ("STAGING_ARTIFACT", "Name contains test/staging patterns combined with a template description"),
        ("HIGH_SECRET_DEMAND", "Requests 5 or more secret environment variables"),
        ("SENSITIVE_CRED_REQUEST", "Requests wallet keys, database passwords, or other high-risk credentials"),
        ("REPO_ARCHIVED", "GitHub repository is archived by its maintainer"),
        ("NO_SOURCE", "No repository URL and no verifiable package source"),
        ("DESCRIPTION_DUPLICATE", "Same description used by 3+ servers from different publishers"),
    ]
    flag_rows = ""
    for fname, fdesc in flag_defs:
        count = flag_counts.get(fname, 0)
        flag_rows += f'<tr><td class="flag-name">{fname}</td><td>{fdesc}</td><td class="flag-count">{count}</td></tr>'

    return f"""<div class="container">
  <div class="hero">
    <h1>Trust Signals for <span>Every</span> MCP Server</h1>
    <p class="tagline">The MCP ecosystem has no rules. We think you deserve to know what you're installing.</p>
    <p class="sub">Open source. Non-profit. Forever free.</p>
    <div class="cta">
      <a href="/" class="btn btn-primary">Browse the Scorecard</a>
      <a href="/publishers/" class="btn btn-secondary">Publishers</a>
      <a href="https://github.com/gigabrainobserver/mcp-scorecard" class="btn btn-secondary">View Source</a>
    </div>
  </div>

  <div class="scale-banner">
    <div class="scale-row">
      <div class="scale-item"><div class="num">{server_count:,}</div><div class="label">Servers Scored</div></div>
      <div class="scale-item"><div class="num">{publisher_count:,}</div><div class="label">Publishers</div></div>
      <div class="scale-item"><div class="num">{total_flags:,}</div><div class="label">Flags Raised</div></div>
      <div class="scale-item"><div class="num">$0</div><div class="label">Cost to Use</div></div>
    </div>
  </div>

  <section>
    <h2>The Problem</h2>
    <p>AI agents are gaining the ability to install and use software on your behalf. The Model Context Protocol (MCP) is becoming the standard way they do it — connecting to servers that access your files, your databases, your credentials, your cloud accounts.</p>
    <p>The MCP registry now lists thousands of servers. <strong>There is no review process.</strong> No verification. No download counts. No trust signals of any kind. Anyone can publish a server that requests your AWS keys, your database password, or your wallet credentials — and nothing in the ecosystem will warn you.</p>
    <p>Agents are increasingly auto-selecting MCP servers and handing them credentials with no way to evaluate whether that server is maintained, legitimate, or safe. The registry is a flat list with no quality signal.</p>
    <p><strong>This is the wild west, and the land rush is on.</strong></p>
  </section>

  <div class="manifesto">
    <p>You decide which servers to trust.<br>We make sure you have <span>the data to decide</span>.</p>
  </div>

  <section>
    <h2>What We Do</h2>
    <p>MCP Scorecard scores every server in the MCP registry using publicly available data. We check the source code, the GitHub repo, the package metadata, the credentials it requests, and the people behind it. We publish everything as open data — free for humans and machines alike.</p>
    <p>We don't curate. We don't block. We don't sell rankings. We surface facts and let you draw your own conclusions.</p>
    <p>Every signal, every weight, every threshold is in the <a href="https://github.com/gigabrainobserver/mcp-scorecard">open source code</a>. If you disagree with how we score something, you can see exactly why — and you can fork it.</p>
  </section>

  <section>
    <h2>Our Commitments</h2>
    <div class="principles">
      <div class="principle"><h4>Open Source</h4><p>The entire scoring pipeline — collection, enrichment, scoring, publishing — is open source under MIT. Audit it, fork it, improve it.</p></div>
      <div class="principle"><h4>No Ads, No Tracking</h4><p>No analytics. No cookies. No fingerprinting. The site is static HTML served from GitHub Pages. We don't know who you are and we don't want to.</p></div>
      <div class="principle"><h4>Facts, Not Opinions</h4><p>Flags are observable data from public sources. We don't maintain blocklists. We don't do manual reviews. We don't accept payment to change a score.</p></div>
      <div class="principle"><h4>Machine-Readable</h4><p>Every score is available as static JSON. MCP clients and AI agents can check trust signals programmatically before granting access.</p></div>
      <div class="principle"><h4>Independent</h4><p>Not affiliated with any MCP server vendor, registry, or marketplace. No commercial interest in any ranking. We exist to inform, not to sell.</p></div>
    </div>
  </section>

  <section>
    <h2>Why This Matters Now</h2>
    <p>We're at an inflection point. AI agents are moving from "suggest code" to "execute code." From "draft an email" to "manage your infrastructure." MCP is the protocol that makes this possible — and the trust infrastructure hasn't caught up.</p>
    <p>Right now, an agent can select an MCP server from the registry, request your database credentials, and execute operations on your behalf. The only thing standing between your data and an unmaintained, unverified server is... nothing. There is no gate.</p>
    <blockquote><p>The time to build trust infrastructure is before the first major incident, not after.</p></blockquote>
    <p>We're not trying to slow down the MCP ecosystem. We're trying to make sure it grows with visibility. Every server deserves a chance to prove itself — and every user deserves the information to make that call.</p>
  </section>

  <section>
    <h2>Get Involved</h2>
    <div class="timeline">
      <div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-content"><h4>Use the data</h4><p>Check servers before installing them. Share the scorecard with your team. Build tools on top of our JSON output.</p></div></div>
      <div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-content"><h4>Improve the scoring</h4><p>Found a false positive? Think a signal is weighted wrong? Open an issue or submit a PR. The methodology is meant to evolve.</p></div></div>
      <div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-content"><h4>Spread the word</h4><p>The scorecard only works if people know it exists. Blog about it, tweet it, drop it in your team Slack. Every person informed is one fewer caught off guard.</p></div></div>
      <div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-content"><h4>Build trust infrastructure</h4><p>We're one project. The ecosystem needs more — package signing, server attestation, runtime sandboxing. If you're building in this space, let's talk.</p></div></div>
    </div>
  </section>

  <hr class="section-divider">

  <section>
    <h2>Scoring Model</h2>
    <p>Every server is scored 0–100 across four categories. The aggregate trust score is a weighted average.</p>
    <div class="cat-grid">
      <div class="cat-card cat-prov"><div class="weight">30% weight</div><div class="cat-name">Provenance</div><div class="cat-q">Is this real?</div></div>
      <div class="cat-card cat-maint"><div class="weight">25% weight</div><div class="cat-name">Maintenance</div><div class="cat-q">Is it alive?</div></div>
      <div class="cat-card cat-pop"><div class="weight">20% weight</div><div class="cat-name">Popularity</div><div class="cat-q">Does anyone use it?</div></div>
      <div class="cat-card cat-perm"><div class="weight">25% weight</div><div class="cat-name">Permissions</div><div class="cat-q">What does it want?</div></div>
    </div>
    <h3>Provenance — Is this real?</h3>
    <p>Has a source repo, license, installable package, website, icon, matching namespace, SECURITY.md, code of conduct, and a unique (non-boilerplate) description.</p>
    <h3>Maintenance — Is it alive?</h3>
    <p>Repo age, how recently it was pushed, active commit weeks in the past year, contributor count, and release activity.</p>
    <h3>Popularity — Does anyone use it?</h3>
    <p>GitHub stars, forks, and watchers on a logarithmic scale. npm/PyPI download counts planned for a future version.</p>
    <h3>Permissions — What does it want?</h3>
    <p>How many secrets it requests, transport type risk (local stdio vs remote), credential sensitivity (API key vs database password vs wallet key), and package type.</p>
  </section>

  <section>
    <h2>Score Bands</h2>
    <div class="bands">
      <a href="/risk/high-trust/" style="text-decoration:none" class="band band-high"><div class="range">80–100</div><div class="blabel">High Trust</div></a>
      <a href="/risk/moderate/" style="text-decoration:none" class="band band-mod"><div class="range">60–79</div><div class="blabel">Moderate</div></a>
      <a href="/risk/low-trust/" style="text-decoration:none" class="band band-low"><div class="range">40–59</div><div class="blabel">Low Trust</div></a>
      <a href="/risk/very-low/" style="text-decoration:none" class="band band-vlow"><div class="range">20–39</div><div class="blabel">Very Low</div></a>
      <a href="/risk/suspicious/" style="text-decoration:none" class="band band-unk"><div class="range">0–19</div><div class="blabel">Suspicious</div></a>
    </div>
  </section>

  <section>
    <h2>Red Flags</h2>
    <p>Binary flags that indicate structural or behavioral anomalies, independent of the numeric score. These are observable facts, not opinions.</p>
    <table class="flags-table">
      <thead><tr><th>Flag</th><th>What it observes</th><th>Count</th></tr></thead>
      <tbody>{flag_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>How It Works</h2>
    <p>The pipeline runs on-demand. Four stages, all free public APIs.</p>
    <div class="endpoint" style="font-size:13px; line-height:1.8;">
      <span style="color:#3fb950;">COLLECT</span> Registry API &rarr; {server_count:,}+ servers<br>
      <span style="color:#58a6ff;">ENRICH</span>&nbsp; GitHub API &rarr; repo metadata, community profile, commit activity<br>
      <span style="color:#d29922;">SCORE</span>&nbsp;&nbsp; 4 categories &times; every server + red flag detection<br>
      <span style="color:#f0883e;">PUBLISH</span> Supabase Postgres &rarr; scored data served via REST API
    </div>
  </section>

</div>"""


# ── API page ────────────────────────────────────────────────

API_CSS = """
  .container { max-width: 860px; margin: 0 auto; padding: 0 24px; }
  .hero { padding: 80px 0 24px; text-align: center; }
  .hero h1 { font-size: 40px; font-weight: 700; margin-bottom: 16px; }
  .hero h1 span { color: #58a6ff; }
  .hero .tagline { font-size: 20px; color: #7d8590; max-width: 600px; margin: 0 auto 12px; }
  .hero .sub { font-size: 15px; color: #484f58; max-width: 500px; margin: 0 auto; }
  section { margin-bottom: 56px; }
  section h2 { font-size: 24px; font-weight: 600; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #21262d; }
  section h3 { font-size: 16px; font-weight: 600; margin: 20px 0 8px; }
  section p { color: #b1bac4; margin-bottom: 14px; font-size: 15px; }
  section p strong { color: #e6edf3; }
  .endpoint { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px; margin: 12px 0; font-family: monospace; }
  .endpoint .method { color: #3fb950; font-weight: 700; }
  .endpoint .url { color: #e6edf3; font-size: 14px; word-break: break-all; }
  .endpoint .desc { color: #7d8590; font-size: 13px; margin-top: 4px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; }
  .code-block { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 16px; font-family: monospace; font-size: 13px; color: #e6edf3; overflow-x: auto; margin: 12px 0; line-height: 1.6; white-space: pre; }
  .code-block .cm { color: #484f58; }
  .code-block .str { color: #a5d6ff; }
  .code-block .key { color: #7ee787; }
  .code-block .num { color: #f0883e; }
  .param-table { width: 100%; border-collapse: collapse; margin: 12px 0 20px; }
  .param-table th, .param-table td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #21262d; }
  .param-table th { font-size: 12px; color: #7d8590; text-transform: uppercase; font-weight: 600; }
  .param-table td { font-size: 14px; }
  .param-table .param-name { font-weight: 600; color: #e6edf3; font-family: monospace; font-size: 13px; }
  .param-table .param-type { color: #7d8590; font-family: monospace; font-size: 12px; }
  .param-table .param-desc { color: #b1bac4; font-size: 13px; }
  .tier-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin: 20px 0; }
  .tier-card { background: #161b22; border: 1px solid #21262d; border-radius: 12px; padding: 28px; display: flex; flex-direction: column; }
  .tier-card.pro { border-color: #58a6ff; }
  .tier-label { display: inline-block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; padding: 3px 8px; border-radius: 4px; margin-bottom: 12px; width: fit-content; }
  .tier-label.free { background: rgba(63,185,80,0.15); color: #3fb950; }
  .tier-label.pro { background: rgba(88,166,255,0.15); color: #58a6ff; }
  .tier-card h4 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
  .tier-card .tier-price { font-size: 14px; color: #7d8590; margin-bottom: 16px; }
  .tier-card ul { list-style: none; padding: 0; margin: 0; flex: 1; }
  .tier-card ul li { font-size: 14px; color: #b1bac4; padding: 6px 0; border-bottom: 1px solid #21262d; }
  .tier-card ul li:last-child { border-bottom: none; }
  .tier-card ul li::before { content: "\\2713  "; color: #3fb950; font-weight: 700; }
  .tier-card .tier-cta { margin-top: 20px; text-align: center; }
  .tier-card .tier-cta .btn { width: 100%; text-align: center; }
  .btn { padding: 10px 24px; border-radius: 8px; font-size: 15px; font-weight: 600; display: inline-block; }
  .btn-primary { background: #58a6ff; color: #0d1117; }
  .btn-primary:hover { background: #79b8ff; text-decoration: none; }
  .btn-secondary { background: #21262d; color: #e6edf3; border: 1px solid #30363d; }
  .btn-secondary:hover { background: #30363d; text-decoration: none; }
  .key-form { margin-top: 16px; }
  .key-form input, .key-form select { width: 100%; padding: 8px 12px; border: 1px solid #30363d; border-radius: 6px; background: #0d1117; color: #e6edf3; font-size: 14px; margin-bottom: 8px; }
  .key-form input::placeholder { color: #484f58; }
  .key-form select { appearance: none; cursor: pointer; }
  .key-form .form-error { color: #f85149; font-size: 13px; margin-bottom: 8px; display: none; }
  .key-result { background: #0d1117; border: 1px solid #3fb950; border-radius: 8px; padding: 16px; margin-top: 16px; }
  .key-result .key-value { font-family: monospace; font-size: 14px; color: #3fb950; word-break: break-all; user-select: all; padding: 8px; background: #161b22; border-radius: 4px; margin: 8px 0; }
  .key-result .key-warning { font-size: 12px; color: #d29922; }
  .use-cases { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 20px 0; }
  .use-case { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 20px; }
  .use-case h4 { font-size: 15px; font-weight: 600; margin-bottom: 6px; color: #e6edf3; }
  .use-case p { font-size: 13px; color: #7d8590; margin: 0; }
  @media (max-width: 640px) { .tier-grid { grid-template-columns: 1fr; } }
"""

API_BODY = """<div class="container">

  <div class="hero">
    <h1>Trust Data, <span>The Full Picture</span></h1>
    <p class="tagline">Integrate MCP trust scores into your tools, agents, and workflows.</p>
    <p class="sub">Free tier included. No credit card required.</p>
  </div>

  <section id="tiers">
    <h2>Get Access</h2>
    <div class="tier-grid">
      <div class="tier-card">
        <span class="tier-label free">Free</span>
        <h4>100 requests / day</h4>
        <div class="tier-price">$0 forever</div>
        <ul>
          <li>All endpoints</li>
          <li>Rate limit headers included</li>
          <li>Personal projects &amp; evaluation</li>
        </ul>
        <div class="tier-cta" id="free-key-cta">
          <div class="key-form" id="key-form">
            <input type="email" id="key-email" placeholder="you@example.com" required>
            <select id="key-use-case">
              <option value="">How will you use the API?</option>
              <option value="mcp_client">MCP client integration</option>
              <option value="cicd">CI/CD pipeline</option>
              <option value="security">Security dashboard</option>
              <option value="ai_agent">AI agent</option>
              <option value="research">Research / exploration</option>
              <option value="other">Other</option>
            </select>
            <div class="form-error" id="form-error"></div>
            <button class="btn btn-secondary" style="width:100%" id="submit-key" onclick="provisionKey()">Get Free Key</button>
          </div>
          <div class="key-result" id="key-result" style="display:none">
            <div style="font-size:13px;color:#b1bac4;margin-bottom:4px;">Your API key:</div>
            <div class="key-value" id="key-value"></div>
            <div class="key-warning">Save this now — it cannot be retrieved again.</div>
          </div>
        </div>
      </div>
      <div class="tier-card pro">
        <span class="tier-label pro">Pro</span>
        <h4>10,000 requests / day</h4>
        <div class="tier-price">Coming soon</div>
        <ul>
          <li>All endpoints</li>
          <li>Rate limit headers included</li>
          <li>Personal projects &amp; evaluation</li>
          <li>Production integrations &amp; SaaS</li>
          <li>Bulk server lookups</li>
          <li>Score change notifications</li>
          <li>Priority support</li>
        </ul>
        <div class="tier-cta">
          <span class="btn btn-primary" style="opacity:0.5;cursor:default;">Coming Soon</span>
        </div>
      </div>
    </div>
  </section>

  <section>
    <h2>Quick Start</h2>
    <h3>REST API</h3>
    <p>Base URL for all API requests:</p>
    <div class="code-block">https://api.mcp-scorecard.ai/v1</div>
    <p>Example request:</p>
    <div class="code-block">curl -H <span class="str">"X-API-Key: your_key"</span> \\
  https://api.mcp-scorecard.ai/v1/stats</div>
    <h3>MCP Server</h3>
    <p>Give your AI agent direct access to trust scores. The <strong>mcp-scorecard-server</strong> package wraps this API as an MCP tool — no HTTP calls needed in your code.</p>
    <p>Add to your Claude Code config (<strong>.mcp.json</strong>):</p>
    <div class="code-block">{
  <span class="key">"mcpServers"</span>: {
    <span class="key">"mcp-scorecard"</span>: {
      <span class="key">"command"</span>: <span class="str">"uvx"</span>,
      <span class="key">"args"</span>: [<span class="str">"mcp-scorecard-server"</span>],
      <span class="key">"env"</span>: {
        <span class="key">"SCORECARD_API_KEY"</span>: <span class="str">"your_key"</span>
      }
    }
  }
}</div>
    <p>Available tools:</p>
    <table class="param-table">
      <thead><tr><th>Tool</th><th>Description</th></tr></thead>
      <tbody>
        <tr><td class="param-name">check_server_trust</td><td class="param-desc">Look up trust score, flags, and install info for a specific server</td></tr>
        <tr><td class="param-name">search_servers</td><td class="param-desc">Search servers by keyword (min 2 chars)</td></tr>
        <tr><td class="param-name">list_servers</td><td class="param-desc">Browse and filter servers by score, flags, platform, or namespace</td></tr>
        <tr><td class="param-name">get_ecosystem_stats</td><td class="param-desc">Aggregate stats — total servers, score distribution, flag summary</td></tr>
      </tbody>
    </table>
    <p>Works with any MCP-compatible client — Claude Code, Cursor, Windsurf, or your own agent.</p>
  </section>

  <section>
    <h2>Authentication</h2>
    <p>All endpoints except <strong>/v1/health</strong> require an API key passed via the <strong>X-API-Key</strong> header.</p>
    <div class="code-block"><span class="cm"># Authenticated request</span>
curl -H <span class="str">"X-API-Key: sk_your_key_here"</span> \\
  https://api.mcp-scorecard.ai/v1/servers

<span class="cm"># Health check (no auth needed)</span>
curl https://api.mcp-scorecard.ai/v1/health</div>
    <p>Invalid or missing keys return <strong>401 Unauthorized</strong>.</p>
  </section>

  <section>
    <h2>Endpoints</h2>
    <h3>Health Check</h3>
    <div class="endpoint"><span class="method">GET</span> <span class="url">/v1/health</span><div class="desc">Service status. No authentication required.</div></div>
    <div class="code-block">{ <span class="key">"data"</span>: { <span class="key">"status"</span>: <span class="str">"ok"</span> }, <span class="key">"meta"</span>: { <span class="key">"cached"</span>: false } }</div>

    <h3>Ecosystem Statistics</h3>
    <div class="endpoint"><span class="method">GET</span> <span class="url">/v1/stats</span><div class="desc">Aggregate statistics across all scored servers.</div></div>

    <h3>List Servers</h3>
    <div class="endpoint"><span class="method">GET</span> <span class="url">/v1/servers</span><div class="desc">List and filter servers. Paginated.</div></div>
    <table class="param-table">
      <thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
      <tbody>
        <tr><td class="param-name">limit</td><td class="param-type">int</td><td class="param-desc">Results per page. 1–200, default 50.</td></tr>
        <tr><td class="param-name">offset</td><td class="param-type">int</td><td class="param-desc">Pagination offset. Default 0.</td></tr>
        <tr><td class="param-name">sort</td><td class="param-type">string</td><td class="param-desc">Sort field: trust_score, name, namespace, provenance, maintenance, popularity, permissions, scored_at.</td></tr>
        <tr><td class="param-name">order</td><td class="param-type">string</td><td class="param-desc">Sort direction: asc or desc. Default desc.</td></tr>
        <tr><td class="param-name">min_score</td><td class="param-type">int</td><td class="param-desc">Filter by minimum trust score.</td></tr>
        <tr><td class="param-name">flags</td><td class="param-type">string</td><td class="param-desc">Filter by flag name, e.g. SENSITIVE_CRED_REQUEST.</td></tr>
        <tr><td class="param-name">target</td><td class="param-type">string</td><td class="param-desc">Filter by platform target, e.g. PostgreSQL.</td></tr>
        <tr><td class="param-name">namespace</td><td class="param-type">string</td><td class="param-desc">Filter by publisher namespace.</td></tr>
      </tbody>
    </table>

    <h3>Get Server</h3>
    <div class="endpoint"><span class="method">GET</span> <span class="url">/v1/servers/:namespace/:id</span><div class="desc">Detailed trust data for a single server.</div></div>

    <h3>Search</h3>
    <div class="endpoint"><span class="method">GET</span> <span class="url">/v1/search?q=</span><div class="desc">Search servers by name. Minimum 2 characters.</div></div>
    <table class="param-table">
      <thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
      <tbody>
        <tr><td class="param-name">q</td><td class="param-type">string</td><td class="param-desc">Search query. Required, min 2 characters.</td></tr>
        <tr><td class="param-name">limit</td><td class="param-type">int</td><td class="param-desc">Max results. 1–200, default 20.</td></tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>Rate Limits</h2>
    <p>Rate limits reset daily at midnight UTC. Every response includes headers to track your usage:</p>
    <div class="code-block"><span class="key">X-RateLimit-Limit</span>: 100        <span class="cm"># Your daily limit</span>
<span class="key">X-RateLimit-Remaining</span>: 87   <span class="cm"># Requests left today</span>
<span class="key">X-RateLimit-Reset</span>: 1709424000 <span class="cm"># UTC midnight epoch</span></div>
    <p>When you exceed your limit, the API returns <strong>429 Too Many Requests</strong> with a <strong>Retry-After</strong> header.</p>
  </section>

  <section>
    <h2>Response Format</h2>
    <p>All responses use a standard envelope:</p>
    <div class="code-block">{
  <span class="key">"data"</span>: { ... },     <span class="cm"># The response payload</span>
  <span class="key">"meta"</span>: {             <span class="cm"># Request metadata</span>
    <span class="key">"cached"</span>: true,
    <span class="key">"total"</span>: <span class="num">2889</span>,
    <span class="key">"limit"</span>: <span class="num">50</span>,
    <span class="key">"offset"</span>: <span class="num">0</span>
  }
}</div>
    <p>Responses may be cached for up to <strong>1 hour</strong>. CORS is enabled for all origins.</p>
  </section>

  <section>
    <h2>Errors</h2>
    <table class="param-table">
      <thead><tr><th>Status</th><th>Meaning</th></tr></thead>
      <tbody>
        <tr><td class="param-name">400</td><td class="param-desc">Bad request — missing or invalid parameters</td></tr>
        <tr><td class="param-name">401</td><td class="param-desc">Unauthorized — missing or invalid API key</td></tr>
        <tr><td class="param-name">404</td><td class="param-desc">Not found — server or route doesn't exist</td></tr>
        <tr><td class="param-name">429</td><td class="param-desc">Rate limit exceeded — wait for reset</td></tr>
        <tr><td class="param-name">502</td><td class="param-desc">Upstream error — Supabase is unreachable</td></tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>Use Cases</h2>
    <div class="use-cases">
      <div class="use-case"><h4>MCP Clients</h4><p>Check trust scores before granting a server access to credentials.</p></div>
      <div class="use-case"><h4>CI/CD Pipelines</h4><p>Gate MCP server additions on minimum trust thresholds.</p></div>
      <div class="use-case"><h4>Security Dashboards</h4><p>Monitor trust signals across your fleet of MCP servers.</p></div>
      <div class="use-case"><h4>AI Agents</h4><p>Evaluate server trust programmatically before tool selection.</p></div>
    </div>
  </section>

</div>"""

API_KEY_JS = """
async function provisionKey() {
  var btn = document.getElementById('submit-key');
  var errEl = document.getElementById('form-error');
  var email = document.getElementById('key-email').value.trim();
  var useCase = document.getElementById('key-use-case').value;
  errEl.style.display = 'none';
  errEl.textContent = '';
  if (!email || !/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email)) {
    errEl.textContent = 'Please enter a valid email address.';
    errEl.style.display = 'block';
    return;
  }
  btn.disabled = true;
  btn.textContent = 'Generating...';
  try {
    var res = await fetch('https://api.mcp-scorecard.ai/v1/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, use_case: useCase }),
    });
    var data = await res.json();
    if (!res.ok) {
      errEl.textContent = (data.error && data.error.message) || 'Something went wrong.';
      errEl.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Get Free Key';
      return;
    }
    document.getElementById('key-form').style.display = 'none';
    document.getElementById('key-result').style.display = 'block';
    document.getElementById('key-value').textContent = data.data.api_key;
  } catch (e) {
    errEl.textContent = 'Network error. Please try again.';
    errEl.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Get Free Key';
  }
}
"""


# ── Privacy page ────────────────────────────────────────────

PRIVACY_CSS = """
  .container { max-width: 720px; margin: 0 auto; padding: 48px 24px; }
  h2 { font-size: 28px; font-weight: 700; margin-bottom: 24px; }
  h3 { font-size: 18px; font-weight: 600; margin: 28px 0 8px; color: #e6edf3; }
  p { color: #b1bac4; margin-bottom: 14px; font-size: 15px; }
  p strong { color: #e6edf3; }
  ul { margin: 0 0 14px 24px; color: #b1bac4; font-size: 15px; }
  li { margin-bottom: 6px; }
  .updated { font-size: 13px; color: #484f58; margin-top: 32px; }
"""

PRIVACY_BODY = """<div class="container">
  <h2>Privacy Policy</h2>
  <p><strong>The short version:</strong> We don't collect anything. No data. No cookies. No tracking. Nothing.</p>
  <h3>What we collect</h3>
  <p>Nothing. This site is static HTML served from GitHub Pages. We have no server-side code, no database, no analytics, and no way to identify you.</p>
  <h3>Cookies</h3>
  <p>This site sets <strong>zero cookies</strong>. No session cookies, no tracking cookies, no third-party cookies. None.</p>
  <h3>Analytics and tracking</h3>
  <p>We use <strong>no analytics services</strong>. No Google Analytics, no Plausible, no Fathom, no tracking pixels, no fingerprinting. We don't know how many people visit this site, and we don't want to know.</p>
  <h3>Third-party requests</h3>
  <p>This site makes <strong>no requests to third-party services</strong>. All assets (HTML, CSS, JSON data) are served from the same domain. No CDNs, no external fonts, no social media widgets.</p>
  <h3>Data we publish</h3>
  <p>MCP Scorecard publishes trust scores derived entirely from <strong>publicly available data</strong>:</p>
  <ul>
    <li>Public MCP registry listings</li>
    <li>Public GitHub repository metadata (stars, forks, license, commit history)</li>
    <li>Public package registry metadata</li>
  </ul>
  <p>We do not collect, store, or publish any private or personal data about server authors or users.</p>
  <h3>GitHub Pages</h3>
  <p>This site is hosted on <a href="https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages">GitHub Pages</a>. GitHub may collect basic server logs (IP addresses) as part of standard web hosting. This is governed by <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">GitHub's Privacy Statement</a>, not by us. We have no access to these logs.</p>
  <h3>Contact</h3>
  <p>Questions about this policy? <a href="https://github.com/gigabrainobserver/mcp-scorecard/issues">Open an issue</a> on GitHub.</p>
  <p class="updated">Last updated: February 2026</p>
</div>"""


# ── 404 page ────────────────────────────────────────────────

FOUR_OH_FOUR_CSS = """
  .container { max-width: 600px; margin: 0 auto; padding: 80px 24px; text-align: center; }
  .container h2 { font-size: 48px; font-weight: 700; color: #484f58; margin-bottom: 16px; }
  .container p { font-size: 16px; color: #7d8590; margin-bottom: 24px; }
  .container .links { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }
  .container .links a { padding: 8px 20px; border-radius: 6px; background: #21262d; color: #e6edf3; font-weight: 600; font-size: 14px; }
  .container .links a:hover { background: #30363d; text-decoration: none; }
"""

REDIRECT_JS = """
(function() {
  var loc = window.location;
  var path = loc.pathname;
  var hash = loc.hash.replace('#', '');
  var redirect = null;
  if (path.match(/publisher\\.html$/i) && hash) redirect = '/publisher/' + hash + '/';
  else if (path.match(/platform\\.html$/i) && hash) redirect = '/platform/' + hash + '/';
  else if (path.match(/blog\\.html$/i) && hash) redirect = '/blog/' + hash + '/';
  else if (path.match(/publishers\\.html$/i)) redirect = '/publishers/';
  else if (path.match(/platforms\\.html$/i)) redirect = '/platforms/';
  else if (path.match(/about\\.html$/i)) redirect = '/about/';
  else if (path.match(/api\\.html$/i)) redirect = '/api/';
  else if (path.match(/privacy\\.html$/i)) redirect = '/privacy/';
  if (redirect) window.location.replace(redirect);
})();
"""


def generate_static_pages(
    site_dir: Path,
    server_count: int,
    publisher_count: int,
    total_flags: int,
    flag_counts: dict,
    sitemap_urls: list[dict],
    lastmod: str,
) -> int:
    """Generate about, api, privacy, and 404 pages. Returns count."""
    count = 0

    # --- About page ---
    crumbs = [("Home", "/"), ("About", "/about/")]
    json_ld = [organization_jsonld(), breadcrumb_jsonld(crumbs)]

    about_html = base_page(
        title="MCP Scorecard — Mission & Methodology",
        description="Why MCP Scorecard exists. Open-source, non-profit trust scoring for every MCP server. No ads, no tracking, free forever.",
        canonical_path="/about/",
        body_html=breadcrumb_nav(crumbs) + _about_body(server_count, publisher_count, total_flags, flag_counts),
        json_ld=json_ld,
        page_css=ABOUT_CSS,
        active_nav="about",
    )
    _write(site_dir / "about" / "index.html", about_html)
    count += 1

    # --- API page ---
    crumbs = [("Home", "/"), ("API", "/api/")]
    json_ld = [organization_jsonld(), breadcrumb_jsonld(crumbs)]

    api_html = base_page(
        title="MCP Scorecard — API",
        description="Programmatic access to trust scores for every MCP server. Free tier included.",
        canonical_path="/api/",
        body_html=breadcrumb_nav(crumbs) + API_BODY,
        json_ld=json_ld,
        page_css=API_CSS,
        active_nav="api",
        extra_js=API_KEY_JS,
    )
    _write(site_dir / "api" / "index.html", api_html)
    count += 1

    # --- Privacy page ---
    crumbs = [("Home", "/"), ("Privacy", "/privacy/")]
    json_ld = [organization_jsonld(), breadcrumb_jsonld(crumbs)]

    privacy_html = base_page(
        title="Privacy Policy — MCP Scorecard",
        description="MCP Scorecard privacy policy. We collect nothing. No cookies, no analytics, no tracking.",
        canonical_path="/privacy/",
        body_html=breadcrumb_nav(crumbs) + PRIVACY_BODY,
        json_ld=json_ld,
        page_css=PRIVACY_CSS,
    )
    _write(site_dir / "privacy" / "index.html", privacy_html)
    count += 1

    # --- 404 page ---
    body_404 = (
        '<div class="container">'
        '<h2>404</h2>'
        '<p>This page doesn\'t exist. It may have moved when we reorganized URLs.</p>'
        '<div class="links">'
        '<a href="/">Server Listing</a>'
        '<a href="/publishers/">Publishers</a>'
        '<a href="/blog/">Blog</a>'
        '</div>'
        '</div>'
    )
    page_404 = base_page(
        title="Page Not Found — MCP Scorecard",
        description="Page not found.",
        canonical_path="/404.html",
        body_html=body_404,
        page_css=FOUR_OH_FOUR_CSS,
        extra_js=REDIRECT_JS,
    )
    # 404.html goes at site root (GitHub Pages convention)
    _write(site_dir / "404.html", page_404)
    count += 1

    return count


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
