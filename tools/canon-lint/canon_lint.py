#!/usr/bin/env python3
"""canon-lint — deterministic consistency linter for a fleet canon repo.

Stdlib-only, zero dependencies, no LLM. Enforces the two-zone folder schema
defined in CONVENTIONS.md ("Lintable structure"):

    agents/<name>/
      profile.md    required — identity + index; the reachability root
      facts.yaml    required — the purely lintable zone: structured claims
      docs/         prose zone — front-matter envelope linted, body never read
      files/        shared artifacts — must be referenced, no orphans
      projects/     LEGACY (R21) — shared projects under an agent folder; tolerated
                    until each moves to the top-level zone below (Tandem: ent#585)

    projects/<slug>/ (top level, R35) — company projects, the one zone everyone
                    reads and writes. project.md carries a linted charter envelope;
                    decisions.md is an append-only ledger; everything else in the
                    slug folder is unlinted workspace. The same rule lints the legacy
                    agents/<name>/projects/<slug>/ placement.

The lintable zone uses a deliberately RESTRICTED grammar (a strict YAML
subset): flat `key: value` scalars, full-line comments only, values that
contain ": " must be quoted. Every file stays valid YAML for other tools;
this linter parses the subset itself so it needs no YAML library.

Usage:
    canon_lint.py [--repo PATH] [--rules PATH] [--scope agents/<name>]
                  [--format text|json] [--today YYYY-MM-DD] [--baseline FINDINGS.json]
    canon_lint.py --changed-domains BASE --scope agents/<name> [--format json]

Exit codes: 0 = pass (warnings allowed) · 1 = failures · 2 = bad invocation.

--baseline (the ratchet): pass a previous `--format json` report (typically this same
linter run against the PR's base tree) and the exit code is decided by NEW failures only —
findings absent from the baseline. Pre-existing findings are still printed, marked
`(baseline)`, so a repo that is already red can gate PRs on "no new findings" without
first paying down every debt. A finding is identified by (rule, path, message); line
numbers are deliberately not part of the key, so an unrelated edit above a stale fact
does not make it "new".
"""

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

RULE_DEFAULTS = {
    "layout": "warn",             # unexpected top-level entries in a folder
    "envelope": "fail",           # profile.md/docs front matter parses + required keys
    "fact-schema": "fail",        # facts.yaml present, parses, entries complete + typed
    "key-grammar": "fail",        # fact keys match subject.relation grammar
    "one-home-per-key": "fail",   # a non-superseded key lives in exactly one folder
    "ownership": "fail",          # owner == enclosing folder name
    "staleness": "fail",          # canonical items past review_by
    "source-resolution": "fail",  # local fact sources must exist
    "metrics-schema": "warn",     # metrics/<period>.yaml placeable on a timeline (protocols/metrics-publication.md)
    "reachability": "fail",       # canonical docs linked from profile.md; no orphan files; drafts unlinked
    "project-envelope": "fail",   # projects/<slug>/project.md present + charter envelope; decisions.md envelope
    "top-level-layout": "warn",   # expected root entries only; domains/<id>/ matches a domains.yaml id
    "domain-schema": "warn",      # domains.yaml envelope + one map per domain, complete and resolvable
    "role-schema": "warn",        # roles/<id>.yaml: id == filename, vocabularies, refs resolve
    "objective-schema": "warn",   # objectives/<id>.yaml: id == filename, role owner, metric entries
    "objective-metric-name": "fail",  # a metric name must be declarable AND recordable (registry class)
    "role-binding": "warn",       # every agent named in the top level is one this canon knows
    "guard-schema": "warn",       # guard_metrics: the codified shape (hold + served_by + target)
    "consumer-anchor": "warn",    # every consumer of an anchored domain stamps consumes.<domain>.<agent>[-<surface>] at the domain's anchor sha
    "orphan-subject": "warn",     # a fact subject published in 2+ folders that no domain claims; a claimed key homed outside its domain's owner
    "retired-phrase": "warn",     # a phrase a change notice retired still sits in a folder — the stamp says rebuilt, the text says otherwise
    "unanchored-domain": "warn",  # a `propagation: copied` domain has no anchor, so nobody can be told they are behind
}
STATUS_VOCAB = ("canonical", "draft", "superseded")
REQUIRED_FACT_KEYS = ("key", "value", "status", "updated", "review_by", "source")
REQUIRED_DOC_KEYS = ("owner", "status", "updated", "review_by", "tldr")
# projects/<slug>/project.md — the shared-project charter (CONVENTIONS.md § Project charter; R35
# placement at the top level, R21's agents/<name>/projects/ tolerated until each project moves).
# `status` mirrors the registry epic's status:* label, so the vocabulary is the PM standard's, not
# the doc conviction levels; `epic` names the registry epic the charter mirrors.
REQUIRED_PROJECT_KEYS = ("owner", "status", "epic", "updated", "review_by", "tldr")
PROJECT_STATUS_VOCAB = ("active", "blocked", "needs-decision", "paused", "pending-verification", "done")
PROJECT_STALENESS_EXEMPT = ("paused", "done")   # the steward skips paused; done is terminal
# decisions.md — append-only ledger. Standard doc envelope keys minus review_by: nothing ever
# re-stamps a ledger, so a review date on it would only ever go stale.
REQUIRED_LEDGER_KEYS = ("owner", "status", "updated", "tldr")
# `#0` is legal: "not yet registered" — a charter scaffolded before its epic exists (a /project-init
# --dry-run). The linter checks shape only; /canon-reconcile flags an unregistered epic.
EPIC_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#(0|[1-9][0-9]*)$")
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(\.[a-z0-9][a-z0-9-]*)+$")
KV_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s+(.*))?$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
ALLOWED_TOP = {"profile.md", "facts.yaml", "docs", "files", "metrics", "projects", "NEEDS-REVIEW.md", "sot_mirror"}
# sot_mirror: corbin's verbatim SoT canon mirror (protocols/sot-canon-mirror.md) -
# payload files are byte-identical to source-of-truth and carry NO envelopes by design;
# the envelope lives in sot_mirror/MIRROR.yaml alone.


class Lint:
    def __init__(self, severities, today):
        self.severities = severities
        self.today = today
        self.findings = []
        self.counts = {"folders": 0, "docs": 0, "facts": 0}

    def add(self, rule, path, line, message):
        sev = self.severities.get(rule, "fail")
        if sev == "off":
            return
        self.findings.append(
            {"rule": rule, "severity": sev, "path": str(path), "line": line, "message": message}
        )


def unquoted(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1], True
    return v, False


def parse_kv(stripped):
    """Parse one `key: value` line of the restricted grammar. Returns (key, value, error)."""
    m = KV_RE.match(stripped)
    if not m:
        return None, None, "not a `key: value` line (restricted grammar: flat scalars only)"
    key, raw = m.group(1), m.group(2) or ""
    value, was_quoted = unquoted(raw)
    if not was_quoted and ": " in raw:
        return key, value, "value contains ': ' and must be quoted to stay valid YAML"
    return key, value, None


def valid_date(v):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", v or ""):
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


def parse_front_matter(lint, path, text):
    """Returns (meta dict, body string). Emits envelope findings for grammar errors."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        lint.add("envelope", path, 1, "missing front matter (file must open with `---`)")
        return {}, text
    meta, end = {}, None
    for i, raw in enumerate(lines[1:], start=2):
        s = raw.strip()
        if s == "---":
            end = i
            break
        if not s or s.startswith("#"):
            continue
        key, value, err = parse_kv(s)
        if err:
            lint.add("envelope", path, i, err)
            continue
        if key in meta:
            lint.add("envelope", path, i, f"duplicate front-matter key `{key}`")
        meta[key] = value
    if end is None:
        lint.add("envelope", path, 1, "unterminated front matter (no closing `---`)")
        return meta, ""
    return meta, "\n".join(lines[end:])


def parse_facts(lint, path, text):
    """Parse facts.yaml (restricted grammar). Returns list of entries with __line markers."""
    entries, current, header_seen, empty_list = [], None, False, False
    for i, raw in enumerate(text.splitlines(), start=1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if not header_seen:
            if s == "facts:":
                header_seen = True
            elif s == "facts: []":
                header_seen, empty_list = True, True
            else:
                lint.add("fact-schema", path, i, "file must start with `facts:` (or `facts: []` when empty)")
                header_seen = True  # report once, keep parsing
            continue
        if s.startswith("- "):
            if empty_list:
                lint.add("fact-schema", path, i, "entries present but header says `facts: []`")
                empty_list = False
            current = {"__line": i}
            entries.append(current)
            s = s[2:].strip()
        if current is None:
            lint.add("fact-schema", path, i, "content outside a `- ` list entry")
            continue
        key, value, err = parse_kv(s)
        if err:
            lint.add("fact-schema", path, i, err)
            continue
        if key in current:
            lint.add("fact-schema", path, i, f"duplicate field `{key}` in one entry")
        current[key] = value
    return entries


def check_dates_and_staleness(lint, path, line, item, status, label):
    for field in ("updated", "review_by"):
        if field in item and valid_date(item.get(field)) is None:
            rule = "fact-schema" if label.startswith("fact") else "envelope"
            lint.add(rule, path, line, f"`{field}: {item.get(field)}` is not a valid YYYY-MM-DD date")
    due = valid_date(item.get("review_by", ""))
    if status == "canonical" and due is not None and due < lint.today:
        lint.add("staleness", path, line, f"{label} past review_by {item['review_by']} — verify and re-stamp (canon-reconcile)")


PERIOD_MONTHLY_RE = re.compile(r"^(\d{4})-(\d{2})$")
PERIOD_WEEKLY_RE = re.compile(r"^(\d{4})-W(\d{2})$")
WINDOW_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})$")
METRIC_LEAF_RE = re.compile(r"^\s{4,}([a-z0-9_]+):\s*\{(.*)\}\s*$")
REQUIRED_METRIC_ENVELOPE = ("owner", "period", "period_type", "window", "updated", "verified")


def period_bounds(period):
    """Canonical [start, end] for a period id, or None if the id is malformed."""
    m = PERIOD_MONTHLY_RE.match(period)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if not 1 <= mo <= 12:
            return None
        start = date(y, mo, 1)
        end = date(y + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1)
        return start, end
    m = PERIOD_WEEKLY_RE.match(period)
    if m:
        try:
            start = date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
        except ValueError:
            return None
        return start, start + timedelta(days=6)
    return None


def check_metrics_folder(lint, folder, name):
    """metrics/<period>.yaml must be PLACEABLE ON A TIMELINE.

    See protocols/metrics-publication.md. The failure this prevents is silent:
    a consumer that cannot bucket a file drops the period and reports it
    unavailable, while the publisher sees a green run and a file on main.
    """
    mdir = folder / "metrics"
    if not mdir.is_dir():
        return
    for f in sorted(mdir.glob("*.yaml")):
        text = f.read_text(encoding="utf-8", errors="replace")
        meta, _ = parse_front_matter(lint, f, text)
        period = f.stem
        bounds = period_bounds(period)
        if bounds is None:
            lint.add("metrics-schema", f, 1, f"filename `{f.name}` is not a period id (YYYY-MM or YYYY-Www)")
            continue
        start, end = bounds
        for k in REQUIRED_METRIC_ENVELOPE:
            if k not in meta:
                lint.add("metrics-schema", f, 1, f"envelope missing required key `{k}`")
        if meta.get("owner") and meta["owner"] != name:
            lint.add("ownership", f, 1, f"owner `{meta['owner']}` != folder `{name}`")
        if meta.get("period") and meta["period"] != period:
            lint.add("metrics-schema", f, 1, f"`period: {meta['period']}` disagrees with filename `{f.name}`")

        expected = f"{start.isoformat()}..{end.isoformat()}"
        win = meta.get("window")
        if win and win != expected:
            lint.add("metrics-schema", f, 1, f"`window: {win}` is not the span of `{period}` ({expected})")

        # every metric leaf carries as_of + window, and as_of sits INSIDE the window
        for i, line in enumerate(text.splitlines(), 1):
            m = METRIC_LEAF_RE.match(line)
            if not m:
                continue
            leaf, body = m.group(1), m.group(2)
            as_of = re.search(r"as_of:\s*(\d{4}-\d{2}-\d{2})", body)
            if not as_of:
                lint.add("metrics-schema", f, i, f"metric `{leaf}` has no `as_of`")
                continue
            lw = re.search(r"window:\s*(\d{4}-\d{2}-\d{2}\.\.\d{4}-\d{2}-\d{2})", body)
            if not lw:
                lint.add("metrics-schema", f, i, f"metric `{leaf}` has no `window` — an `as_of` alone is not placeable")
            lo, hi = (lw.group(1).split("..") if lw else (start.isoformat(), end.isoformat()))
            if not lo <= as_of.group(1) <= hi:
                lint.add("metrics-schema", f, i,
                         f"metric `{leaf}` `as_of: {as_of.group(1)}` falls outside its window {lo}..{hi} — "
                         f"as_of is the date the measurement REFERS to; put the publish date in `updated:`")


def lint_projects(lint, folder, name):
    """projects/<slug>/ — a shared (company) project.

    Two placements, one rule. `folder` is the repo root for the top-level zone (R35, `name`
    None — everyone writes there, so `owner` is provenance, not a folder match), or an
    `agents/<name>/` folder for the legacy R21 placement (`owner` must equal `name`, the
    own-folder rule that placement lived under). Projects move from the second to the first
    one at a time (Tandem: ent#585); the rule reads both until the last one has moved.

    Only two files are linted, both by front matter alone: `project.md` (REQUIRED — the
    charter, mirroring the registry epic) and `decisions.md` (optional — the append-only
    ledger). Everything else in the slug folder is the project's workspace and is never
    read, exactly as `project_files/<slug>/` is free-form at agent level.
    """
    projects_dir = folder / "projects"
    if not projects_dir.is_dir():
        return
    for entry in sorted(projects_dir.iterdir()):
        if entry.name.startswith("."):
            continue
        if not entry.is_dir():
            lint.add("layout", entry, 0, f"unexpected file `{entry.name}` directly under projects/ — every project is a `projects/<slug>/` folder")
            continue
        slug = entry.name
        charter = entry / "project.md"
        if not charter.is_file():
            lint.add("project-envelope", charter, 0, f"project.md missing — every projects/<slug>/ needs its charter (owner, status, epic, updated, review_by, tldr)")
        else:
            lint.counts["docs"] += 1
            meta, _ = parse_front_matter(lint, charter, charter.read_text(encoding="utf-8", errors="replace"))
            for k in REQUIRED_PROJECT_KEYS:
                if k not in meta:
                    lint.add("project-envelope", charter, 1, f"missing required charter key `{k}`")
            status = meta.get("status")
            if status and status not in PROJECT_STATUS_VOCAB:
                lint.add("project-envelope", charter, 1, f"status `{status}` not in {list(PROJECT_STATUS_VOCAB)} (mirrors the registry epic's status:* label)")
            if meta.get("epic") and not EPIC_RE.match(meta["epic"]):
                lint.add("project-envelope", charter, 1, f"epic `{meta['epic']}` must be the registry epic as `owner/repo#N`")
            if name and meta.get("owner") and meta["owner"] != name:
                lint.add("ownership", charter, 1, f"owner `{meta['owner']}` != folder `{name}` — a legacy agents/<name>/projects/ charter is owned by that agent (top-level projects/ has no folder rule, R35)")
            for field in ("updated", "review_by"):
                if field in meta and valid_date(meta.get(field)) is None:
                    lint.add("project-envelope", charter, 1, f"`{field}: {meta.get(field)}` is not a valid YYYY-MM-DD date")
            due = valid_date(meta.get("review_by", ""))
            if status not in PROJECT_STALENESS_EXEMPT and due is not None and due < lint.today:
                lint.add("staleness", charter, 1, f"project `{slug}` charter past review_by {meta['review_by']} — verify against the epic and re-stamp (canon-reconcile)")
        ledger = entry / "decisions.md"
        if ledger.is_file():
            lint.counts["docs"] += 1
            meta, _ = parse_front_matter(lint, ledger, ledger.read_text(encoding="utf-8", errors="replace"))
            for k in REQUIRED_LEDGER_KEYS:
                if k not in meta:
                    lint.add("project-envelope", ledger, 1, f"missing required ledger key `{k}`")
            if meta.get("status") and meta["status"] not in STATUS_VOCAB:
                lint.add("project-envelope", ledger, 1, f"status `{meta['status']}` not in {list(STATUS_VOCAB)}")
            if name and meta.get("owner") and meta["owner"] != name:
                lint.add("ownership", ledger, 1, f"owner `{meta['owner']}` != folder `{name}`")
            if "updated" in meta and valid_date(meta.get("updated")) is None:
                lint.add("project-envelope", ledger, 1, f"`updated: {meta.get('updated')}` is not a valid YYYY-MM-DD date")
            # No staleness arm: the ledger is append-only and never re-stamped (its review date is the charter's).


def lint_folder(lint, repo, folder):
    name = folder.name
    lint.counts["folders"] += 1

    # ---- layout ----
    for entry in sorted(folder.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.name not in ALLOWED_TOP:
            lint.add("layout", entry, 0, f"unexpected entry `{entry.name}` — schema allows: profile.md, facts.yaml, docs/, files/, metrics/, projects/ (legacy, R21), NEEDS-REVIEW.md, sot_mirror/ (corbin only)")

    # ---- metrics/ (timeline zone) ----
    check_metrics_folder(lint, folder, name)

    # ---- profile.md (envelope + reachability root) ----
    profile = folder / "profile.md"
    profile_meta, profile_body = {}, ""
    if not profile.is_file():
        lint.add("envelope", profile, 0, "profile.md missing — every folder needs its index/identity doc")
    else:
        lint.counts["docs"] += 1
        profile_meta, profile_body = parse_front_matter(lint, profile, profile.read_text(encoding="utf-8", errors="replace"))
        for k in REQUIRED_DOC_KEYS:
            if k not in profile_meta:
                lint.add("envelope", profile, 1, f"missing required front-matter key `{k}`")
        if profile_meta.get("status") and profile_meta["status"] not in STATUS_VOCAB:
            lint.add("envelope", profile, 1, f"status `{profile_meta['status']}` not in {list(STATUS_VOCAB)}")
        elif profile_meta.get("status") not in (None, "canonical"):
            lint.add("envelope", profile, 1, "profile.md must be `status: canonical` — it is the folder's index")
        if profile_meta.get("owner") and profile_meta["owner"] != name:
            lint.add("ownership", profile, 1, f"owner `{profile_meta['owner']}` != folder `{name}`")
        check_dates_and_staleness(lint, profile, 1, profile_meta, profile_meta.get("status"), "doc")

    # ---- docs/ (envelope zone) ----
    docs_meta = {}
    docs_dir = folder / "docs"
    doc_bodies = []
    if docs_dir.is_dir():
        for doc in sorted(docs_dir.rglob("*.md")):
            lint.counts["docs"] += 1
            meta, body = parse_front_matter(lint, doc, doc.read_text(encoding="utf-8", errors="replace"))
            docs_meta[doc] = meta
            doc_bodies.append(body)
            for k in REQUIRED_DOC_KEYS:
                if k not in meta:
                    lint.add("envelope", doc, 1, f"missing required front-matter key `{k}`")
            if meta.get("status") and meta["status"] not in STATUS_VOCAB:
                lint.add("envelope", doc, 1, f"status `{meta['status']}` not in {list(STATUS_VOCAB)}")
            if meta.get("owner") and meta["owner"] != name:
                lint.add("ownership", doc, 1, f"owner `{meta['owner']}` != folder `{name}`")
            check_dates_and_staleness(lint, doc, 1, meta, meta.get("status"), "doc")

    # ---- facts.yaml (fully lintable zone) ----
    facts_path = folder / "facts.yaml"
    facts = []
    if not facts_path.is_file():
        lint.add("fact-schema", facts_path, 0, "facts.yaml missing — seed it with `facts: []`")
    else:
        facts = parse_facts(lint, facts_path, facts_path.read_text(encoding="utf-8", errors="replace"))
        for f in facts:
            lint.counts["facts"] += 1
            line = f["__line"]
            for k in REQUIRED_FACT_KEYS:
                if k not in f:
                    lint.add("fact-schema", facts_path, line, f"entry missing required field `{k}`")
            status = f.get("status")
            if status and status not in STATUS_VOCAB:
                lint.add("fact-schema", facts_path, line, f"status `{status}` not in {list(STATUS_VOCAB)}")
            if f.get("key") and not KEY_RE.match(f["key"]):
                lint.add("key-grammar", facts_path, line, f"key `{f['key']}` must be lowercase dotted `subject.relation` ([a-z0-9-] segments)")
            check_dates_and_staleness(lint, facts_path, line, f, status, f"fact `{f.get('key', '?')}`")
            src = f.get("source", "")
            if src.startswith(("docs/", "files/", "./")):
                if not (folder / src.lstrip("./")).is_file():
                    lint.add("source-resolution", facts_path, line, f"source `{src}` does not exist in agents/{name}/")
            # http(s):// and external refs (workspace paths, APIs, "manual") pass here —
            # verifying them against reality is /canon-reconcile's job, not the linter's.

    # ---- projects/ (shared-project charters — envelope only, body never read) ----
    lint_projects(lint, folder, name)

    # ---- reachability ----
    linked = set()
    for target in LINK_RE.findall(profile_body):
        target = target.split("#", 1)[0]
        if not target or "://" in target or target.startswith("/"):
            continue
        linked.add(target.lstrip("./"))
    for doc, meta in docs_meta.items():
        rel = doc.relative_to(folder).as_posix()
        status = meta.get("status")
        if status == "canonical" and rel not in linked:
            lint.add("reachability", doc, 1, f"canonical doc not linked from profile.md — add it to the index")
        if status == "draft" and rel in linked:
            lint.add("reachability", profile, 1, f"draft `{rel}` linked from profile.md — drafts must not be reachable (ideas can't dress as canon)")

    files_dir = folder / "files"
    if files_dir.is_dir():
        referenced_text = "\n".join([profile_body] + doc_bodies + [
            (f.get("source", "") + "\n" + f.get("value", "")) for f in facts
        ])
        for artifact in sorted(files_dir.rglob("*")):
            if artifact.is_dir() or artifact.name.startswith("."):
                continue
            rel = artifact.relative_to(folder).as_posix()
            if rel not in referenced_text:
                lint.add("reachability", artifact, 0, f"orphan artifact — `{rel}` is referenced by no doc, profile, or fact")

    return [
        {"key": f["key"], "status": f.get("status", ""), "path": facts_path, "line": f["__line"], "folder": name}
        for f in facts if f.get("key")
    ]


# ---------------------------------------------------------------------------
# The top level: domains.yaml, roles/<id>.yaml, objectives/<id>.yaml
#
# These are the files the fleet DECIDES on (CONVENTIONS.md § "Top-level files:
# the map, roles, objectives", ruled with R44), and until now not one lint rule
# could see them. They use the restricted grammar one level deeper: flat
# scalars, lists of bare scalars, and one level of list-of-maps whose values are
# scalars or scalar lists. Nothing nests further, so a zero-dependency parser
# reads them exactly — the same bargain facts.yaml makes.
#
# Every rule here lands at `warn` except `objective-metric-name`: the roles and
# objectives are `file_status: draft` / `provenance: ai-inferred` pending
# Eugene's per-objective ruling (R42), and a draft that is correctly a draft must
# not turn CI red. They ratchet to `fail` once the set is ruled — one line in
# lint/rules.yaml, no code change.
# ---------------------------------------------------------------------------

# Root entries the repo schema allows (dotfiles are skipped; `projects/` is R35's
# shared zone, linted by lint_projects).
ALLOWED_ROOT = {
    "CODEOWNERS", "CONVENTIONS.md", "README.md", "LICENSE",
    "agents", "domains", "domains.yaml", "lint", "objectives", "projects",
    "protocols", "roles", "tools",
}
# The envelope every top-level file carries. `verified:` is the stamp
# /canon-reconcile moves. This zone spells the envelope status `file_status:`
# because the files also carry a domain `status:` of their own (a role is
# active/vacant, an objective active/achieved/dropped).
TOP_ENVELOPE_KEYS = ("owner", "updated", "verified", "file_status", "schema_version", "source")
FILE_STATUS_VOCAB = ("canonical", "draft", "superseded")
# The metric registry's name class — NOT the objective reader's wider id class.
# `services/template_metrics.py` gates `template.yaml metrics:` with this regex and
# `metric_points_service` gates record_metrics with the same compiled copy, while the
# objective reader's id regex also admits dots, dashes and capitals. A dotted name
# therefore parses everywhere an id is read, can never be declared and can never be
# recorded: it reads `declared: false` forever with no finding that says why
# (ent#730's note; the docs half is abilityai/trinity#3121). The canon is the only
# place the mismatch can be caught before a whole map is designed around it.
METRIC_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ROLE_REF_RE = re.compile(r"^role:[a-z0-9]+(-[a-z0-9]+)*$")
DIRECTION_VOCAB = ("up", "down", "hold")
HORIZON_VOCAB = ("day", "week", "month", "quarter", "year")
ROLE_STATUS_VOCAB = ("active", "vacant")
OBJECTIVE_STATUS_VOCAB = ("active", "achieved", "dropped")
DECISION_RIGHTS_VOCAB = ("decides", "recommends", "executes", "informed")
FRESHNESS_MAX_DAYS = 30


def _flow_list(raw):
    """`[a, b, c]` -> ['a','b','c']; `[]` -> []. Bare scalar items only (C7)."""
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    return [unquoted(part)[0] for part in inner.split(",") if part.strip()]


def parse_structured(lint, rule, path, text):
    """Parse one top-level file in the extended restricted grammar.

    Returns (data, where): `data` maps key -> scalar (str | None), list of
    scalars, or list of maps whose values are scalars / scalar lists; `where`
    maps key -> 1-based line for findings, and each map item carries `__line`.
    Grammar violations report under `rule` — a file the linter cannot read is a
    schema finding, never a silent pass.
    """
    lines = text.splitlines()
    n = len(lines)

    def split_kv(s):
        """`key: <raw>` -> (key, raw text, error). Unlike parse_kv the value is
        returned RAW (quotes intact): the quoting check belongs to read_scalar,
        which sees the whole folded value, and `key: ''` must stay a value."""
        m = KV_RE.match(s)
        if not m:
            return None, None, "not a `key: value` line (restricted grammar)"
        return m.group(1), (m.group(2) or "").strip(), None

    def blank(i):
        s = lines[i].strip()
        return not s or s.startswith("#")

    def ind(i):
        return len(lines[i]) - len(lines[i].lstrip(" "))

    def nxt(i):
        while i < n and blank(i):
            i += 1
        return i

    def is_dash(i):
        return lines[i].strip().startswith("- ") or lines[i].strip() == "-"

    def read_scalar(i, base, raw):
        """`raw` is the text after `key:` on line i. Returns (value, next line)."""
        raw = raw.strip()
        if raw in ("|", ">", "|-", ">-"):
            body, j = [], i + 1
            while j < n and (not lines[j].strip() or ind(j) > base):
                body.append(lines[j].strip())
                j += 1
            return "\n".join(body).strip(), j
        parts, j = [], i + 1
        while j < n:
            if blank(j):
                j += 1
                continue
            if ind(j) <= base:
                break
            parts.append(lines[j].strip())
            j += 1
        logical = " ".join([raw] + parts) if parts else raw
        if logical.startswith("["):
            if not logical.endswith("]"):
                lint.add(rule, path, i + 1, "unterminated flow list `[...]`")
                return [], j
            return _flow_list(logical), j
        value, quoted = unquoted(logical)
        if quoted and logical.lstrip().startswith("'"):
            value = value.replace("''", "'")   # YAML's single-quote escape
        if not quoted and ": " in logical:
            lint.add(rule, path, i + 1, "value contains ': ' and must be quoted to stay valid YAML")
        if not quoted and value in ("null", "~", ""):
            return None, j
        return value, j

    def read_block_list(i, base):
        """A block list whose dashes sit at `base` or one step deeper.

        Each item is a bare scalar (an id, a name, a line of prose) or a map
        (`- key: value` with its keys aligned under the dash). The two are told
        apart by the head of the item, exactly as YAML tells them apart.
        """
        items, j = [], nxt(i)
        while j < n and ind(j) in (base, base + 2) and is_dash(j):
            head = lines[j].strip()[1:].strip()
            if ":" in head and split_kv(head)[0] is not None:
                item, j = read_map_item(j)
            else:
                item, j = read_scalar(j, ind(j), head)
            items.append(item)
            j = nxt(j)
        return items, j

    def read_nested_map(i, base):
        """A map of scalars one step past the one-level grammar.

        C7 allows a list item's values to be scalars or flow lists, never another
        map — but a file can carry one anyway (`scoring:` in roles/agent-ops.yaml).
        Parsing it keeps the REST of the file readable instead of cascading one
        finding per line, and the single finding puts the choice where it belongs:
        flatten the keys, or amend the grammar. The linter does not decide that.
        """
        nested, j = {}, nxt(i)
        while j < n and ind(j) == base and not is_dash(j):
            key, raw, err = split_kv(lines[j].strip())
            if key is None:
                lint.add(rule, path, j + 1, err or "not a `key: value` line")
                j = nxt(j + 1)
                continue
            if raw:
                nested[key], j = read_scalar(j, base, raw)
            else:
                nested[key], j = read_block_list(j + 1, base)
            j = nxt(j)
        return nested, j

    def assign(target, key, raw, i, base):
        if key in target:
            lint.add(rule, path, i + 1, f"duplicate field `{key}`")
        if raw:
            target[key], j = read_scalar(i, base, raw)
            return j
        items, j = read_block_list(i + 1, base)
        if not items:
            probe = nxt(i + 1)
            if probe < n and ind(probe) > base and not is_dash(probe) and split_kv(lines[probe].strip())[0] is not None:
                lint.add(rule, path, i + 1,
                         f"`{key}` is a map inside a list item — the restricted grammar stops at one "
                         "level (item values are scalars or lists of scalars). Flatten it "
                         f"(`{key}_<subkey>: value`) or amend the grammar in CONVENTIONS")
                target[key], j = read_nested_map(probe, ind(probe))
                return j
        target[key] = items
        return j

    def read_map_item(i):
        """One `- key: value` item; the item's keys align one step in from the dash."""
        base = ind(i) + 2
        item = {"__line": i + 1}
        key, raw, err = split_kv(lines[i].strip()[1:].strip())
        if key is None:
            lint.add(rule, path, i + 1, err or "not a `key: value` line in a list item")
            return item, i + 1
        j = assign(item, key, raw, i, base)
        while True:
            j = nxt(j)
            if j >= n or ind(j) != base or is_dash(j):
                break
            key, raw, err = split_kv(lines[j].strip())
            if key is None:
                lint.add(rule, path, j + 1, err or "not a `key: value` line in a list item")
                j += 1
                continue
            j = assign(item, key, raw, j, base)
        return item, j

    data, where, i = {}, {}, 0
    while i < n:
        if blank(i):
            i += 1
            continue
        if ind(i) != 0:
            lint.add(rule, path, i + 1, "unexpected indentation at the top level (restricted grammar: flat scalars, flow lists, one level of list items)")
            i += 1
            continue
        if is_dash(i):
            lint.add(rule, path, i + 1, "list item `- ` outside any key")
            i += 1
            continue
        key, raw, err = split_kv(lines[i].strip())
        if key is None:
            lint.add(rule, path, i + 1, err or "not a `key: value` line")
            i += 1
            continue
        if key in data:
            lint.add(rule, path, i + 1, f"duplicate key `{key}`")
        where[key] = i + 1
        if raw:
            data[key], i = read_scalar(i, 0, raw)
            continue
        # `key:` with no value — a block list, a nested map, or empty
        items, j = read_block_list(i + 1, 0)
        if not items:
            probe = nxt(i + 1)
            if probe < n and ind(probe) > 0 and not is_dash(probe) and split_kv(lines[probe].strip())[0] is not None:
                lint.add(rule, path, i + 1,
                         f"`{key}` is a nested map — the restricted grammar is flat scalars, flow "
                         "lists and one level of list items. Flatten it or amend the grammar in "
                         "CONVENTIONS")
                data[key], i = read_nested_map(probe, ind(probe))
                continue
        data[key] = items
        i = j
    return data, where


def check_top_envelope(lint, rule, path, data, where, valid_owners, label):
    """The shared envelope of every top-level file: keys, dates, owner, staleness."""
    for k in TOP_ENVELOPE_KEYS:
        if k not in data:
            lint.add(rule, path, 1, f"missing required envelope key `{k}`")
    if data.get("schema_version") not in (None, "1"):
        lint.add(rule, path, where.get("schema_version", 1), f"schema_version `{data['schema_version']}` — the grammar in CONVENTIONS is version 1")
    status = data.get("file_status")
    if status and status not in FILE_STATUS_VOCAB:
        lint.add(rule, path, where.get("file_status", 1), f"file_status `{status}` not in {list(FILE_STATUS_VOCAB)}")
    for field in ("updated", "verified", "review_by"):
        if data.get(field) is not None and valid_date(data[field]) is None:
            lint.add(rule, path, where.get(field, 1), f"`{field}: {data[field]}` is not a valid YYYY-MM-DD date")
    owner = data.get("owner")
    if owner:
        ref = ROLE_REF_RE.match(owner)
        if ref:
            # an objective is owned by a ROLE, never a person or an agent (R44)
            if owner[5:] not in valid_owners["roles"]:
                lint.add("ownership", path, where.get("owner", 1), f"owner `{owner}` does not resolve to roles/{owner[5:]}.yaml")
        elif owner not in valid_owners["agents"] and owner != "steward":
            lint.add("ownership", path, where.get("owner", 1), f"owner `{owner}` is neither an agents/<name>/ folder, a `role:<id>`, nor `steward`")
    due = valid_date(data.get("review_by") or "")
    if status == "canonical" and due is not None and due < lint.today:
        lint.add("staleness", path, where.get("review_by", 1), f"{label} past review_by {data['review_by']} — verify and re-stamp (canon-reconcile)")


def check_metric_entries(lint, path, entries, kind, agent_names):
    """`metrics:` / `guard_metrics:` list items — the shape both rules share.

    `objective-metric-name` is the one rule in this zone that ships `fail`: a name
    outside the registry's class cannot be declared or recorded in any state of the
    file, so a draft is no excuse. Everything else about the entry is `warn`.
    """
    rule = "guard-schema" if kind == "guard_metrics" else "objective-schema"
    for entry in entries:
        if not isinstance(entry, dict):
            lint.add(rule, path, 0, f"`{kind}` item is not a `- name: ...` map")
            continue
        line = entry.get("__line", 0)
        name = entry.get("name")
        if not name:
            lint.add(rule, path, line, f"`{kind}` item missing `name` (the declared metric name)")
        elif not METRIC_NAME_RE.match(name):
            lint.add("objective-metric-name", path, line,
                     f"metric `{name}` is not a declarable metric name — the registry requires "
                     "`^[a-z][a-z0-9_]{0,63}$` (lowercase, digits, underscores; no dots, dashes or "
                     "capitals). A name like this parses as an id but can never be declared in "
                     "template.yaml metrics: nor recorded (abilityai/trinity#3121)")
        direction = entry.get("direction")
        if direction not in DIRECTION_VOCAB:
            lint.add(rule, path, line, f"`direction: {direction}` not in {list(DIRECTION_VOCAB)}")
        if kind == "guard_metrics" and direction not in (None, "hold"):
            lint.add("guard-schema", path, line, f"a guard metric holds a level — `direction: {direction}` is not `hold`")
        for field in ("target", "served_by") if kind == "guard_metrics" else ("target", "by"):
            if field not in entry:
                lint.add(rule, path, line, f"`{kind}` item `{name or '?'}` missing `{field}` (state it, `null` when there is no number yet)")
        if entry.get("by") is not None and valid_date(entry["by"]) is None:
            lint.add(rule, path, line, f"`by: {entry['by']}` is not a valid YYYY-MM-DD date")
        served = entry.get("served_by")
        if served and served not in agent_names:
            lint.add("role-binding", path, line,
                     f"`served_by: {served}` names no agent this canon knows — use the deployed agent "
                     "name exactly (the `tom` vs `tom-marketing-operations-agent` class of mismatch "
                     "resolves to nothing, silently)")


def lint_top_level(lint, repo):
    """domains.yaml + roles/ + objectives/ — the CORE files R44 ruled.

    Returns nothing; every finding lands through `lint.add`. The known-agent set
    for `role-binding` is the union of the `agents/<name>/` folders and every
    owner/consumer named in domains.yaml, so an agent that is not canon-enrolled
    yet still resolves when the map states it (a `null` path with a `path_note`
    is the stated form — R7: stated, not faked).
    """
    agent_folders = {p.name for p in (repo / "agents").iterdir() if p.is_dir() and not p.name.startswith(".")}
    role_ids = {p.stem for p in sorted((repo / "roles").glob("*.yaml"))} if (repo / "roles").is_dir() else set()
    objective_ids = {p.stem for p in sorted((repo / "objectives").glob("*.yaml"))} if (repo / "objectives").is_dir() else set()

    # ---- top-level-layout ----
    domain_ids = set()
    map_path = repo / "domains.yaml"
    map_data, map_where = {}, {}
    if map_path.is_file():
        map_data, map_where = parse_structured(lint, "domain-schema", map_path, map_path.read_text(encoding="utf-8", errors="replace"))
        for entry in map_data.get("domains") or []:
            if isinstance(entry, dict) and entry.get("id"):
                domain_ids.add(entry["id"])
    else:
        lint.add("top-level-layout", map_path, 0, "domains.yaml missing — the domain map is the root of the top level (R44)")

    for entry in sorted(repo.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.name not in ALLOWED_ROOT:
            lint.add("top-level-layout", entry, 0, f"unexpected root entry `{entry.name}` — the schema allows: {', '.join(sorted(ALLOWED_ROOT))}")
    domains_dir = repo / "domains"
    if domains_dir.is_dir():
        for entry in sorted(domains_dir.iterdir()):
            if entry.name.startswith("."):
                continue
            if not entry.is_dir():
                lint.add("top-level-layout", entry, 0, f"unexpected file `{entry.name}` directly under domains/ — every entry is a `domains/<id>/` folder")
            elif entry.name not in domain_ids:
                lint.add("top-level-layout", entry, 0, f"`domains/{entry.name}/` matches no `id` in domains.yaml — the folder and the map name the same domain")

    known_agents = set(agent_folders)
    for entry in map_data.get("domains") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("owner") and entry["owner"] != "steward":
            known_agents.add(entry["owner"])
        for consumer in entry.get("consumers") or []:
            if consumer != "all":
                known_agents.add(consumer)
    valid_owners = {"agents": agent_folders | known_agents, "roles": role_ids}

    # ---- domain-schema ----
    if map_path.is_file():
        check_top_envelope(lint, "domain-schema", map_path, map_data, map_where, valid_owners, "the domain map")
        if map_data.get("steward") and map_data["steward"] not in known_agents:
            lint.add("domain-schema", map_path, map_where.get("steward", 1), f"steward `{map_data['steward']}` names no agent this canon knows")
        if "review_by" not in map_data:
            lint.add("domain-schema", map_path, 1, "missing `review_by` — the map itself is verified on a bound like every other canonical file")
        seen = set()
        for entry in map_data.get("domains") or []:
            if not isinstance(entry, dict):
                lint.add("domain-schema", map_path, 0, "`domains` item is not a `- id: ...` map")
                continue
            line, did = entry.get("__line", 0), entry.get("id")
            for field in ("id", "description", "owner", "path", "consumers", "freshness_days", "source"):
                if field not in entry:
                    lint.add("domain-schema", map_path, line, f"domain `{did or '?'}` missing `{field}`")
            if did:
                if not KEBAB_RE.match(did):
                    lint.add("domain-schema", map_path, line, f"domain id `{did}` must be lowercase kebab-case")
                if did in seen:
                    lint.add("domain-schema", map_path, line, f"domain id `{did}` declared twice — one entry per domain")
                seen.add(did)
            owner = entry.get("owner")
            if owner and owner != "steward" and owner not in known_agents:
                lint.add("role-binding", map_path, line, f"domain `{did}` owner `{owner}` is neither an `agents/<name>/` folder nor `steward`")
            path_value = entry.get("path")
            if path_value is None:
                # A null path is legal — the owner is not canon-enrolled yet. It must be
                # STATED, not faked: `path_note` says so in words (R7).
                if "path" in entry and not entry.get("path_note"):
                    lint.add("domain-schema", map_path, line, f"domain `{did}` has `path: null` and no `path_note` — an absent path is stated in words, never left blank")
            elif not (repo / path_value).exists():
                lint.add("source-resolution", map_path, line, f"domain `{did}` path `{path_value}` does not exist in the canon repo")
            prop = entry.get("propagation")
            if prop is not None and prop not in PROPAGATION_KINDS:
                lint.add("domain-schema", map_path, line, f"domain `{did}` propagation `{prop}` must be one of {', '.join(PROPAGATION_KINDS)}")
            excl = entry.get("exclude")
            if excl is not None:
                if not isinstance(excl, list) or not all(isinstance(x, str) and x for x in excl):
                    lint.add("domain-schema", map_path, line, f"domain `{did}` exclude must be a flow list of paths relative to its `path`")
                elif path_value:
                    for x in excl:
                        if not (repo / str(path_value).rstrip("/") / x).exists():
                            lint.add("source-resolution", map_path, line, f"domain `{did}` exclude `{x}` does not exist under `{path_value}`")
            fresh = entry.get("freshness_days")
            if fresh is not None:
                if not re.match(r"^\d+$", str(fresh)):
                    lint.add("domain-schema", map_path, line, f"domain `{did}` freshness_days `{fresh}` is not an integer")
                elif int(fresh) > FRESHNESS_MAX_DAYS:
                    lint.add("domain-schema", map_path, line, f"domain `{did}` freshness_days {fresh} exceeds the {FRESHNESS_MAX_DAYS}-day bound CONVENTIONS sets")

    # ---- role-schema ----
    for role_path in sorted((repo / "roles").glob("*.yaml")) if (repo / "roles").is_dir() else []:
        data, where = parse_structured(lint, "role-schema", role_path, role_path.read_text(encoding="utf-8", errors="replace"))
        check_top_envelope(lint, "role-schema", role_path, data, where, valid_owners, f"role `{role_path.stem}`")
        if data.get("id") != role_path.stem:
            lint.add("role-schema", role_path, where.get("id", 1), f"`id: {data.get('id')}` must equal the file name `{role_path.stem}`")
        for field in ("title", "family", "status", "mission", "review_by"):
            if field not in data:
                lint.add("role-schema", role_path, 1, f"missing required field `{field}`")
        status = data.get("status")
        if status and status not in ROLE_STATUS_VOCAB:
            lint.add("role-schema", role_path, where.get("status", 1), f"`status: {status}` not in {list(ROLE_STATUS_VOCAB)}")
        covering = data.get("covering_role") or data.get("defaults_to")
        if status == "vacant" and not covering:
            lint.add("role-schema", role_path, 1, "a `vacant` role names the role that covers it (`defaults_to` / `covering_role`) — a seat nobody covers is a silent gap")
        for field in ("defaults_to", "covering_role"):
            ref = data.get(field)
            if ref and ref not in role_ids:
                lint.add("role-schema", role_path, where.get(field, 1), f"`{field}: {ref}` does not resolve to roles/{ref}.yaml")
        for agent in data.get("supporting_agents") or []:
            if agent not in known_agents:
                lint.add("role-binding", role_path, where.get("supporting_agents", 1), f"`supporting_agents` names `{agent}`, which is no agent this canon knows — use the deployed agent name exactly")
        for obj in data.get("objectives") or []:
            if obj not in objective_ids:
                lint.add("role-schema", role_path, where.get("objectives", 1), f"`objectives` names `{obj}`, which does not resolve to objectives/{obj}.yaml")
        for domain in (data.get("inputs") or []) + (data.get("outputs") or []):
            if domain not in domain_ids:
                lint.add("role-schema", role_path, 1, f"`inputs`/`outputs` names domain `{domain}`, which is no `id` in domains.yaml")
        for resp in data.get("responsibilities") or []:
            if not isinstance(resp, dict):
                lint.add("role-schema", role_path, 0, "`responsibilities` item is not a `- id: ...` map")
                continue
            line = resp.get("__line", 0)
            for field in ("id", "statement", "decision_rights"):
                if field not in resp:
                    lint.add("role-schema", role_path, line, f"responsibility `{resp.get('id', '?')}` missing `{field}`")
            rights = resp.get("decision_rights")
            if rights and rights not in DECISION_RIGHTS_VOCAB:
                lint.add("role-schema", role_path, line, f"`decision_rights: {rights}` not in {list(DECISION_RIGHTS_VOCAB)}")
            for metric in resp.get("metrics") or []:
                if not METRIC_NAME_RE.match(metric):
                    lint.add("objective-metric-name", role_path, line, f"metric `{metric}` is not a declarable metric name — the registry requires `^[a-z][a-z0-9_]{{0,63}}$` (no dots, dashes or capitals)")
            for ref in (resp.get("consulted") or []) + (resp.get("informed") or []):
                # `all` = every role, the same meaning the map gives it for consumers
                if ref != "all" and ref not in role_ids:
                    lint.add("role-schema", role_path, line, f"responsibility `{resp.get('id', '?')}` names role `{ref}` in consulted/informed, which does not resolve to roles/{ref}.yaml")

    # ---- objective-schema ----
    for obj_path in sorted((repo / "objectives").glob("*.yaml")) if (repo / "objectives").is_dir() else []:
        data, where = parse_structured(lint, "objective-schema", obj_path, obj_path.read_text(encoding="utf-8", errors="replace"))
        check_top_envelope(lint, "objective-schema", obj_path, data, where, valid_owners, f"objective `{obj_path.stem}`")
        if data.get("id") != obj_path.stem:
            lint.add("objective-schema", obj_path, where.get("id", 1), f"`id: {data.get('id')}` must equal the file name `{obj_path.stem}`")
        for field in ("statement", "horizon", "status", "review_by"):
            if field not in data:
                lint.add("objective-schema", obj_path, 1, f"missing required field `{field}`")
        if data.get("horizon") and data["horizon"] not in HORIZON_VOCAB:
            lint.add("objective-schema", obj_path, where.get("horizon", 1), f"`horizon: {data['horizon']}` not in {list(HORIZON_VOCAB)}")
        if data.get("status") and data["status"] not in OBJECTIVE_STATUS_VOCAB:
            lint.add("objective-schema", obj_path, where.get("status", 1), f"`status: {data['status']}` not in {list(OBJECTIVE_STATUS_VOCAB)}")
        owner = data.get("owner")
        if owner and not ROLE_REF_RE.match(owner):
            lint.add("objective-schema", obj_path, where.get("owner", 1), f"`owner: {owner}` must be `role:<role-id>` — an objective is owned by a seat, never by a person or an agent (R44)")
        for agent in data.get("supporting_agents") or []:
            if agent not in known_agents:
                lint.add("role-binding", obj_path, where.get("supporting_agents", 1), f"`supporting_agents` names `{agent}`, which is no agent this canon knows — use the deployed agent name exactly")
        metrics = data.get("metrics") or []
        if not metrics:
            lint.add("objective-schema", obj_path, 1, "no `metrics:` — an objective with no metric cannot be measured, and the brief has nothing to read")
        check_metric_entries(lint, obj_path, metrics, "metrics", known_agents)
        check_metric_entries(lint, obj_path, data.get("guard_metrics") or [], "guard_metrics", known_agents)


PROPAGATION_KINDS = ("copied", "live")   # copied: consumers keep a derived copy, so a change must reach them; live: read at use, never stale

SHA_TOKEN_RE = re.compile(r"@([0-9a-f]{7,40})\b")


def mirror_anchor(repo, domain_path):
    """source_sha of the nearest MIRROR.yaml at or above a domain's path, or (None, None).

    Only mirrored domains have a machine-readable anchor today (sot_mirror/MIRROR.yaml);
    a domain without one is outside this rule until its owner publishes an anchor.
    """
    if not domain_path:
        return None, None
    cur = (repo / domain_path.rstrip("/"))
    for cand in [cur] + list(cur.parents):
        try:
            cand.relative_to(repo)
        except ValueError:
            break
        mirror = cand / "MIRROR.yaml" if cand.is_dir() else None
        if mirror and mirror.is_file():
            for raw in mirror.read_text(encoding="utf-8", errors="replace").splitlines():
                key, value, err = parse_kv(raw.strip())
                if not err and key == "source_sha" and value:
                    return value.strip().strip("'\""), mirror
            return None, mirror
        if cand == repo:
            break
    return None, None


def native_anchor(facts, domain_id):
    """Anchor of a canon-native domain: the first `<repo>@<sha>` in the owner's
    non-superseded `<domain-id>.anchor` fact, or None. The owner moves the anchor by
    editing one fact in its own folder — no mirror, no second file."""
    for f in facts or []:
        if f.get("key") == f"{domain_id}.anchor" and f.get("status") != "superseded":
            shas = SHA_TOKEN_RE.findall(str(f.get("value", "")))
            if shas:
                return shas[0]
    return None


def lint_consumer_anchors(lint, repo):
    """consumer-anchor: a consumer listed for an anchored domain proves it rebuilt from the
    current anchor.

    A domain is anchored one of two ways: its `path` sits under a MIRROR.yaml (the mirror's
    source_sha), or — a canon-native domain — its owner publishes a `<domain-id>.anchor`
    fact whose value starts `<repo>@<sha>`. A domain with neither is outside this rule.

    For each anchored domains.yaml entry, every consumer
    (except `all`) must carry, in ITS OWN facts.yaml, at least one non-superseded fact
    `consumes.<domain>.<consumer>` or `consumes.<domain>.<consumer>-<surface>`, and every
    such fact must cite the mirror's source_sha (`<repo>@<sha>`, 7+ hex, prefix match).
    Matching is by owning folder + key prefix, never by parsing the suffix, so hyphenated
    agent names stay unambiguous. One finding per behind consumer, plus a roll-up behind-list
    per domain. Value status (at | due | nothing-derived) is reported, not judged: a `due`
    stamp at the current sha is current — the consumer knows, the work is tracked.
    """
    map_path = repo / "domains.yaml"
    if not map_path.is_file():
        return
    scratch = Lint({}, lint.today)   # parse without double-reporting schema findings
    data, _ = parse_structured(scratch, "domain-schema", map_path, map_path.read_text(encoding="utf-8", errors="replace"))
    facts_cache = {}

    def facts_of(agent):
        if agent not in facts_cache:
            fp = repo / "agents" / agent / "facts.yaml"
            facts_cache[agent] = parse_facts(scratch, fp, fp.read_text(encoding="utf-8", errors="replace")) if fp.is_file() else None
        return facts_cache[agent]

    for entry in data.get("domains") or []:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        did, line = entry["id"], entry.get("__line", 0)
        anchor, mirror = mirror_anchor(repo, entry.get("path"))
        anchor_home = f"{mirror.relative_to(repo)} source_sha" if anchor else None
        if not anchor and entry.get("owner") and entry["owner"] != "steward":
            anchor = native_anchor(facts_of(entry["owner"]), did)
            anchor_home = f"agents/{entry['owner']}/facts.yaml `{did}.anchor`"
        if not anchor:
            if entry.get("propagation") == "copied":
                lint.add("unanchored-domain", map_path, line,
                         f"domain `{did}` is `propagation: copied` but has no anchor (no MIRROR.yaml above its path, no `{did}.anchor` fact"
                         f"{' in agents/' + entry['owner'] + '/facts.yaml' if entry.get('owner') and entry['owner'] != 'steward' else ''}) — "
                         "consumers cannot be told they are behind; the owner's next /canon-publish seeds it")
            continue
        behind = []
        for consumer in entry.get("consumers") or []:
            if consumer == "all":
                continue
            facts = facts_of(consumer)
            prefix = f"consumes.{did}.{consumer}"
            if facts is None:
                behind.append(f"{consumer} (no canon folder)")
                lint.add("consumer-anchor", map_path, line, f"domain `{did}`: consumer `{consumer}` has no agents/{consumer}/facts.yaml — it cannot stamp `{prefix}`")
                continue
            stamps = [f for f in facts if f.get("status") != "superseded"
                      and (f.get("key") == prefix or str(f.get("key", "")).startswith(prefix + "-"))]
            if not stamps:
                behind.append(f"{consumer} (no stamp)")
                lint.add("consumer-anchor", repo / "agents" / consumer / "facts.yaml", 0, f"domain `{did}`: no `{prefix}[-<surface>]` fact — consumer has not recorded what it rebuilt from {anchor[:7]}")
                continue
            for f in stamps:
                shas = SHA_TOKEN_RE.findall(str(f.get("value", "")))
                if not any(anchor.startswith(s) or s.startswith(anchor) for s in shas):
                    cited = ", ".join(s[:7] for s in shas) or "no <repo>@<sha>"
                    behind.append(f"{consumer} ({f.get('key')} @ {cited})")
                    lint.add("consumer-anchor", repo / "agents" / consumer / "facts.yaml", f.get("__line", 0), f"`{f.get('key')}` cites {cited}; {anchor_home} is {anchor[:7]} — rebuilt from a superseded anchor")
        if behind:
            lint.add("consumer-anchor", map_path, line, f"domain `{did}` behind-list at {anchor[:7]}: {'; '.join(behind)}")


def _claims(prefix, key):
    return key == prefix or key.startswith(prefix + ".")


def lint_orphan_subjects(lint, repo, all_keys):
    """orphan-subject: every shared subject has a domain, and a domain's keys live with its owner.

    domains.yaml may give each domain `key_prefixes: [a, b.c]` — the fact-key prefixes it
    owns — and, at the top level, `local_key_prefixes: [...]` — subjects every agent states
    about ITSELF (its schedules, its consumes.* stamps), which are never a shared domain.

    Two findings, both about facts nobody decided to duplicate:
      * a subject (the key's first segment) published by 2+ folders that no domain and no
        local prefix claims — several agents each hold their own version of something and
        nobody owns the truth. Name an owner or mark it local.
      * a key under a domain's prefix homed in a folder that is neither the domain's owner
        nor the folder its `path` sits in — a consumer restating the owner's fact as its own.
    """
    map_path = repo / "domains.yaml"
    if not map_path.is_file():
        return
    scratch = Lint({}, lint.today)
    data, where = parse_structured(scratch, "domain-schema", map_path, map_path.read_text(encoding="utf-8", errors="replace"))
    local = [p for p in (data.get("local_key_prefixes") or []) if isinstance(p, str)]
    claims = []   # (prefix, domain id, allowed home folders, line)
    for entry in data.get("domains") or []:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        homes = set()
        if entry.get("owner") and entry["owner"] != "steward":
            homes.add(entry["owner"])
        parts = str(entry.get("path") or "").split("/")
        if len(parts) > 1 and parts[0] == "agents":
            homes.add(parts[1])
        for prefix in entry.get("key_prefixes") or []:
            if isinstance(prefix, str) and prefix:
                claims.append((prefix, entry["id"], homes, entry.get("__line", 0)))

    unclaimed = {}
    for e in all_keys:
        if e["status"] == "superseded":
            continue
        key = e["key"]
        if any(_claims(p, key) for p in local):
            continue
        owner_claims = [c for c in claims if _claims(c[0], key)]
        if owner_claims:
            prefix, did, homes, _ = max(owner_claims, key=lambda c: len(c[0]))
            if homes and e["folder"] not in homes:
                lint.add("orphan-subject", e["path"], e["line"],
                         f"key `{key}` sits under `{prefix}`, which domain `{did}` owns ({', '.join(sorted('agents/' + h + '/' for h in homes))}) — "
                         f"cite the owner's fact instead of restating it, or stamp what you derived as `consumes.{did}.{e['folder']}`")
            continue
        unclaimed.setdefault(key.split(".")[0], set()).add(e["folder"])
    for subject, folders in sorted(unclaimed.items()):
        if len(folders) > 1:
            lint.add("orphan-subject", map_path, where.get("domains", 1),
                     f"subject `{subject}.*` is published by {len(folders)} folders ({', '.join(sorted(folders))}) and no domain claims it — "
                     "add it to one domain's `key_prefixes` (it then has an owner and a consumer list) or to `local_key_prefixes` (each agent's own business)")


NOTICE_LIST_ITEM_RE = re.compile(r"""^\s+-\s+(?:"((?:[^"\\]|\\.)*)"|'((?:[^']|'')*)'|(.+?))\s*$""")
RETIRED_EXEMPT_KEY_PREFIXES = ("consumes.", "release-propagation.")


def load_retired_phrases(repo):
    """{phrase_lower: (phrase, run, notice path)} from every change notice's `retired_phrases`.

    Notices live at agents/<hub>/files/propagation/<run-id>.yaml (protocols/change-propagation.md
    §3). `files/` is never linted, so they are read here with a line reader, not the grammar."""
    out = {}
    for notice in sorted((repo / "agents").glob("*/files/propagation/*.yaml")):
        run, in_list = notice.stem, False
        for raw in notice.read_text(encoding="utf-8", errors="replace").splitlines():
            if raw and not raw.startswith((" ", "\t")):
                in_list = raw.strip() == "retired_phrases:"
                if raw.startswith("run:"):
                    run = raw.split(":", 1)[1].strip().strip("'\"") or run
                continue
            if in_list:
                m = NOTICE_LIST_ITEM_RE.match(raw)
                if m:
                    phrase = (m.group(1) or m.group(2) or m.group(3) or "").strip()
                    if len(phrase) >= 4:   # a 1-3 char "phrase" would match everything
                        out.setdefault(phrase.lower(), (phrase, run, notice))
    return out


def lint_retired_phrases(lint, repo):
    """retired-phrase: text a change notice retired must be gone from every folder.

    The stamp (`consumes.<domain>.<agent>`) proves a consumer RAN a rebuild; this rule
    checks the rebuild's result where a linter can see it — the canon folder. It reads
    profile.md, docs/*.md and the values of non-superseded facts. It does not read the
    stamps themselves (a stamp may quote the phrase it removed), `files/`, a mirror, or
    drafts. Literal, case-insensitive match; one finding per file and phrase.
    A hit on a line that is itself a warning ("never say X") is still a hit: reword the
    warning so the retired string is not sitting in the file for the next reader to lift.
    """
    phrases = load_retired_phrases(repo)
    if not phrases:
        return
    scratch = Lint({}, lint.today)
    for folder in sorted(p for p in (repo / "agents").iterdir() if p.is_dir() and not p.name.startswith(".")):
        targets = []   # (path, [(line, text)])
        docs = [folder / "profile.md"] + (sorted((folder / "docs").glob("*.md")) if (folder / "docs").is_dir() else [])
        for doc in docs:
            if not doc.is_file():
                continue
            text = doc.read_text(encoding="utf-8", errors="replace")
            if re.search(r"^status:\s*(draft|superseded)\s*$", text.split("\n---", 1)[0], re.M):
                continue
            targets.append((doc, list(enumerate(text.splitlines(), start=1))))
        fp = folder / "facts.yaml"
        if fp.is_file():
            rows = [(f.get("__line", 0), str(f.get("value", "")))
                    for f in parse_facts(scratch, fp, fp.read_text(encoding="utf-8", errors="replace"))
                    if f.get("status") != "superseded"
                    and not str(f.get("key", "")).startswith(RETIRED_EXEMPT_KEY_PREFIXES)]
            targets.append((fp, rows))
        for path, rows in targets:
            seen = set()
            for line, text in rows:
                low = text.lower()
                for key, (phrase, run, notice) in phrases.items():
                    if key in low and key not in seen:
                        seen.add(key)
                        lint.add("retired-phrase", path, line,
                                 f"still carries `{phrase}`, retired by run `{run}` ({notice.relative_to(repo)}) — rebuild the text; a stamp does not remove it")


# ---------------------------------------------------------------------------
# --changed-domains: the trigger half of change propagation (not a lint rule)
# ---------------------------------------------------------------------------

ANCHOR_VALUE_RE = re.compile(r"([A-Za-z0-9_.:/-]+?)@([0-9a-f]{7,40})\b")


def _git(repo, *args):
    import subprocess
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def _md_body(text):
    """A markdown file minus its front matter: an envelope re-stamp is not a content change."""
    if text.startswith("---\n"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def _fact_values(text, keep):
    scratch = Lint({}, date.today())
    return {(f.get("key"), str(f.get("value", ""))) for f in parse_facts(scratch, Path("facts.yaml"), text or "")
            if f.get("status") != "superseded" and keep(str(f.get("key", "")))}


def changed_domains(repo, base, scope):
    """Copied domains whose source lives in `scope` (one agent folder) and changed since `base`.

    A domain is in scope when its `path` sits inside the folder. Only `propagation: copied`
    domains count — a `live` domain is read at the moment of use and cannot go stale. A change
    is a change of CONTENT: a markdown body below its front matter, a file under a directory
    path, or a fact VALUE under the domain's `key_prefixes` (without prefixes: any fact in the
    path except the local subjects and anchors). Paths in the domain's `exclude:` (working logs
    that live beside the content consumers copy) never count. Re-stamping `updated:`/`review_by:`/`verified:`
    is never a change — the weekly reconcile does that, and it must not wake the fleet.

    Returns one dict per in-scope copied domain: id, changed, reasons, anchor kind
    (mirror | native | none), the anchor as `<repo>@<sha>`, whether the owner moved a native
    anchor in this range, whether that anchor names another repo (upstream: the owner moves
    it, never the publish skill), and for an unanchored domain the commit to seed it at.
    """
    scope = scope.strip("/")
    map_path = repo / "domains.yaml"
    if not map_path.is_file():
        return []
    scratch = Lint({}, date.today())
    data, _ = parse_structured(scratch, "domain-schema", map_path, map_path.read_text(encoding="utf-8", errors="replace"))
    local = tuple(p for p in (data.get("local_key_prefixes") or []) if isinstance(p, str))
    out = []
    for entry in data.get("domains") or []:
        if not isinstance(entry, dict) or not entry.get("id") or entry.get("propagation") != "copied":
            continue
        did, dpath = entry["id"], str(entry.get("path") or "").rstrip("/")
        if not dpath or not (dpath == scope or dpath.startswith(scope + "/")):
            continue
        prefixes = tuple(p for p in (entry.get("key_prefixes") or []) if isinstance(p, str) and p)
        skip = tuple(f"{dpath}/{x}" for x in (entry.get("exclude") or []) if isinstance(x, str) and x)

        def keep(key, prefixes=prefixes, did=did):
            if key == f"{did}.anchor" or key.endswith(".anchor") and not prefixes:
                return False
            if prefixes:
                return any(_claims(p, key) for p in prefixes)
            return not any(_claims(p, key) for p in local)

        reasons = []
        facts_rel = f"{scope}/facts.yaml"
        names = (_git(repo, "diff", "--name-only", base, "HEAD", "--", dpath) or "").split()
        if prefixes and facts_rel not in names:
            names += (_git(repo, "diff", "--name-only", base, "HEAD", "--", facts_rel) or "").split()
        for name in sorted(set(names)):
            if name.endswith("MIRROR.yaml") or any(name == x.rstrip("/") or name.startswith(x.rstrip("/") + "/") for x in skip):
                continue
            old = _git(repo, "show", f"{base}:{name}") or ""
            cur = (repo / name).read_text(encoding="utf-8", errors="replace") if (repo / name).is_file() else ""
            if name == facts_rel:
                if not prefixes and not (dpath == scope or facts_rel.startswith(dpath + "/")):
                    continue
                delta = _fact_values(old, keep) ^ _fact_values(cur, keep)
                if delta:
                    reasons.append(f"facts: {', '.join(sorted({k for k, _ in delta}))}")
            elif name.endswith(".md"):
                if _md_body(old).strip() != _md_body(cur).strip():
                    reasons.append(f"content: {name}")
            elif old != cur:
                reasons.append(f"content: {name}")

        kind, anchor, moved, upstream, seed = "none", None, False, False, None
        msha, mirror = mirror_anchor(repo, dpath)
        if msha:
            kind, anchor = "mirror", f"{entry.get('owner') or 'mirror'}@{msha}"
        else:
            owner_facts = repo / "agents" / scope.split("/")[-1] / "facts.yaml"
            def native_value(text):
                for f in parse_facts(scratch, owner_facts, text or ""):
                    if f.get("key") == f"{did}.anchor" and f.get("status") != "superseded":
                        m = ANCHOR_VALUE_RE.search(str(f.get("value", "")))
                        return f"{m.group(1)}@{m.group(2)}" if m else None
                return None
            cur_anchor = native_value(owner_facts.read_text(encoding="utf-8", errors="replace") if owner_facts.is_file() else "")
            old_anchor = native_value(_git(repo, "show", f"{base}:{facts_rel}") or "")
            if cur_anchor:
                kind, anchor = "native", cur_anchor
                moved = cur_anchor != old_anchor
                upstream = not cur_anchor.startswith("canon@")
                if moved:
                    reasons.append(f"anchor moved: {old_anchor or 'none'} -> {cur_anchor}")
            else:
                seed = (_git(repo, "log", "-1", "--format=%H", "--", dpath) or "").strip() or None
        out.append({"domain": did, "changed": bool(reasons), "reasons": reasons, "anchor_kind": kind,
                    "anchor": anchor, "anchor_moved": moved, "upstream": upstream, "seed_sha": seed})
    return out


def load_rules(lint_defaults, rules_path):
    severities = dict(lint_defaults)
    if rules_path is None or not rules_path.is_file():
        return severities, None
    in_rules = False
    for i, raw in enumerate(rules_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s == "rules:":
            in_rules = True
            continue
        if not raw.startswith((" ", "\t")):
            in_rules = False
        if in_rules:
            key, value, err = parse_kv(s)
            if err or key not in RULE_DEFAULTS or value not in ("fail", "warn", "off"):
                return None, f"{rules_path}:{i}: bad rule line `{s}` (known rules, values fail|warn|off)"
            severities[key] = value
    return severities, None


def main():
    ap = argparse.ArgumentParser(description="Deterministic canon repo linter")
    ap.add_argument("--repo", default=".", help="canon repo root (default: cwd)")
    ap.add_argument("--rules", default=None, help="rules.yaml path (default: <repo>/lint/rules.yaml)")
    ap.add_argument("--scope", default=None, help="report only findings under this folder, e.g. agents/corbin (cross-folder conflicts touching it included)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--today", default=None, help="override today's date (testing)")
    ap.add_argument("--baseline", default=None, help="JSON report to ratchet against: exit 1 only on failures NOT in it")
    ap.add_argument("--changed-domains", metavar="BASE", default=None,
                    help="not a lint: list the copied domains whose source lives in --scope and changed since commit BASE (the trigger /canon-publish reads)")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if args.changed_domains:
        if not args.scope:
            print("canon-lint: --changed-domains needs --scope agents/<name>", file=sys.stderr)
            return 2
        if _git(repo, "rev-parse", "--verify", f"{args.changed_domains}^{{commit}}") is None:
            print(f"canon-lint: --changed-domains `{args.changed_domains}` is not a commit in {repo}", file=sys.stderr)
            return 2
        rows = changed_domains(repo, args.changed_domains, args.scope)
        if args.format == "json":
            print(json.dumps(rows, indent=2))
        else:
            for r in rows:
                state = "CHANGED" if r["changed"] else "same"
                print(f"{state:7} {r['domain']}  anchor={r['anchor'] or '-'} ({r['anchor_kind']}{', upstream' if r['upstream'] else ''})"
                      + (f"  seed@{r['seed_sha'][:7]}" if r["seed_sha"] else "") + ("  — " + "; ".join(r["reasons"]) if r["reasons"] else ""))
        return 0
    agents_dir = repo / "agents"
    if not agents_dir.is_dir():
        print(f"canon-lint: no agents/ directory under {repo} — is this a canon repo?", file=sys.stderr)
        return 2
    today = valid_date(args.today) if args.today else date.today()
    if args.today and today is None:
        print(f"canon-lint: --today `{args.today}` is not YYYY-MM-DD", file=sys.stderr)
        return 2

    rules_path = Path(args.rules) if args.rules else repo / "lint" / "rules.yaml"
    severities, err = load_rules(RULE_DEFAULTS, rules_path)
    if err:
        print(f"canon-lint: {err}", file=sys.stderr)
        return 2

    baseline_keys = None
    if args.baseline:
        try:
            with open(args.baseline, encoding="utf-8") as fh:
                baseline_keys = {(f["rule"], f["path"], f["message"]) for f in json.load(fh)["findings"]}
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"canon-lint: --baseline `{args.baseline}` is not a canon-lint JSON report ({e})", file=sys.stderr)
            return 2

    lint = Lint(severities, today)
    all_keys = []
    for folder in sorted(p for p in agents_dir.iterdir() if p.is_dir()):
        all_keys.extend(lint_folder(lint, repo, folder))
    # ---- top-level projects/ (R35: the shared zone everyone reads and writes) ----
    lint_projects(lint, repo, None)
    # ---- the top level: domains.yaml, roles/, objectives/ (R44 CORE) ----
    lint_top_level(lint, repo)
    # ---- consumers of anchored domains (mirrored or canon-native) carry the current anchor ----
    lint_consumer_anchors(lint, repo)
    # ---- every shared subject has a domain; a domain's keys live with its owner ----
    lint_orphan_subjects(lint, repo, all_keys)
    # ---- what a change notice retired is gone from every folder ----
    lint_retired_phrases(lint, repo)

    # ---- one home per key (global index over non-superseded facts) ----
    index = {}
    for entry in all_keys:
        if entry["status"] != "superseded":
            index.setdefault(entry["key"], []).append(entry)
    for key, homes in sorted(index.items()):
        folders = sorted({h["folder"] for h in homes})
        if len(folders) > 1:
            for h in homes:
                others = ", ".join(f"agents/{f}/" for f in folders if f != h["folder"])
                lint.add("one-home-per-key", h["path"], h["line"], f"key `{key}` also homed in {others} — one canonical home per key")
        elif len(homes) > 1:
            for h in homes[1:]:
                lint.add("one-home-per-key", h["path"], h["line"], f"key `{key}` declared twice in this folder (first at line {homes[0]['line']})")

    findings = lint.findings
    if args.scope:
        scope = args.scope.rstrip("/")
        findings = [f for f in findings if scope in f["path"]]

    def relpath(p):
        try:
            return str(Path(p).relative_to(repo))
        except ValueError:
            return p
    for f in findings:
        f["path"] = relpath(f["path"])
        if baseline_keys is not None:
            f["new"] = (f["rule"], f["path"], f["message"]) not in baseline_keys
    findings.sort(key=lambda f: (f["severity"] != "fail", f["path"], f["line"]))
    fails = sum(1 for f in findings if f["severity"] == "fail")
    warns = len(findings) - fails
    new_fails = sum(1 for f in findings if f["severity"] == "fail" and f.get("new", True))
    gate_fails = new_fails if baseline_keys is not None else fails
    summary = {"folders": lint.counts["folders"], "docs": lint.counts["docs"],
               "facts": lint.counts["facts"], "failures": fails, "warnings": warns,
               "scope": args.scope or "all", "result": "FAIL" if gate_fails else "PASS"}
    if baseline_keys is not None:
        summary["baseline"] = args.baseline
        summary["new_failures"] = new_fails

    if args.format == "json":
        print(json.dumps({"summary": summary, "findings": findings}, indent=2))
    else:
        print(f"canon-lint — {summary['folders']} folder(s), {summary['facts']} fact(s), {summary['docs']} doc(s), scope: {summary['scope']}")
        for f in findings:
            loc = f"{f['path']}:{f['line']}" if f["line"] else f["path"]
            tag = "" if baseline_keys is None else ("  NEW" if f.get("new") else "  (baseline)")
            print(f"  {f['severity'].upper():4} {loc} [{f['rule']}] {f['message']}{tag}")
        if baseline_keys is None:
            print(f"== {summary['result']}: {fails} failure(s), {warns} warning(s)")
        else:
            print(f"== {summary['result']}: {new_fails} NEW failure(s) vs baseline ({fails} total, {warns} warning(s))")
    return 1 if gate_fails else 0


if __name__ == "__main__":
    sys.exit(main())
