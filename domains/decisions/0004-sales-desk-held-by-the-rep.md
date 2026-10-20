---
owner: steward
status: canonical
updated: 2026-10-20
verified: 2026-10-20
review_by: 2026-11-19
tldr: "The sales desk is now the agent `sales`, owned by the sales-rep's own login, so its approvals reach the rep; the old `sales-agent` is retired"
source: "the principal, 2026-10-20 (session 5 of the Agent-Native Agency workshop)"
---

# 0004 - The sales desk is held by the rep

**Decision.** The deals domain's owner agent is `sales` (was `sales-agent`). It was created from the
same public template by the `sales-rep` (Sam Reyes) under his own Trinity login, so the platform
routes its approvals - "send this reply?", a discount within his 10% - to his Workspace Inbox.
The principal still decides everything above the rep's limit, through the orchestrator, which the
principal owns.

**Why.** On the open-source edition of Trinity an agent's approvals go to the agent's owner. A seat
is held by a person; on this edition the way to say "this agent serves Sam's seat" is for Sam to own
it. (The Enterprise edition expresses it directly, as an approver seat on any agent.)

**What changed.** `domains.yaml` (deals owner), consumer lists, `agents/sales/` (was
`agents/sales-agent/`). The pipeline and drafts were carried over from the retired agent.
