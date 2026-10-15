# Keymaker canon - conventions

> The canonical-data layer of **Keymaker**, a fictional automation agency built in public during
> the Agent-Native Agency workshop. It is an **instance of the fleet canon standard** - the same
> primitives, the same grammar and the same linter as `Abilityai/canon`'s `CONVENTIONS.md`, cut to
> what a five-agent agency needs. Where this file is silent, the fleet standard applies.

## Layout

```
CONVENTIONS.md         # this file - the rules of the layer
CODEOWNERS             # folder -> the person who reviews changes there
domains.yaml           # THE MAP: what lives where, who owns it, the role behind it, who consumes it
domains/<id>/          # shared content no agent owns, kept by the map's steward:
  pricing/pricing.md        the price list
  approvals/approvals.yaml  who may decide what alone, up to which limit, who decides above it
  org-context/ORGANISATION.md  the people, the roles they fill, the agents that serve them
  decisions/NNNN-<slug>.md  the decision log, append-only
roles/<role-id>.yaml   # one file per role - a seat of work, never a person
objectives/<id>.yaml   # one file per objective - owned by a role, naming declared metrics
protocols/             # inter-agent contracts: information-routing (the flows), playbook-call
agents/<name>/         # one folder per agent - that agent's published record, owned by it
tools/canon-lint/      # the deterministic linter, byte-identical to the fleet's
lint/rules.yaml        # linter severities
```

Deploy definitions (the `deploy_system` manifest) are deliberately **not** here: every agent
clones this whole repo as its canon, so whatever sits in it becomes the agents' working knowledge.
The manifest lives in `Abilityai/keymaker-orchestrator` under `deploy/`.

## Seven rules

1. **People write, agents read.** The top level - the map, `domains/`, `roles/`, `objectives/`,
   `protocols/` - is written by the map's steward on a person's decision, by pull request. An
   agent that wants a change writes a proposal in its own workspace and raises an approval to
   the role `domains/approvals/approvals.yaml` names. An agent commit to the top level is a defect.
2. **One owner per domain, one writer per folder.** `domains.yaml` names exactly one owner for
   each kind of work. An agent writes only its own `agents/<name>/` folder. Two owners means one
   of them is wrong; a domain with no owner says `owner: steward`, never nothing.
3. **Read fresh, never remember.** An agent reads the canon from its `canon/` clone at the start
   of every run and before every route. A price or an owner quoted from memory is a bug.
4. **Roles, never people, in the files the fleet decides on.** `roles/` holds seats; who fills a
   seat is a Trinity assignment, restated in plain words in `domains/org-context/ORGANISATION.md`.
   Every approval names a role and an expiry.
5. **Decisions are logged, not edited.** `domains/decisions/NNNN-<slug>.md` is append-only; a
   reversed decision gets a new file that names the one it supersedes.
6. **Lintable, not prose, at the top level.** `domains.yaml`, `roles/`, `objectives/` and
   `approvals.yaml` use the restricted grammar (scalars, flow lists, one level of list-of-maps,
   `notes: |` for free text). `python3 tools/canon-lint/canon_lint.py --repo .` must pass.
7. **Nothing secret, nothing live.** No credentials, no customer data, no numbers that change
   daily. The canon holds what was decided; live state lives with the agent that owns it.

## Envelopes

Top-level YAML carries `schema_version: 1`, `owner`, `updated`, `verified`, `review_by`,
`file_status` (`canonical | draft | superseded`) and `source`. Markdown under `domains/`,
`protocols/` and `agents/` carries the doc envelope: `owner`, `status`, `updated`, `verified`,
`review_by`, `tldr`, `source`. Staleness bound: 30 days.
