---
owner: steward
status: canonical
updated: 2026-10-29
verified: 2026-10-29
review_by: 2026-11-30
tldr: "A workshop price for the Automation audit: $500 (list $2,500), three slots, paid by card on a Stripe Payment Link, until 2026-11-30; a payment is a won deal and Ability AI delivers the audit"
source: "the principal, 2026-10-29 (session 6 of the Agent-Native Agency workshop) - 'approved' in chat with Corbin, 03:50 UTC"
---

# 0008 - The Automation audit at a workshop price

- **Date:** 2026-10-29
- **Decided by:** the principal (the only seat that may price the audit below list - `approvals.yaml`: any discount on the Automation audit, `decides_alone: null`, `above_limit: principal`).
- **What:** a fifth row on the price list, **Automation audit - workshop price**: the same audit as the $2,500 row, **$500 fixed, three slots, for attendees of the Agent-Native Agency workshop, until 2026-11-30**. Paid by card on a Stripe Payment Link (`https://buy.stripe.com/28EdRb0g857f5jm8BYfEk00`, product `prod_VWnzA3UB7EDUpu`, created from the finance desk's restricted key). This is a separate offer, not a discount: the rule *no discounts on the audit* is unchanged.
- **What happens on a payment:** Finance reads it from Stripe (`/payments --check`) as a checkout payment with no invoice number and tells the orchestrator - product, email, amount. The orchestrator routes it to Sales as a request to talk at **Won** for the audit (`/deal <company> --open --source workshop-payment`), Sales writes the handoff, Delivery opens the project. **Ability AI delivers the audit** (Eugene Vyborov); Keymaker is the storefront. The buyer hears from a person within one business day - the Payment Link's confirmation says so.
- **Why:** the workshop's last session asked for something real for someone real. A paid audit at a price the room can say yes to is the smallest real engagement the agency can run end to end on the system it built in public - payment, books, deal, project - and the audit is the entry point of the engagement shape anyway (audit -> pilot -> build -> operate).
- **Touches:** `domains/pricing/pricing.md` (new row + a note), the website (a buy button next to the audit, rendered from the canon row by the website agent by pull request), the finance desk's `/payments --check` (already reports checkout payments to the orchestrator), the orchestrator's routing (`deals`).
- **Naming (principal, 2026-10-29 04:30 UTC):** the public row is **Automation audit - introductory price** - the agency's site reads as an agency, not as a workshop artefact; the slots are still meant for the room. The Stripe product carries the same name.
- **Expires:** the row is removed from `pricing.md` after 2026-11-30 or when three slots are sold, whichever first; the Payment Link is deactivated by a person in Stripe at the same time.
