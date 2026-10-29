---
owner: steward
status: canonical
updated: 2026-10-29
verified: 2026-10-29
review_by: 2026-11-28
tldr: "The agency gets a prospecting desk (agent `prospector`) under the sales-rep seat: finds recruiting firms from public sources, qualifies them against who-we-serve, drafts a first line the rep sends; never contacts anyone, never buys a list"
source: "the principal, 2026-10-29 (session 6 of the Agent-Native Agency workshop), on the brain's advice"
---

# 0007 - A prospecting desk

**Decision.** A new domain, `prospects`, owned by the agent `prospector` (template
`Abilityai/keymaker-prospector`), under the existing seat `sales-rep`. The desk finds specialist
recruiting firms of 20-100 people from their public footprint, qualifies each against
`domains/market/who-we-serve.md` (two of three signals: size and specialism, an ATS and a job board,
visible hurt), and drafts one first line per firm. The rep decides who is contacted and sends from
their own mailbox. A firm becomes a `deal` only when a conversation has started and Sales opens it.

**Who holds the seat.** The sales rep (`roles/sales-rep.yaml`), as for `sales`. No new seat: a
prospecting desk serves the person who sells, it does not sell.

**Why.** Every deal the agency has had came inbound through the website; the brain's reading says
a small agency's clients come from inbound and referral first, and that outbound works only when
it is narrow, researched and sent by a person - which is exactly the shape the agency's own rules
already impose (drafts only, canon prices, the rep presses send). A desk that reads public footprints
and writes first lines is that shape; a desk that mails lists is not, and is not built.

**The line it never crosses.** Public sources only. No personal email address or phone number is
stored, ever - a contact is a role and a name as the firm publishes it, with the URL. No purchased or
imported list. No send path exists on the desk and no key would add one.

**What changed.** `domains.yaml` (new `prospects` domain; `prospector` added as a consumer of
`market` and `deals`), `domains/approvals/approvals.yaml` (one entry: contact a firm we have not
spoken to), `domains/org-context/ORGANISATION.md` (the `sales-rep` row gains `prospector`),
`agents/prospector/`. First desk hired with the orchestrator's `/hire` playbook rather than by hand.
