# Proposals

Changes an agent has prepared and a person has not yet approved. Written by the orchestrator's
`/canon-change`; each file names the file it would change, the exact diff, who must approve it
(from `operators.yaml`) and the deadline. A person applies an approved proposal by PR and deletes
the file; a declined one is deleted with a line in `decisions/` if the reason matters.
