---
owner: finance
status: canonical
updated: 2026-10-29
verified: 2026-10-29
review_by: 2026-11-28
tldr: "The finance desk - invoices from won deals, payments against references, overdue on a fixed ladder; every document approved by the finance lead before it leaves"
source: "seeded by the orchestrator's steward on 2026-10-29 from decision 0006; the agent verifies and republishes on its first review"
---

# finance

The finance desk of Keymaker. Template `Abilityai/keymaker-finance`; owns the `invoicing` domain;
serves the `finance-lead` seat (held by the principal until hired).

| Playbook | What it does | Gate |
|---|---|---|
| `/invoice <deal slug>` | won deal -> invoice document + covering email | finance lead: "send as written" |
| `/payments` | record a payment (amount, reference, date) or list what is unpaid | ledger write needs `--confirm` |
| `/overdue [--review]` | the books review (Mondays) and the next reminder on the ladder | finance lead approves each reminder |

Reads: the handoff Sales writes on a won deal (`deals`), Delivery's client state before a final
notice (`client-projects`), the price list (`pricing`), the limits (`approvals`).
Writes: its own `ledger/invoices.yaml`, `invoices/`, `drafts/`. Never the canon, never a desk's files.

Facts this folder publishes: `facts.yaml` (empty until the first review runs).
