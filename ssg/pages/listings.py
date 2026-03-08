"""Generate listing pages: home, publishers, platforms, blog index.

These pages pre-render initial content as static HTML for crawlers,
then use JavaScript for interactive search/sort/filter.
"""
import html
from pathlib import Path

from ssg.data import score_band
from ssg.render import (
    render_server_row, render_stats_bar, render_score_pill,
    render_targets, score_class, fmt_num, VERIFIED_SVG_14,
)
from ssg.templates import base_page, TOGGLE_DETAIL_JS
from ssg.seo import organization_jsonld, website_jsonld


# ── Homepage (server listing) ──────────────────────────

HOME_CSS = """
  .noscript-list { padding: 16px 32px; }
  .noscript-list a { display: block; padding: 4px 0; font-size: 13px; color: #58a6ff; text-decoration: none; }
  .noscript-list a:hover { text-decoration: underline; }
  .filter-btn { background: #21262d; border: 1px solid #30363d; color: #7d8590; padding: 4px 12px; border-radius: 20px; font-size: 12px; cursor: pointer; }
  .filter-btn:hover, .filter-btn.active { background: #30363d; color: #e6edf3; border-color: #58a6ff; }
"""

# Full interactive JS — ported from index.html with URL patterns updated for SSG
HOME_JS = r"""
let allServers = [];

const filters = {
  credentials: new Set(),
  source: new Set(),
  quality: new Set(),
  provenance: new Set(),
  activity: new Set(),
  popularity: new Set(),
  license: new Set(),
};

function scoreClass(s) {
  if (s >= 80) return 'high';
  if (s >= 60) return 'mod';
  if (s >= 40) return 'low';
  if (s >= 20) return 'vlow';
  return 'unk';
}

function fmtNum(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
  return String(n);
}

var FLAG_SEV = {
  'DEAD_ENTRY':'critical','NO_SOURCE':'critical','SENSITIVE_CRED_REQUEST':'critical',
  'HIGH_SECRET_DEMAND':'warning','STAGING_ARTIFACT':'warning','REPO_ARCHIVED':'warning',
  'TEMPLATE_DESCRIPTION':'info','DESCRIPTION_DUPLICATE':'info',
};
var FLAG_SHORT = {
  'SENSITIVE_CRED_REQUEST':'Sensitive Creds','DEAD_ENTRY':'Dead Entry','NO_SOURCE':'No Source',
  'HIGH_SECRET_DEMAND':'Many Secrets','REPO_ARCHIVED':'Archived','STAGING_ARTIFACT':'Staging',
  'DESCRIPTION_DUPLICATE':'Dup Desc','TEMPLATE_DESCRIPTION':'Template',
};

function renderBadge(b) {
  if (b.type === 'flag') return '<span class="badge badge-flag-' + b.severity + '">' + b.label + '</span>';
  if (b.type === 'bool') return '<span class="badge ' + (b.value ? 'badge-bool-true' : 'badge-bool-false') + '">' + b.label + '</span>';
  if (b.type === 'enum') return '<span class="badge badge-enum-' + b.level + '">' + b.label + ': ' + b.value + '</span>';
  return '';
}

function renderRow(name, s, idx) {
  var cls = scoreClass(s.trust_score);
  var parts = name.split('/');
  var ns = parts[0];
  var id = parts.slice(1).join('/');
  var badges = s.badges || {};
  var pop = badges.popularity || {};
  var repoUrl = (s.install && s.install.repo_url) || (s.signals && s.signals.repo_url) || null;
  var linkIcon = repoUrl
    ? '<a class="row-link" href="' + repoUrl + '" target="_blank" rel="noopener" title="' + repoUrl + '" onclick="event.stopPropagation()"><svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M7.775 3.275a.75.75 0 001.06 1.06l1.25-1.25a2 2 0 112.83 2.83l-2.5 2.5a2 2 0 01-2.83 0 .75.75 0 00-1.06 1.06 3.5 3.5 0 004.95 0l2.5-2.5a3.5 3.5 0 00-4.95-4.95l-1.25 1.25zm-4.69 9.64a2 2 0 010-2.83l2.5-2.5a2 2 0 012.83 0 .75.75 0 001.06-1.06 3.5 3.5 0 00-4.95 0l-2.5 2.5a3.5 3.5 0 004.95 4.95l1.25-1.25a.75.75 0 00-1.06-1.06l-1.25 1.25a2 2 0 01-2.83 0z"/></svg></a>'
    : '';
  var verifiedIcon = s.verified_publisher
    ? '<span class="verified-badge" title="Verified Publisher"><svg width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#58a6ff"/><path d="M9 12l2 2 4-4" stroke="#0d1117" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M9 12l2 2 4-4" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg></span>'
    : '';
  var unidLicIcon = (s.signals && s.signals.github_license === 'NOASSERTION')
    ? '<span class="unid-lic-badge" title="Unidentified License"><svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M12 2L1 21h22L12 2z" fill="#d29922"/><text x="12" y="18" text-anchor="middle" font-size="14" font-weight="bold" fill="#0d1117">!</text></svg></span>'
    : '';
  var rowFlags = s.flags
    .filter(function(f) { return FLAG_SEV[f] !== 'info'; })
    .map(function(f) { return '<span class="row-flag row-flag-' + (FLAG_SEV[f] || 'info') + '">' + (FLAG_SHORT[f] || f) + '</span>'; })
    .join('');
  var rowTargets = (s.targets || [])
    .map(function(t) { return '<span class="row-target">' + t + '</span>'; })
    .join('');
  var popParts = [];
  if (pop.stars > 0) popParts.push('<span>&#9733; <span class="val">' + fmtNum(pop.stars) + '</span></span>');
  if (pop.forks > 0) popParts.push('<span>&#9741; <span class="val">' + fmtNum(pop.forks) + '</span></span>');
  if (pop.watchers > 0) popParts.push('<span>&#9737; <span class="val">' + fmtNum(pop.watchers) + '</span></span>');
  var secBadges = (badges.security || []).map(renderBadge).join('');
  var provBadges = (badges.provenance || []).map(renderBadge).join('');
  var actBadges = (badges.activity || []).map(renderBadge).join('');
  var detailPop = (pop.stars > 0 || pop.forks > 0)
    ? '<div class="detail-pop">' +
      (pop.stars > 0 ? '<span>&#9733; <span class="val">' + fmtNum(pop.stars) + '</span> stars</span>' : '') +
      (pop.forks > 0 ? '<span>&#9741; <span class="val">' + fmtNum(pop.forks) + '</span> forks</span>' : '') +
      (pop.watchers > 0 ? '<span>&#9737; <span class="val">' + fmtNum(pop.watchers) + '</span> watchers</span>' : '') +
      '</div>' : '';
  var install = s.install || {};
  var pkgTypes = install.package_types || [];
  var pkgIds = install.package_identifiers || [];
  var transports = install.transport_types || [];
  var envVars = install.env_vars || [];
  var version = install.version;
  var installHtml = '';
  if (pkgTypes.length > 0 || transports.length > 0 || envVars.length > 0) {
    var iParts = [];
    for (var i = 0; i < pkgTypes.length; i++) {
      var ptype = pkgTypes[i]; var pid = pkgIds[i] || '';
      if (ptype === 'npm') {
        iParts.push('<span class="badge badge-enum-good" title="Click to copy" style="cursor:pointer" onclick="event.stopPropagation();navigator.clipboard.writeText(\'npx -y ' + pid + '\');this.textContent=\'Copied!\';var _t=this;setTimeout(function(){_t.textContent=\'npm: npx -y ' + pid + '\'},1000)">npm: npx -y ' + pid + '</span>');
      } else if (ptype === 'pypi') {
        iParts.push('<span class="badge badge-enum-good" title="Click to copy" style="cursor:pointer" onclick="event.stopPropagation();navigator.clipboard.writeText(\'uvx ' + pid + '\');this.textContent=\'Copied!\';var _t=this;setTimeout(function(){_t.textContent=\'pypi: uvx ' + pid + '\'},1000)">pypi: uvx ' + pid + '</span>');
      } else {
        iParts.push('<span class="badge badge-enum-neutral">' + ptype + ': ' + pid + '</span>');
      }
    }
    for (var ti = 0; ti < transports.length; ti++) {
      var t = transports[ti]; var lvl = t === 'stdio' ? 'good' : 'neutral';
      iParts.push('<span class="badge badge-enum-' + lvl + '">' + t + '</span>');
    }
    if (version) iParts.push('<span class="badge badge-enum-neutral">v' + version + '</span>');
    installHtml = '<div class="badge-group"><span class="badge-group-label">Install</span><div class="badge-row">' + iParts.join('') + '</div></div>';
    if (envVars.length > 0) {
      var evBadges = envVars.map(function(ev) {
        var req = ev.is_required ? 'required' : 'optional';
        var sec = ev.is_secret ? ', secret' : '';
        var elvl = ev.is_secret && ev.is_required ? 'warning' : (ev.is_required ? 'neutral' : 'good');
        return '<span class="badge badge-enum-' + elvl + '" title="' + req + sec + '">' + ev.name + '</span>';
      }).join('');
      installHtml += '<div class="badge-group"><span class="badge-group-label">Env Vars</span><div class="badge-row">' + evBadges + '</div></div>';
    }
  }
  return '<div class="row" data-idx="' + idx + '" onclick="toggleDetail(' + idx + ')">' +
    '<span class="row-chevron">&#9654;</span>' +
    '<span class="score-pill score-' + cls + '">' + s.trust_score + '</span>' +
    '<span class="row-name">' + linkIcon + '<a class="ns" href="/publisher/' + ns + '/" onclick="event.stopPropagation()">' + ns + '/</a>' + id + verifiedIcon + unidLicIcon + '</span>' +
    '<span class="row-flags">' + rowFlags + '</span>' +
    '<span class="row-targets">' + rowTargets + '</span>' +
    '<span class="row-pop">' + popParts.join('') + '</span>' +
    '</div>' +
    '<div class="detail" id="detail-' + idx + '">' +
    (s.verified_publisher ? '<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px"><span class="verified-badge" title="Verified Publisher"><svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#58a6ff"/><path d="M9 12l2 2 4-4" stroke="#0d1117" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M9 12l2 2 4-4" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg></span><span style="font-size:11px;color:#58a6ff;font-weight:600">Verified Publisher</span></div>' : '') +
    '<div class="badge-group"><span class="badge-group-label">Security</span><div class="badge-row">' + secBadges + '</div></div>' +
    '<div class="badge-group"><span class="badge-group-label">Provenance</span><div class="badge-row">' + provBadges + '</div></div>' +
    '<div class="badge-group"><span class="badge-group-label">Activity</span><div class="badge-row">' + actBadges + '</div></div>' +
    detailPop + installHtml +
    '</div>';
}

function toggleDetail(idx) {
  var row = document.querySelector('.row[data-idx="' + idx + '"]');
  var detail = document.getElementById('detail-' + idx);
  var wasOpen = detail.classList.contains('open');
  document.querySelectorAll('.detail.open').forEach(function(d) { d.classList.remove('open'); });
  document.querySelectorAll('.row.expanded').forEach(function(r) { r.classList.remove('expanded'); });
  if (!wasOpen) { detail.classList.add('open'); row.classList.add('expanded'); }
}

var CRED_FLAGS = ['SENSITIVE_CRED_REQUEST', 'HIGH_SECRET_DEMAND'];
var SOURCE_FLAGS = ['DEAD_ENTRY', 'NO_SOURCE', 'REPO_ARCHIVED'];
var QUALITY_FLAGS = ['TEMPLATE_DESCRIPTION', 'DESCRIPTION_DUPLICATE', 'STAGING_ARTIFACT'];

function matchRow(s, cat) {
  var f = filters[cat];
  if (f.size === 0) return true;
  for (var v of f) {
    if (v.startsWith('+')) {
      if (v === '+clean_creds' && !s.flags.some(function(fl) { return CRED_FLAGS.indexOf(fl) >= 0; })) return true;
      if (v === '+has_source' && !s.flags.some(function(fl) { return SOURCE_FLAGS.indexOf(fl) >= 0; })) return true;
      if (v === '+original' && !s.flags.some(function(fl) { return QUALITY_FLAGS.indexOf(fl) >= 0; })) return true;
      if (v === '+full_prov') {
        var prov = (s.badges && s.badges.provenance) || [];
        var has = function(k) { var p = prov.find(function(p) { return p.key === k; }); return p && p.value; };
        var licBadge = prov.find(function(p) { return p.key === 'license'; });
        var hasLic = licBadge && licBadge.level !== 'critical';
        if (has('has_source_repo') && hasLic && has('has_installable_package')) return true;
      }
      if (v === '+active') {
        var act = (s.badges && s.badges.activity) || [];
        var commits = (act.find(function(a) { return a.key === 'commit_activity'; }) || {}).value;
        var push = (act.find(function(a) { return a.key === 'last_push'; }) || {}).value;
        if ((commits === 'active' || commits === 'regular') && (push === '< 30 days' || push === '< 6 months')) return true;
      }
      if (v === '+popular') { if (((s.badges && s.badges.popularity && s.badges.popularity.stars) || 0) >= 100) return true; }
      if (v === '+licensed') { if (((s.signals && s.signals.license_category) || 'unknown') !== 'unknown') return true; }
    }
    else if (s.flags.indexOf(v) >= 0) return true;
    else if (v.startsWith('no:')) {
      var prov2 = (s.badges && s.badges.provenance) || [];
      var p2 = prov2.find(function(p) { return p.key === v.slice(3); });
      if (p2 && !p2.value) return true;
    }
    else if (v === 'lic:permissive' && s.signals && s.signals.license_category === 'permissive') return true;
    else if (v === 'lic:MIT' && s.signals && s.signals.github_license === 'MIT') return true;
    else if (v === 'lic:copyleft' && s.signals && s.signals.license_category === 'copyleft') return true;
    else if (v === 'lic:none' && ((s.signals && s.signals.license_category) || 'unknown') === 'unknown' && !(s.signals && s.signals.github_license === 'NOASSERTION')) return true;
    else if (v === 'lic:unidentified' && s.signals && s.signals.github_license === 'NOASSERTION') return true;
    else if (v === 'stars:0' && ((s.badges && s.badges.popularity && s.badges.popularity.stars) || 0) === 0) return true;
    else if (v === 'stars:10' && ((s.badges && s.badges.popularity && s.badges.popularity.stars) || 0) >= 10) return true;
    else if (v === 'stars:100' && ((s.badges && s.badges.popularity && s.badges.popularity.stars) || 0) >= 100) return true;
    else if (v === 'stars:1000' && ((s.badges && s.badges.popularity && s.badges.popularity.stars) || 0) >= 1000) return true;
    else if (v.indexOf(':') >= 0) {
      var act2 = (s.badges && s.badges.activity) || [];
      for (var ai = 0; ai < act2.length; ai++) {
        if ((act2[ai].key + ':' + act2[ai].value) === v) return true;
      }
    }
  }
  return false;
}

function render() {
  var q = document.getElementById('search').value.toLowerCase();
  var sort = document.getElementById('sort').value;
  var filtered = allServers.filter(function(entry) {
    var name = entry[0]; var s = entry[1];
    if (q && name.toLowerCase().indexOf(q) < 0) return false;
    for (var cat of Object.keys(filters)) {
      if (!matchRow(s, cat)) return false;
    }
    return true;
  });
  if (sort === 'score-desc') filtered.sort(function(a, b) { return b[1].trust_score - a[1].trust_score; });
  else if (sort === 'score-asc') filtered.sort(function(a, b) { return a[1].trust_score - b[1].trust_score; });
  else if (sort === 'name-asc') filtered.sort(function(a, b) { return a[0].localeCompare(b[0]); });
  else if (sort === 'flags-desc') filtered.sort(function(a, b) { return b[1].flags.length - a[1].flags.length || b[1].trust_score - a[1].trust_score; });
  else if (sort === 'stars-desc') filtered.sort(function(a, b) { return ((b[1].badges && b[1].badges.popularity && b[1].badges.popularity.stars) || 0) - ((a[1].badges && a[1].badges.popularity && a[1].badges.popularity.stars) || 0); });
  document.getElementById('list').innerHTML = filtered.map(function(entry, i) { return renderRow(entry[0], entry[1], i); }).join('');
  document.getElementById('count-label').textContent = filtered.length + ' of ' + allServers.length + ' servers';
}

async function init() {
  try {
    var data = await fetchServers();
    allServers = Object.entries(data.servers);
  } catch(e) { return; /* keep pre-rendered content */ }

  var bands = { high: 0, mod: 0, low: 0, vlow: 0, unk: 0 };
  var flagCounts = {};
  var totalScore = 0;
  for (var si = 0; si < allServers.length; si++) {
    var s = allServers[si][1];
    bands[scoreClass(s.trust_score)]++;
    totalScore += s.trust_score;
    for (var fi = 0; fi < s.flags.length; fi++) flagCounts[s.flags[fi]] = (flagCounts[s.flags[fi]] || 0) + 1;
  }
  var flagged = allServers.filter(function(e) { return e[1].flags.length > 0; }).length;

  document.getElementById('stats-bar').innerHTML =
    '<div class="stat"><div class="num">' + allServers.length + '</div><div class="label">Servers</div></div>' +
    '<div class="stat-sep"></div>' +
    '<div class="stat band-high"><div class="num">' + bands.high + '</div><div class="label">High Trust</div></div>' +
    '<div class="stat band-mod"><div class="num">' + bands.mod + '</div><div class="label">Moderate</div></div>' +
    '<div class="stat band-low"><div class="num">' + bands.low + '</div><div class="label">Low Trust</div></div>' +
    '<div class="stat band-vlow"><div class="num">' + bands.vlow + '</div><div class="label">Very Low</div></div>' +
    '<div class="stat-sep"></div>' +
    '<div class="stat band-unk"><div class="num">' + bands.unk + '</div><div class="label">Suspicious</div></div>' +
    '<div class="stat"><div class="num" style="color:#f85149">' + flagged + '</div><div class="label">Flagged</div></div>';

  /* --- Build filter panel --- */
  var provCounts = {}; var actCounts = {};
  var starBuckets = { 0: 0, 10: 0, 100: 0, 1000: 0 };
  var cleanCreds = 0, hasSource = 0, original = 0, fullProv = 0, activeDevs = 0, popular = 0;
  var licCounts = { permissive: 0, copyleft: 0, none: 0, unidentified: 0, licensed: 0 };

  for (var si2 = 0; si2 < allServers.length; si2++) {
    var s2 = allServers[si2][1];
    if (!s2.flags.some(function(f) { return CRED_FLAGS.indexOf(f) >= 0; })) cleanCreds++;
    if (!s2.flags.some(function(f) { return SOURCE_FLAGS.indexOf(f) >= 0; })) hasSource++;
    if (!s2.flags.some(function(f) { return QUALITY_FLAGS.indexOf(f) >= 0; })) original++;

    var prov = (s2.badges && s2.badges.provenance) || [];
    var hasP = function(k) { var p = prov.find(function(p) { return p.key === k; }); return p && p.value; };
    var licBadge = prov.find(function(p) { return p.key === 'license'; });
    var hasLic = licBadge && licBadge.level !== 'critical';
    if (hasP('has_source_repo') && hasLic && hasP('has_installable_package')) fullProv++;

    var act = (s2.badges && s2.badges.activity) || [];
    var commits = (act.find(function(a) { return a.key === 'commit_activity'; }) || {}).value;
    var push = (act.find(function(a) { return a.key === 'last_push'; }) || {}).value;
    if ((commits === 'active' || commits === 'regular') && (push === '< 30 days' || push === '< 6 months')) activeDevs++;

    var stars = (s2.badges && s2.badges.popularity && s2.badges.popularity.stars) || 0;
    if (stars >= 100) popular++;
    if (stars === 0) starBuckets[0]++;
    if (stars >= 10) starBuckets[10]++;
    if (stars >= 100) starBuckets[100]++;
    if (stars >= 1000) starBuckets[1000]++;

    var licCat = (s2.signals && s2.signals.license_category) || 'unknown';
    if (licCat !== 'unknown') licCounts.licensed++;
    licCounts[licCat] = (licCounts[licCat] || 0) + 1;
    if (s2.signals && s2.signals.github_license === 'MIT') licCounts.MIT = (licCounts.MIT || 0) + 1;
    if (licCat === 'unknown') {
      if (s2.signals && s2.signals.github_license === 'NOASSERTION') licCounts.unidentified++;
      else licCounts.none++;
    }
    for (var bi = 0; bi < prov.length; bi++) {
      if (!prov[bi].value) provCounts['no:' + prov[bi].key] = (provCounts['no:' + prov[bi].key] || 0) + 1;
    }
    for (var ai2 = 0; ai2 < act.length; ai2++) {
      var ak = act[ai2].key + ':' + act[ai2].value;
      actCounts[ak] = (actCounts[ak] || 0) + 1;
    }
  }

  var sep = '<span class="pill-sep"></span>';
  function pillRow(posPill, negPills) {
    return '<div class="pill-lead">' + posPill + sep + '</div><div class="pill-rest">' + negPills + '</div>';
  }
  var PILL_SEV = {
    'SENSITIVE_CRED_REQUEST':'critical','HIGH_SECRET_DEMAND':'warning',
    'DEAD_ENTRY':'critical','NO_SOURCE':'critical','REPO_ARCHIVED':'warning',
    'TEMPLATE_DESCRIPTION':'info','DESCRIPTION_DUPLICATE':'info','STAGING_ARTIFACT':'warning',
  };
  var ACT_SEV = {
    'commit_activity:dormant':'critical','last_push:> 1 year':'critical',
    'contributors:solo':'neutral','repo_age:< 90 days':'new','contributors:community':'good',
  };
  function flagPill(flag, label, cat) {
    var sev = PILL_SEV[flag] || 'info';
    return '<button class="pill pill-' + sev + '" data-cat="' + cat + '" data-val="' + flag + '">' + label + '<span class="pill-count">' + flagCounts[flag] + '</span></button>';
  }

  var credPills = pillRow(
    '<button class="pill pill-positive" data-cat="credentials" data-val="+clean_creds">Clean Credentials<span class="pill-count">' + cleanCreds + '</span></button>',
    [['SENSITIVE_CRED_REQUEST','Sensitive Creds'],['HIGH_SECRET_DEMAND','Many Secrets']].filter(function(x){return flagCounts[x[0]];}).map(function(x){return flagPill(x[0],x[1],'credentials');}).join('')
  );
  var srcPills = pillRow(
    '<button class="pill pill-positive" data-cat="source" data-val="+has_source">Has Source<span class="pill-count">' + hasSource + '</span></button>',
    [['DEAD_ENTRY','Dead Entry'],['NO_SOURCE','No Source'],['REPO_ARCHIVED','Archived']].filter(function(x){return flagCounts[x[0]];}).map(function(x){return flagPill(x[0],x[1],'source');}).join('')
  );
  var qualPills = pillRow(
    '<button class="pill pill-positive" data-cat="quality" data-val="+original">Original<span class="pill-count">' + original + '</span></button>',
    [['TEMPLATE_DESCRIPTION','Template Desc'],['DESCRIPTION_DUPLICATE','Duplicate Desc'],['STAGING_ARTIFACT','Staging']].filter(function(x){return flagCounts[x[0]];}).map(function(x){return flagPill(x[0],x[1],'quality');}).join('')
  );
  var provPillsHtml = pillRow(
    '<button class="pill pill-positive" data-cat="provenance" data-val="+full_prov">Full Provenance<span class="pill-count">' + fullProv + '</span></button>',
    [['no:has_source_repo','No Repo'],['no:has_license','No License'],['no:has_installable_package','No Package'],['no:namespace_matches_owner','No NS Match'],['no:has_security_md','No SECURITY.md']].filter(function(x){return provCounts[x[0]];}).map(function(x){return '<button class="pill pill-warning" data-cat="provenance" data-val="' + x[0] + '">' + x[1] + '<span class="pill-count">' + provCounts[x[0]] + '</span></button>';}).join('')
  );
  var actPillsHtml = pillRow(
    '<button class="pill pill-positive" data-cat="activity" data-val="+active">Active<span class="pill-count">' + activeDevs + '</span></button>',
    [['commit_activity:dormant','Dormant'],['last_push:> 1 year','Stale > 1yr'],['contributors:solo','Solo Dev'],['repo_age:< 90 days','New Repo'],['contributors:community','Community']].filter(function(x){return actCounts[x[0]];}).map(function(x){return '<button class="pill pill-' + (ACT_SEV[x[0]] || 'neutral') + '" data-cat="activity" data-val="' + x[0] + '">' + x[1] + '<span class="pill-count">' + actCounts[x[0]] + '</span></button>';}).join('')
  );
  var popPillsHtml = pillRow(
    '<button class="pill pill-positive" data-cat="popularity" data-val="+popular">Popular<span class="pill-count">' + popular + '</span></button>',
    [[['stars:0','No Stars',starBuckets[0],'neutral'],['stars:10','10+',starBuckets[10],'neutral'],['stars:100','100+',starBuckets[100],'good'],['stars:1000','1k+',starBuckets[1000],'good']]].flat().filter(function(x){return x[2]>0;}).map(function(x){return '<button class="pill pill-' + x[3] + '" data-cat="popularity" data-val="' + x[0] + '">' + x[1] + '<span class="pill-count">' + x[2] + '</span></button>';}).join('')
  );
  var licPillsHtml = pillRow(
    '<button class="pill pill-positive" data-cat="license" data-val="+licensed">Licensed<span class="pill-count">' + licCounts.licensed + '</span></button>',
    [['lic:permissive','Permissive',licCounts.permissive,'good'],['lic:MIT','MIT',licCounts.MIT||0,'good'],['lic:copyleft','Copyleft',licCounts.copyleft,'neutral'],['lic:none','No License',licCounts.none,'warning'],['lic:unidentified','Unidentified',licCounts.unidentified,'neutral']].filter(function(x){return x[2]>0;}).map(function(x){return '<button class="pill pill-' + x[3] + '" data-cat="license" data-val="' + x[0] + '">' + x[1] + '<span class="pill-count">' + x[2] + '</span></button>';}).join('')
  );

  document.getElementById('filter-panel').innerHTML =
    '<div class="filter-row"><span class="filter-row-label credentials">Credentials</span>' + credPills + '</div>' +
    '<div class="filter-row"><span class="filter-row-label source">Source</span>' + srcPills + '</div>' +
    '<div class="filter-row"><span class="filter-row-label provenance">Provenance</span>' + provPillsHtml + '</div>' +
    '<div class="filter-row"><span class="filter-row-label description">Description</span>' + qualPills + '</div>' +
    '<div class="filter-row"><span class="filter-row-label activity">Activity</span>' + actPillsHtml + '</div>' +
    '<div class="filter-row"><span class="filter-row-label popularity">Popularity</span>' + popPillsHtml + '</div>' +
    '<div class="filter-row"><span class="filter-row-label license">License</span>' + licPillsHtml + '</div>';

  document.querySelectorAll('.pill').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var cat = btn.dataset.cat; var val = btn.dataset.val;
      if (filters[cat].has(val)) { filters[cat].delete(val); btn.classList.remove('active'); }
      else { filters[cat].add(val); btn.classList.add('active'); }
      render();
    });
  });

  document.getElementById('search').addEventListener('input', render);
  document.getElementById('sort').addEventListener('change', render);
  render();
}

init();
"""


def generate_home_page(
    site_dir: Path,
    servers: dict,
    bands: dict,
    total_flagged: int,
) -> None:
    """Generate the homepage with pre-rendered server listing + full JS hydration."""
    server_count = len(servers)

    # Stats bar (pre-rendered for crawlers, JS replaces on load)
    global_bands = {}
    for key in ["high", "mod", "low", "vlow", "unk"]:
        global_bands[key] = bands[key]["count"]
    stats_html = render_stats_bar(server_count, global_bands, flagged=total_flagged)
    # Wrap in id for JS replacement
    stats_html = stats_html.replace('<div class="stats-bar">', '<div class="stats-bar" id="stats-bar">', 1)

    # Pre-render first 100 servers sorted by score (crawler sees these)
    sorted_servers = sorted(servers.items(), key=lambda x: x[1].get("trust_score", 0), reverse=True)

    rows = []
    for i, (name, s) in enumerate(sorted_servers[:100]):
        rows.append(render_server_row(name, s, i, show_ns=True))
    pre_rendered_list = f'<div class="list" id="list">{"".join(rows)}</div>'

    # Noscript fallback — linked list for crawlers without JS
    noscript_links = []
    for name, s in sorted_servers[:200]:
        ns = name.split("/")[0]
        sid = "/".join(name.split("/")[1:])
        score = s.get("trust_score", 0)
        noscript_links.append(
            f'<a href="/server/{name}/">[{score}] {html.escape(ns)}/{html.escape(sid)}</a>'
        )
    noscript_html = (
        '<noscript>'
        f'<div class="noscript-list">{"".join(noscript_links)}</div>'
        '</noscript>'
    )

    # Controls — match original IDs so JS can wire up
    controls_html = (
        '<div class="controls">'
        '<input type="text" class="search" id="search" placeholder="Search servers..." role="search" aria-label="Search servers">'
        '<select class="sort-select" id="sort" aria-label="Sort order">'
        '<option value="score-desc">Score: High &rarr; Low</option>'
        '<option value="score-asc">Score: Low &rarr; High</option>'
        '<option value="name-asc">Name: A &rarr; Z</option>'
        '<option value="flags-desc">Most Flags</option>'
        '<option value="stars-desc">Most Stars</option>'
        '</select>'
        '<span class="count-label" id="count-label"></span>'
        '</div>'
    )

    # Empty filter panel — JS populates this
    filter_panel = '<div class="filter-panel" id="filter-panel"></div>'

    body_html = stats_html + controls_html + filter_panel + pre_rendered_list + noscript_html

    json_ld = [organization_jsonld(), website_jsonld()]

    page_html = base_page(
        title="MCP Scorecard — Trust Scores for Every MCP Server",
        description=f"Independent trust scores for {server_count:,} MCP servers. Search, filter, and compare servers by provenance, maintenance, popularity, and permissions.",
        canonical_path="/",
        body_html=body_html,
        json_ld=json_ld,
        page_css=HOME_CSS,
        active_nav="servers",
        extra_head='<script src="/js/supabase.js"></script>',
        extra_js=HOME_JS,
    )

    out_path = site_dir / "index.html"
    out_path.write_text(page_html, encoding="utf-8")


# ── Publishers listing ──────────────────────────────────

PUBLISHERS_CSS = """
  .pub-list-hero { padding: 32px 32px 24px; border-bottom: 1px solid #21262d; }
  .pub-list-hero h2 { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
  .pub-list-hero p { font-size: 14px; color: #7d8590; }
  .pub-grid { display: flex; flex-direction: column; }
  .pub-row { display: flex; align-items: center; gap: 12px; padding: 8px 32px; border-bottom: 1px solid #21262d; text-decoration: none; }
  .pub-row:hover { background: #161b22; text-decoration: none; }
  .pub-row .pub-ns { font-size: 13px; font-weight: 600; color: #e6edf3; min-width: 180px; display: flex; align-items: center; gap: 5px; }
  .pub-row .pub-count { font-size: 12px; color: #7d8590; min-width: 60px; }
  .pub-row .pub-avg { font-size: 12px; min-width: 50px; text-align: center; }
  .pub-row .pub-stars { font-size: 12px; color: #7d8590; }
  @media (max-width: 768px) {
    .pub-row { padding: 8px 16px; }
    .pub-row .pub-stars { display: none; }
  }
"""


def generate_publishers_page(
    site_dir: Path,
    publishers: dict,
) -> None:
    """Generate /publishers/ listing page."""
    # Sort by avg score desc
    sorted_pubs = sorted(publishers.items(), key=lambda x: (x[1]["avg_score"], x[1]["server_count"]), reverse=True)

    hero_html = (
        '<div class="pub-list-hero">'
        f'<h2>Publishers ({len(publishers):,})</h2>'
        '<p>All publisher namespaces in the MCP registry, sorted by average trust score.</p>'
        '</div>'
    )

    rows = []
    for ns, pub in sorted_pubs:
        ns_esc = html.escape(ns)
        avg = pub["avg_score"]
        cls = score_class(avg)
        scount = pub["server_count"]
        stars = pub["total_stars"]
        verified = ""
        if pub.get("verified"):
            verified = f'<span class="verified-badge" title="Verified Publisher">{VERIFIED_SVG_14}</span>'
        stars_html = f'<span class="pub-stars">&#9733; {fmt_num(stars)}</span>' if stars > 0 else ""
        rows.append(
            f'<a class="pub-row" href="/publisher/{ns}/">'
            f'<span class="pub-ns">{ns_esc}{verified}</span>'
            f'<span class="pub-count">{scount} server{"s" if scount != 1 else ""}</span>'
            f'<span class="pub-avg score-pill score-{cls}">{avg}</span>'
            f'{stars_html}'
            f'</a>'
        )
    list_html = f'<div class="pub-grid">{"".join(rows)}</div>'

    json_ld = [organization_jsonld()]

    page_html = base_page(
        title="MCP Server Publishers — Trust Scores | MCP Scorecard",
        description=f"Browse {len(publishers):,} MCP server publishers. Sorted by average trust score.",
        canonical_path="/publishers/",
        body_html=hero_html + list_html,
        json_ld=json_ld,
        page_css=PUBLISHERS_CSS,
        active_nav="publishers",
    )

    out_path = site_dir / "publishers" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page_html, encoding="utf-8")


# ── Platforms listing ──────────────────────────────────

PLATFORMS_CSS = """
  .plat-list-hero { padding: 32px 32px 24px; border-bottom: 1px solid #21262d; }
  .plat-list-hero h2 { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
  .plat-list-hero p { font-size: 14px; color: #7d8590; }
  .plat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; padding: 24px 32px; }
  .plat-card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px; text-decoration: none; transition: border-color 0.15s; }
  .plat-card:hover { border-color: #58a6ff; text-decoration: none; }
  .plat-card-name { font-size: 15px; font-weight: 600; color: #e6edf3; margin-bottom: 6px; }
  .plat-card-meta { font-size: 12px; color: #7d8590; display: flex; gap: 12px; }
  @media (max-width: 480px) { .plat-grid { grid-template-columns: 1fr; padding: 16px; } }
"""


def generate_platforms_page(
    site_dir: Path,
    platforms: dict,
) -> None:
    """Generate /platforms/ listing page."""
    sorted_plats = sorted(platforms.items(), key=lambda x: x[1]["server_count"], reverse=True)

    hero_html = (
        '<div class="plat-list-hero">'
        f'<h2>Platforms ({len(platforms)})</h2>'
        '<p>Target platforms and integrations in the MCP ecosystem, sorted by server count.</p>'
        '</div>'
    )

    cards = []
    for target, plat in sorted_plats:
        slug = plat["slug"]
        name_esc = html.escape(target)
        scount = plat["server_count"]
        avg = plat["avg_score"]
        cls = score_class(avg)
        cards.append(
            f'<a class="plat-card" href="/platform/{slug}/">'
            f'<div class="plat-card-name">{name_esc}</div>'
            f'<div class="plat-card-meta">'
            f'<span>{scount} servers</span>'
            f'<span class="score-pill score-{cls}" style="font-size:11px;padding:1px 6px">{avg} avg</span>'
            f'</div>'
            f'</a>'
        )
    grid_html = f'<div class="plat-grid">{"".join(cards)}</div>'

    json_ld = [organization_jsonld()]

    page_html = base_page(
        title="MCP Server Platforms — Trust Scores | MCP Scorecard",
        description=f"Browse {len(platforms)} target platforms in the MCP ecosystem. See server counts and average trust scores.",
        canonical_path="/platforms/",
        body_html=hero_html + grid_html,
        json_ld=json_ld,
        page_css=PLATFORMS_CSS,
        active_nav="platforms",
    )

    out_path = site_dir / "platforms" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page_html, encoding="utf-8")


# ── Blog index ──────────────────────────────────────────

BLOG_INDEX_CSS = """
  .layout { display: flex; max-width: 1000px; margin: 0 auto; padding: 0 24px; gap: 48px; }
  .main { flex: 1; min-width: 0; padding: 48px 0; }
  .main h2 { font-size: 28px; font-weight: 700; margin-bottom: 32px; }
  .sidebar { width: 220px; flex-shrink: 0; padding: 48px 0; border-left: 1px solid #21262d; padding-left: 24px; }
  .sb-section { margin-bottom: 28px; }
  .sb-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #484f58; margin-bottom: 10px; }
  .sb-item { display: block; font-size: 13px; color: #7d8590; padding: 3px 0; text-decoration: none; }
  .sb-item:hover { color: #58a6ff; text-decoration: none; }
  .sb-count { float: right; color: #484f58; font-size: 12px; }
  .sb-tag { display: inline-flex; align-items: center; gap: 6px; }
  .sb-tag .tag { font-size: 10px; padding: 1px 6px; }
  .sb-pub { font-family: monospace; font-size: 12px; }
  .post-card { border-bottom: 1px solid #21262d; padding: 24px 0; }
  .post-card:first-of-type { padding-top: 0; }
  .post-card:last-of-type { border-bottom: none; }
  .post-date { font-size: 12px; color: #7d8590; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
  .post-title { font-size: 20px; font-weight: 600; margin-bottom: 8px; }
  .post-title a { color: #e6edf3; }
  .post-title a:hover { color: #58a6ff; text-decoration: none; }
  .post-summary { font-size: 15px; color: #7d8590; line-height: 1.5; }
  .post-pubs { margin-top: 8px; display: flex; gap: 4px; flex-wrap: wrap; }
  .post-pub { font-size: 10px; padding: 1px 6px; border-radius: 3px; background: rgba(88,166,255,0.08); color: #58a6ff; font-family: monospace; text-decoration: none; }
  .post-pub:hover { background: rgba(88,166,255,0.18); text-decoration: none; }
  .tag { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.5px; vertical-align: middle; }
  .tag-pulse { background: rgba(88,166,255,0.15); color: #58a6ff; }
  .tag-spotlight { background: rgba(63,185,80,0.15); color: #3fb950; }
  .tag-trend { background: rgba(210,153,34,0.15); color: #d29922; }
  .tag-investigation { background: rgba(248,81,73,0.15); color: #f85149; }
  .tag-interview { background: rgba(163,113,247,0.15); color: #a371f7; }
  .tag-comparison { background: rgba(88,166,255,0.15); color: #58a6ff; }
  .tag-incident { background: rgba(248,81,73,0.15); color: #f85149; }
  @media (max-width: 768px) {
    .layout { flex-direction: column; gap: 0; }
    .sidebar { width: 100%; border-left: none; border-top: 1px solid #21262d; padding-left: 0; padding-top: 24px; }
  }
"""


def _build_blog_sidebar(posts: list[dict]) -> str:
    """Build blog sidebar HTML with tag counts, archive, and publisher mentions."""
    from datetime import datetime

    # Tag counts
    tag_counts: dict[str, int] = {}
    pub_counts: dict[str, int] = {}
    months: dict[str, int] = {}
    for p in posts:
        tag = p.get("tag", "")
        if tag:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        date = p.get("date", "")
        if date:
            m = date[:7]
            months[m] = months.get(m, 0) + 1
        for pub in p.get("publishers", []):
            pub_counts[pub] = pub_counts.get(pub, 0) + 1

    # Tags section
    tag_order = ["Pulse", "Spotlight", "Trend", "Investigation", "Interview", "Comparison", "Incident"]
    tags_html = ""
    for t in tag_order:
        if t in tag_counts:
            t_lower = t.lower()
            tags_html += (
                f'<span class="sb-item"><span class="sb-tag">'
                f'<span class="tag tag-{t_lower}">{html.escape(t)}</span></span>'
                f'<span class="sb-count">{tag_counts[t]}</span></span>'
            )

    # Archive section
    archive_html = ""
    for m in sorted(months.keys(), reverse=True):
        try:
            dt = datetime.strptime(m + "-01", "%Y-%m-%d")
            label = dt.strftime("%B %Y")
        except ValueError:
            label = m
        archive_html += f'<span class="sb-item">{label}<span class="sb-count">{months[m]}</span></span>'

    # Publishers mentioned section
    sorted_pubs = sorted(pub_counts.items(), key=lambda x: x[1], reverse=True)[:12]
    pub_html = ""
    for pub, count in sorted_pubs:
        pub_html += (
            f'<a class="sb-item sb-pub" href="/publisher/{html.escape(pub)}/">'
            f'{html.escape(pub)}<span class="sb-count">{count}</span></a>'
        )

    return (
        '<div class="sidebar">'
        '<div class="sb-section">'
        '<div class="sb-label">Article Type</div>'
        f'{tags_html}'
        '</div>'
        '<div class="sb-section">'
        '<div class="sb-label">Archive</div>'
        f'{archive_html}'
        '</div>'
        '<div class="sb-section">'
        '<div class="sb-label">Publishers Mentioned</div>'
        f'{pub_html}'
        '</div>'
        '</div>'
    )


def generate_blog_index(
    site_dir: Path,
    posts: list[dict],
) -> None:
    """Generate /blog/ listing page with sidebar."""
    cards = []
    for p in posts:
        slug = html.escape(p.get("slug", ""))
        title = html.escape(p.get("title", ""))
        date = html.escape(p.get("date", ""))
        summary = html.escape(p.get("summary", ""))
        tag = p.get("tag", "")
        tag_lower = tag.lower() if tag else ""
        tag_html = f'<span class="tag tag-{tag_lower}">{html.escape(tag)}</span> &nbsp;' if tag else ""

        pubs = p.get("publishers", [])
        pub_pills = "".join(
            f'<a class="post-pub" href="/publisher/{html.escape(pub)}/">{html.escape(pub)}</a>'
            for pub in pubs[:5]
        )
        pub_html = f'<div class="post-pubs">{pub_pills}</div>' if pub_pills else ""

        cards.append(
            f'<div class="post-card">'
            f'<div class="post-date">{tag_html}{date}</div>'
            f'<div class="post-title"><a href="/blog/{slug}/">{title}</a></div>'
            f'<div class="post-summary">{summary}</div>'
            f'{pub_html}'
            f'</div>'
        )

    sidebar_html = _build_blog_sidebar(posts)

    body_html = (
        '<div class="layout">'
        f'<div class="main"><h2>Blog</h2>{"".join(cards)}</div>'
        f'{sidebar_html}'
        '</div>'
    )

    json_ld = [organization_jsonld()]

    page_html = base_page(
        title="MCP Scorecard Blog — Analysis & Ecosystem Reports",
        description=f"{len(posts)} articles covering the MCP server ecosystem. Trust analysis, publisher spotlights, and weekly registry pulse reports.",
        canonical_path="/blog/",
        body_html=body_html,
        json_ld=json_ld,
        page_css=BLOG_INDEX_CSS,
        active_nav="blog",
        extra_head='<link rel="alternate" type="application/rss+xml" title="MCP Scorecard Blog" href="/feed.xml">',
    )

    out_path = site_dir / "blog" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page_html, encoding="utf-8")
