---
owner: steward
status: canonical
updated: 2026-10-29
verified: 2026-10-29
review_by: 2026-11-28
tldr: "The agency writes its first rule for contacting someone who has not written in, and gets a prospecting desk (agent `prospector`) under the sales-rep seat: firms from public sources, qualified against who-we-serve, a first line the rep sends; never contacts anyone, no personal data, no list"
source: "the principal, 2026-10-29 (session 6 of the Agent-Native Agency workshop), after the brain's advice (cornelius execution SMKnQGSihkRwaUXHHtoKdA) - which recommended the rule first and the desk later"
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

**Why, and what the brain said.** The principal's premise was that every deal so far came inbound
through the website. The brain (`/advise`, 2026-10-29) corrected it first: the sales desk's records
carry **no channel field** - channel exists only as free text, one row is a referral, two are blank,
none is outbound - and behind the nine rows sit zero won deals, zero invoices and zero replies
received, so there is no measured inbound ceiling to escape. It also reported zero: the agency's
reading holds **no base rate** for where a small services agency's clients come from, and it
declined to invent one. Its recommendation was not the desk: write the rule for contacting someone
who has not written in (canon was silent - the approvals gate said *client*, not *prospect*, and no
rule covered a prospect's personal data), add `channel` and `outcome` to the pipeline so any
acquisition experiment can be measured, authorise firm-level public-source qualification now, and
keep the first line in the rep's own hand until twenty have been written and logged. Its own
dissent: if Keymaker's purpose is to demonstrate an agent-native agency, the desk's guardrails
*are* the product, and both framings converge on the same first act - write the contact rule.

**The decision takes the rule and the desk together.** The contact rule is the approvals row
below. The desk qualifies at firm level with a mechanical two-of-three screen and drafts a first
line the rep may use or discard; the rep writes and logs what is actually sent. Follow-ups owed to
the brain's reading, not yet done: `channel` and `outcome` fields on the sales desk's pipeline
(decision 0005's bet is unmeasurable without them); the stale sample `pricing.md` on the sales
desk's disk (Operate $2,000) replaced by the canon price. Falsifier the brain set: if by
2026-12-31 fewer than ten firms have a logged outcome, the desk is drafting into a void and the
rule, not the desk, is what to revisit.

**The line it never crosses.** Public sources only. No personal email address or phone number is
stored, ever - a contact is a role and a name as the firm publishes it, with the URL. No purchased or
imported list. No send path exists on the desk and no key would add one.

**What changed.** `domains.yaml` (new `prospects` domain; `prospector` added as a consumer of
`market` and `deals`), `domains/approvals/approvals.yaml` (one entry: contact a firm we have not
spoken to), `domains/org-context/ORGANISATION.md` (the `sales-rep` row gains `prospector`),
`agents/prospector/`. First desk hired with the orchestrator's `/hire` playbook rather than by hand.
