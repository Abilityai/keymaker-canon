---
owner: steward
status: canonical
updated: 2026-10-29
verified: 2026-10-29
review_by: 2026-11-28
tldr: "Who is in the Keymaker agency, which role each person fills, and which agents serve them - plain words, never the thing the fleet decides on"
source: "the principal, 2026-10-15, finance seat 2026-10-29, prospecting desk 2026-10-29; the Trinity assignment is the record, this page is the explanation"
---

# The Keymaker agency - people, roles, agents

Keymaker is a fictional automation agency built in public during the Agent-Native Agency
workshop. The people below are the workshop's own operators, named so that every approval in
`domains/approvals/approvals.yaml` resolves to someone who can answer. The roles are the files in
`roles/`; who fills them is recorded in Trinity (the Access tab of each agent) and restated here
so a person can read it.

| Role (`roles/`) | Filled by | Agents that serve the seat |
|---|---|---|
| `principal` | Eugene Vyborov (eugene@ability.ai) - the admin of the Keymaker instance | `orchestrator`, `cornelius` |
| `sales-rep` | Sam Reyes (sam@keymaker.agency) | `sales`, `prospector` (decision 0007) |
| `delivery-manager` | Noor Haddad (noor@keymaker.agency) | `delivery-agent`, `meeting-notes-bot` |
| `marketing-lead` | Theo Lindqvist (theo@keymaker.agency) | `marketing-agent`, `website` |
| `finance-lead` | Eugene Vyborov (eugene@ability.ai) - held by the principal until the agency hires one (decision 0006) | `finance` |
| `orchestrator` | held by the agent itself | `orchestrator` |

The principal sees every deal and is the only signer. A rep works the deals they own, and decides which prospects the prospecting desk found are contacted. The
delivery manager owns client state. The marketing lead owns what is published. The finance lead approves every invoice and reminder before it leaves. The brain
(`cornelius`) serves everyone and commands no one.
