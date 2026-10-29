---
owner: steward
status: canonical
updated: 2026-10-29
verified: 2026-10-29
review_by: 2026-11-28
tldr: "The agency gets a finance desk (agent `finance`) and a `finance-lead` seat that approves every invoice and reminder; the principal holds the seat until someone is hired"
source: "the principal, 2026-10-29 (session 6 of the Agent-Native Agency workshop)"
---

# 0006 - A finance desk, and the finance-lead seat

**Decision.** A new domain, `invoicing`, owned by the agent `finance` (template
`Abilityai/keymaker-finance`), behind a new seat, `finance-lead` (`roles/finance-lead.yaml`). The
desk turns a won deal into an invoice from the price list and the handoff Sales writes, records
payments against a bank reference, and chases late invoices on a fixed ladder (Day 1 / 7 / 14). The
seat approves every invoice and every reminder before it leaves; a write-off, a credit above the
list rule, or anything after the final notice is the principal's.

**Who holds the seat.** The principal, until the agency hires a finance lead
(`roles/finance-lead.yaml` `defaults_to: principal`; `domains/org-context/ORGANISATION.md`). On the
open-source edition of Trinity that means the principal owns the `finance` agent, so its approvals
land in the principal's Inbox (the same mechanism as decision 0004 for the rep).

**Why.** Money is the most irreversible thing the agency does and until now no desk owned it: a won
deal ended at Sales' handoff and the agency had no record of what it was owed. The desk is cut
down from the real finance agent the way every Keymaker desk is - same shape, file-backed, the
accounting-system adapter left out of the public copy.

**What changed.** `domains.yaml` (new `invoicing` domain; `finance` added as a consumer of `deals`,
`client-projects` and `pricing`), `roles/finance-lead.yaml`, `domains/approvals/approvals.yaml`
(three entries: send an invoice or reminder, record a payment, write off or credit above the rule),
`domains/org-context/ORGANISATION.md`, `agents/finance/`.
