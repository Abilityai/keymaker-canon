---
owner: orchestrator
status: canonical
updated: 2026-10-15
verified: 2026-10-15
review_by: 2026-11-14
tldr: "How information moves in the agency: five flows, each with a gate (log or human-approval); the orchestrator carries all five and owns none"
source: "the fleet canon's protocols/information-routing.md (corbin, v2.1), cut to what a five-agent agency needs; the Keymaker principal, 2026-10-15"
---

# Protocol: information routing

Every agent takes in information it did not ask for - a lead, a call, another agent's report -
and has to decide where it goes. This protocol fixes the five movements and the gate each one
carries, so an agent can read it as data, not prose.

## Gate vocabulary

| Gate | Meaning |
|---|---|
| `log` | write, and leave a receipt - an execution id, a file, a ledger row |
| `human-approval` | a person says yes before anything changes; the agent prepares, then waits |

## The five flows

| Flow | From -> to | Carries | Gate | Never |
|---|---|---|---|---|
| **decisions-down** | people -> every agent | the map, the approval limits, the price list, the roles | `human-approval` - a PR, approved by the role `domains.yaml` names | an agent editing the canon; an agent quoting it from memory |
| **facts-up** | the desks -> their own files -> the orchestrator's ledger -> a person in the morning brief | pipeline state, client health, leads, notes | `log` | a second agent writing a desk's file; a number typed by hand |
| **lessons-through-the-brain** | the desks -> `cornelius` -> back to the desks and the orchestrator as judgment | post-mortems and outcomes up; advice with its sources and labels down | `human-approval` - a person graduates a note | the brain commanding a desk; its inference reported as the agency's view |
| **requests-across** | the orchestrator -> the one owner `domains.yaml` names | one request, as a one-line playbook call (`protocols/playbook-call.md`) | `log` - the execution id is the receipt | the orchestrator doing the work; two owners; a re-send on silence |
| **escalations** | any agent -> the role `domains/approvals/approvals.yaml` names for that action | one decision, the options, the cost of waiting, a deadline | `human-approval` | an ask with no named role; no expiry; the same ask twice |

## Invariants

1. **Named owner beats escalation.** If `domains.yaml` names an owner, the request goes there; the principal's queue is the last resort.
2. **Every destination leaves a receipt.** A hand-off without an execution id did not happen.
3. **Silence is not success.** A run names what it could not see, by name.
4. **A relay is not a source.** Check a fact at the file it lives in before passing it on.

## Machine-readable

```yaml
version: 1
gates: [log, human-approval]
flows:
- id: decisions-down
  from: people
  to: every agent
  gate: human-approval
- id: facts-up
  from: the desks
  to: own files, then the orchestrator's ledger, then a person
  gate: log
- id: lessons-through-the-brain
  from: the desks
  to: cornelius, then back as judgment
  gate: human-approval
- id: requests-across
  from: orchestrator
  to: the one owner domains.yaml names
  gate: log
- id: escalations
  from: any agent
  to: the role approvals.yaml names
  gate: human-approval
escalate_now: [money above a rep limit, a client at risk, anything irreversible, security]
```
