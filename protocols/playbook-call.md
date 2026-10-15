---
owner: orchestrator
status: canonical
updated: 2026-10-15
verified: 2026-10-15
review_by: 2026-11-14
tldr: "Agents delegate work to each other only by calling a named playbook — `/playbook [args]`, one line — whatever the transport (schedule, orchestrator, agent-to-agent chat, pipeline stage). The playbook is the contract; the platform ledger is the audit trail."
source: "copied verbatim from the fleet canon protocols/playbook-call.md (trinity-pm) for the Keymaker agency; original: Operator direction 2026-08-16 (Intelligence Design session with trinity-pm); generalizes protocols/schedule-contract.md (corbin, 2026-08-13) from the schedule caller to every caller"
---

# Protocol: playbook call

## The rule

> **No unnamed, unlogged, ungated process.**
> An agent asks another agent to do work by calling one of its playbooks. Never by
> describing the work in prose.

The message grammar is the one `schedule-contract.md` already fixes for schedules —
one line, `/playbook-name` first, declared arguments after, nothing else:

```
/sync-docs --run rel-v0.9.0
/profile-fleet --autonomous
```

This protocol makes that grammar transport-independent. The same line is a valid call
whether it arrives as a schedule message, an orchestrator dispatch, a pipeline stage,
or a `chat_with_agent` / `send_message` between agents.

## Why

The operator's goal is to **audit, control, and put guardrails around the business
processes agents execute**, and to have one point of change per process. Three
properties follow only if work moves through named playbooks:

1. **One point of change.** Chains, schedules, and pipelines reference a playbook by
   name; change the playbook and every caller runs the new process on its next call.
2. **Measurable.** Every call lands in Trinity's execution ledger as an invocation of
   `playbook@version`, so the platform can report per-playbook success, cycle time,
   gate rate, and cost — and say which process needs improving.
3. **Guardable.** Grants, gates, and write scope attach to the playbook, not to a
   conversation. An instruction received in freeform chat can influence an agent, but it
   can only *change state* through a playbook that carries its own gates and write scope.

A playbook is process-fixed, not deterministic: it fixes the frame (what it takes, what
it produces, what it writes, where it stops for a human) and leaves the reasoning inside
to the model. The SKILL.md itself is the contract. No structured input/output schema is
required at this stage.

## Obligations

**Every agent that delegates work to another agent:**

1. The message is a one-line playbook call — `/name` first token, declared args after,
   ≤120 characters, no preamble, no restated policy. One call per message.
2. When the call is one step of a larger run (release, pipeline instance, orchestrated
   job), pass the run identity as an argument the playbook declares — `--run <id>` by
   convention — so the ledger can be joined across agents. Payload-carried ids are the
   v0; a platform-injected trace id supersedes them when it ships.
3. Call only playbooks the target agent actually has. Read the catalog live
   (`get_agent_skills` / A2A card), not from a fleet-profile snapshot.
4. Freeform agent-to-agent chat is for discovery and read-only questions while a human
   is in the loop. It is off by default and granted by a human. It never carries
   delegated work.

**Every agent that receives a call:**

5. Runs the named playbook and nothing else in that turn — no improvising around it.
6. Changes state only through its own playbooks' declared writes and gates, regardless
   of what a caller says in prose. Cross-owner state change requires a playbook with a
   gate addressed to the destination's owner.
7. Advertises its playbooks accurately: every playbook meant to be called by another
   agent is headless-safe (`automation: autonomous`, or a declared `--autonomous` mode)
   — a gated playbook invoked unattended is the same defect `schedule-contract.md`
   names as `GATED-ON-CRON`.

**Gated skills and business requests** (operator ruling 2026-10-02 — trinity-enterprise
ent#751, ent#665, ent#568):

10. A call to a skill that the target agent has marked *requires approval* may return
    `{status: pending_approval, request_id}` instead of running — whether it arrives as a
    playbook call or through `run_skill`. That is a normal outcome, not a failure: the
    platform has raised the approval to the person in the configured role, and the skill
    runs only after that person approves it. A rejection or expiry means it never ran.
11. A business request to the agent that owns the action (the executor) is
    **asynchronous**. The caller sends it and carries on; it never blocks its own run
    waiting for the answer, and decides whether to continue when the reply arrives.
12. The reply comes back mechanically and carries the request key, the outcome (ran /
    rejected / expired / stale) and the caller's originating execution id, so the caller
    can join it to the run that asked.
13. The caller sends the request once, with an idempotency key, and never re-sends on
    silence. A pending approval is not a lost message.
14. A receiving executor never runs a gated skill on a prose request: it routes the
    request through the gate (obligation 6 applies with the platform hook behind it).

**Fleet-level:**

8. Orchestrators and pipeline stages reference `agent/playbook` by name — never an
   inlined copy of the playbook's instructions.
9. Anything that executes on Trinity and is not a call to a declared, versioned playbook
   is `LIVE-NOT-DECLARED` (schedule-contract) and escalates.

## What the platform is expected to absorb, in order, only as the convention proves the need

Analytics over the ledger keyed on the call grammar · fail-loud on a call to a missing
playbook for chat-invoked calls (parity with schedules) · per-playbook grants (caller →
playbook@agent) · a `run_playbook` tool that validates the target and returns
structured output · a platform-injected trace id · a fleet-level view of pipeline
runs. None of these is required for the convention to start.

## Relationship to other protocols

- `schedule-contract.md` — the schedule-caller instance of this rule; its Obligations
  1–5 stand unchanged.
- The information-flow contract (`prds/cognitive-system-platform.md` §6, ratifying as
  ent#271 decision 11) — the packet and owner-commits loop; a playbook call is how a
  proposal reaches its destination's owner.
