# Keymaker canon

The **canon** of Keymaker, a fictional automation agency built in public during the
[Agent-Native Agency workshop](https://www.ability.ai/trinity/workshops/agent-native-agency-workshop).
It holds **what the agency has decided**: who owns which kind of work, who may approve what, what
things cost, and how information moves between people, agents and the brain.

**People write it. Agents read it. No agent ever edits it.** An agent that wants a change
prepares a proposal and raises an approval to the role that decides.

It is a repository, not an agent, and it is an **instance of the fleet canon standard**
([CONVENTIONS.md](CONVENTIONS.md)): the same files, grammar and linter Ability's own fleet runs
on, cut to what a five-agent agency needs. This repo is a GitHub **template** - press *Use this
template* to start your own.

## What is in it

| File | Holds | Read by |
|---|---|---|
| `domains.yaml` | **the map**: each kind of work, the one agent that owns it, the role behind it, who consumes it | the orchestrator, before every route |
| `roles/` | the seats of work - principal, sales-rep, delivery-manager, marketing-lead, orchestrator - and their decision rights | the orchestrator, when it escalates |
| `domains/approvals/approvals.yaml` | who may decide what alone, up to which limit, who decides above it, how long an ask lives | the orchestrator, every desk |
| `domains/pricing/pricing.md` | the price list - the only source of prices | the sales desk, the orchestrator |
| `domains/org-context/ORGANISATION.md` | who fills each role, in plain words | people; the desks, to name a person |
| `protocols/information-routing.md` | the five flows - decisions down, facts up, lessons through the brain, requests across, escalations - and the gate on each | the orchestrator; people asking "how does X reach Y?" |
| `protocols/playbook-call.md` | how one agent asks another for work: a one-line playbook call | every agent |
| `objectives/` | what the agency is driving at this quarter, owned by a role, measured by declared metrics | the orchestrator's brief |
| `domains/decisions/` | why it is like this - one short file per decision, append-only | anyone |
| `agents/<name>/` | each agent's own published record (`profile.md`, `facts.yaml`) - the only place an agent writes | the other agents |

## Set up a canon for your agency - the procedure

1. **Make the repo.** *Use this template* on GitHub. Public is simplest (agents clone it with no
   token); private works with a token the platform holds (Settings → GitHub).
2. **Fill the map and the seats.** `domains.yaml` (one owner per kind of work - two is one too
   many; the `role` behind it), `roles/` (one file per seat), `domains/org-context/ORGANISATION.md`
   (who fills each seat), `domains/approvals/approvals.yaml` (real limits), `domains/pricing/pricing.md`
   (your offers). Leave the protocols alone until you have a reason to change a gate.
3. **Lint it.** `python3 tools/canon-lint/canon_lint.py --repo .` - exit 0 means the map, roles,
   objectives and envelopes are consistent.
4. **Give the agents the canon.** Each agent that reads it carries a tracked `.trinity/setup.sh`
   that clones the repo into `canon/` on every container start (the orchestrator template has
   one - copy it). An agent reads from `canon/`, never from a copy in its own repo.
5. **Change it by pull request.** A person edits a file and opens a PR; the role
   `domains/approvals/approvals.yaml` names approves and merges; a line in `domains/decisions/`
   says why. An agent that wants a change writes a proposal and raises an approval; it never commits.

## The flows, in one picture

```
   PEOPLE  --decisions down (canon)-->  every agent        gate: a PR, approved by a named role
   DESKS   --facts up (own files, receipts)-->  orchestrator --brief-->  a person   gate: log
   DESKS   --lessons up-->  THE BRAIN  --judgment down-->  desks, orchestrator       gate: a person graduates
   ORCHESTRATOR --one-line playbook call-->  the one owner  --execution id back--     gate: log (the receipt)
   ANY AGENT --escalation-->  the role approvals.yaml names, with options and an expiry   gate: human-approval
```

The orchestrator carries all five and owns none. Full definition: `protocols/information-routing.md`.

## Licence

Apache 2.0. Keymaker is a fictional agency: no real clients, deals or money. The operators are the
workshop's own people, named so the approval chain resolves to someone who can answer.
