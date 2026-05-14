# HiringBase Agent Instructions

Read [AGENTS.md](../AGENTS.md) first and treat it as primary contract for this repository.

## How To Work In This Repo
- Start by identifying which layer task belongs to: `routers`, `services`, `repositories`, `schemas`, `models`, `tasks`, `ai`, or `core`.
- Keep changes inside smallest valid scope. Do not refactor unrelated layers unless task explicitly requires it.
- Preserve feature flow: `routers -> services -> repositories -> models`.
- When task needs deeper project context, read only relevant docs from `../docs/`.
- When editing files under `app/features/**/routers`, `services`, or `repositories`, follow matching path instructions in `.agent-rules/instructions/`.
- When unsure, choose more conservative design that keeps business logic in services and persistence logic in repositories.

## Mandatory Self-Check
Before finishing, confirm:
- no `HTTPException` introduced in feature code
- `StandardResponse` conventions preserved
- transaction ownership still follows repo standards
- async safety still holds for any I/O or SDK work
- update flow still respects audit and snapshot requirements

## Preferred Working Style
- Analyze first, then implement.
- Keep explanations short and concrete.
- Mention uncertainty or tradeoff instead of silently guessing.
- If task crosses architectural boundaries, call that out explicitly before continuing.
