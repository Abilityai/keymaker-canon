# Keymaker canon - conventions

Seven rules. Short on purpose: a canon nobody reads is not a canon.

1. **People write, agents read.** Every file here is edited by a person through a pull request.
   An agent that needs a change writes a proposal under `proposals/` and asks the person
   `operators.yaml` names. An agent commit to this repo is a defect.
2. **One owner per kind of work.** `owners.yaml` names exactly one agent for each kind of work and
   one person behind it. Two owners means one of them is wrong. If a kind of work has no owner,
   the file says `owner: null` - stated, never faked.
3. **Read fresh, never remember.** An agent reads the canon from its `canon/` clone at the start of
   every run and before every route. A price or an owner quoted from memory is a bug, even when it
   happens to be right.
4. **Every approval names a person and an expiry.** `operators.yaml` says who approves what and up
   to which limit. An approval raised to "someone" or with no deadline is refused by convention.
5. **Decisions are logged, not edited.** `decisions/NNNN-<slug>.md` is append-only: one file per
   decision, with the date, who decided, what changed and why. A reversed decision gets a new
   file that says it supersedes the old one.
6. **Prose for people, YAML for agents.** The maps (`owners.yaml`, `operators.yaml`, `flows.yaml`)
   are plain YAML an agent can parse. Explanations go in comments or in this file, never in a
   value an agent will read as data.
7. **Nothing secret, nothing live.** No credentials, no customer data, no numbers that change
   daily. The canon holds what was decided; live state lives with the agent that owns it.

File names are lowercase with hyphens. Dates are ISO (`2026-10-14`). Agent names are the names
as they appear on your Trinity instance.
