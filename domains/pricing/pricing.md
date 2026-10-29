---
owner: steward
status: canonical
updated: 2026-10-29
verified: 2026-10-29
review_by: 2026-11-30
tldr: "The Keymaker price list - four offers and the rules under them; the only source of prices for every agent"
source: "the principal, by pull request; last change domains/decisions/0008-automation-audit-workshop-price.md"
---

# Keymaker price list

The only source of prices for every agent in the agency. Anything not on this list is
`[NEEDS-PRICE-LIST]`; a price off the list needs the principal (see `domains/approvals/approvals.yaml`).
Changed only by pull request to this repo. Sample numbers for a fictional agency.

| Offer | What the client gets | Price | Notes |
|-------|----------------------|-------|-------|
| Automation audit | We map what they run (agents, flows, scripts), decide keep / wrap / rebuild, and deliver a readiness report | $2,500 fixed | 2 weeks |
| Pilot | One department on their own Trinity instance: install, two agents, one real workflow live | $12,000 fixed | 4 weeks; credited against a Build |
| Build | The agency system: departments, shared brain, orchestrator, workspace for their team | from $40,000 | scoped per proposal |
| Operate | We run the instance with them: monitoring, improvements, new playbooks | $2,500 / month | 3-month minimum |
| Automation audit - introductory price | The same audit at a limited-time price; paid by card on the Stripe Payment Link | $500 fixed | 3 slots, until 2026-11-30; a payment is a won deal; decision 0008 |

Every offer is described for our client in `domains/market/who-we-serve.md` (decision 0005).

Rules: no discounts on the audit; a pilot credit applies only within 90 days; Operate is quoted
only after a Build or a Pilot; a discount up to 10% on a Pilot or a Build is the rep's call and is
given as an invoice credit, never as a lower rate; above 10% the principal decides.

Last decided: `domains/decisions/0008-automation-audit-workshop-price.md` (the workshop row); `domains/decisions/0002-operate-price-2500.md` (Operate); `domains/decisions/0001-price-list.md` (the list).
