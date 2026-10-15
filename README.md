# Keymaker canon

The **canon** of Keymaker, a fictional automation agency built in public during the
[Agent-Native Agency workshop](https://www.ability.ai/trinity/workshops/agent-native-agency-workshop).
It is the one place that holds **what the agency has decided**: who owns which kind of work,
who may approve what, what things cost, and how information moves between people, agents and
the brain.

**People write it. Agents read it. No agent ever edits it.** An agent that wants a change
prepares a proposal and names the person who must approve it.

It is a repository, not an agent: there is nothing to deploy. Every agent that needs it clones
it at start (see step 3 below). This repo is a GitHub **template** - press *Use this template*
to start your own.

## What is in it

| File | Holds | Read by |
|---|---|---|
| `owners.yaml` | the routing map: each kind of work, the one agent that owns it, the person behind that agent | the orchestrator, before every route |
| `operators.yaml` | the people: who operates which desk, who may approve what, with limits | the orchestrator, the sales desk |
| `pricing.md` | the price list - the only source of prices | the sales desk, the orchestrator |
| `flows.yaml` | the information flows: decisions down, facts up, lessons through the brain, requests across, escalations - and the gate on each | the orchestrator; people, when they wonder "how does X get to Y?" |
| `decisions/` | the decision log, one short file per decision, append-only | anyone asking "why is it like this?" |
| `proposals/` | changes an agent has prepared and a person has not yet approved | the approver named in each proposal |
| `system.yaml` | the whole agency as one Trinity manifest: six agents, their edges, their tags | `deploy_system`, to rebuild the agency on any Trinity |

Rules in [CONVENTIONS.md](CONVENTIONS.md).

## Set up a canon for your agency - the procedure

1. **Make the repo.** *Use this template* on GitHub. Public is simplest (agents clone it with no
   token); private works with a token the platform holds (Settings → GitHub).
2. **Fill the three maps.** `owners.yaml` (one line per kind of work, one owner each - two owners
   is one too many), `operators.yaml` (real names, real emails, real limits), `pricing.md` (your
   offers). Leave `flows.yaml` as it is until you have a reason to change a gate.
3. **Give the agents the canon.** Each agent that reads it carries a tracked
   `.trinity/setup.sh` that clones the repo into `canon/` on every container start and pulls it
   fresh after that (the orchestrator template has one - copy it). An agent reads the files from
   `canon/`, never from a copy in its own repo. Check it landed: ask the orchestrator
   *"Who do you route to, and how do you decide?"* - it reads `owners.yaml` back to you.
4. **Change it by pull request.** A person edits a file and opens a PR; the person
   `operators.yaml` names for that file approves and merges. An agent that wants a change writes
   `proposals/<date>-<slug>.md` and raises an approval to that person; it never commits to the
   canon. Record why in `decisions/` when the change is more than a typo.
5. **Keep it true.** The orchestrator's `[canon-watch]` schedule pulls the canon every morning and
   reports what changed and whether every owner in `owners.yaml` is a running agent it may call.
   A map that names an agent nobody can reach is reported, not guessed around.

## The flows, in one picture

```
   PEOPLE  ──decisions down (canon)──►  every agent      gate: a PR, approved by a named person
   DESKS   ──facts up (files, receipts)──►  orchestrator ──brief──►  a person     gate: log
   DESKS   ──lessons up──►  THE BRAIN  ──judgment down──►  desks, orchestrator   gate: a person graduates
   ORCHESTRATOR ──one-line playbook call──►  the one owner  ──execution id back──  gate: log (the receipt)
   ANY AGENT ──escalation──►  a named person, with options and an expiry     gate: human-approval
```

The orchestrator carries all five flows and owns none of them. The full definition, with the
gate vocabulary, is in `flows.yaml`.

## Licence

Apache 2.0. Fictional company; nothing here is real.
