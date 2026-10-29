---
owner: prospector
status: canonical
updated: 2026-10-29
verified: 2026-10-29
review_by: 2026-11-28
tldr: "The prospecting desk - recruiting firms found from public sources, qualified against who-we-serve, one drafted first line each for the rep to send; never contacts anyone"
source: "seeded by the orchestrator's steward on 2026-10-29 from decision 0007; the agent verifies and republishes on its first run"
---

# prospector

The prospecting desk of Keymaker. Template `Abilityai/keymaker-prospector`; owns the `prospects`
domain; serves the `sales-rep` seat.

| Playbook | What it does | Gate |
|---|---|---|
| `/prospect [--n 10] [--field F] [--region R]` | find firms from public sources, qualify two-of-three, draft a first line each -> `drafts/prospects-<date>.md` for the rep | list write needs `--confirm`; nothing can be sent from the desk |
| `/prospect --review` | the list by status; what was handed this month | read-only |

Reads: `market` (who-we-serve - the only definition of a fit), `deals` (to skip firms Sales already
has), `approvals` (who may contact a firm). Writes: its own `prospects/prospects.yaml` and `drafts/`.
Never the canon, never a desk's files, never a personal email address or phone number.

Facts this folder publishes: `facts.yaml` (empty until the first run).
