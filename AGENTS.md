# AGENTS.md - HiringBase AI Context

## Mission
AI-powered recruitment backend for HR teams: job vacancy creation, form-based applications without CVs, AI candidate screening and ranking, explainable AI decisions, and ticket-based status tracking.

## Critical Rules
- Keep feature flow directional: `routers -> services -> repositories -> models`.
- Never raise `HTTPException` anywhere in feature code, including routers, services, and dependencies. Raise `BaseDomainException` subclasses only.
- All responses must use `StandardResponse` with `{success, message, data, errors, meta}`.
- All I/O must be async-safe. Offload blocking SDK or file work.
- Services own `db.commit()`. Repositories own `db.add()`, `db.flush()`, and `db.refresh()`.
- Never add files directly to feature root. Use `routers/`, `services/`, `repositories/`, `schemas/`, `models/`, or `tasks/`.
- Backend, database, and AI internals stay in English. User-facing labels, statuses, messages, and errors must map through Indonesian localization helpers.
- Heavy AI work must run through Taskiq workers or equivalent async-safe offloading.
- Taskiq runtime for screening now depends on **both** worker and scheduler. If broker runs without scheduler, hourly batch screening is considered misconfigured.
- Every update must snapshot old values with `get_model_snapshot` before mutation.
- AI scoring weight changes must be recorded in audit log.
- IP and User-Agent come from middleware contextvars. Do not pass them manually.
- Do not add local ML libraries for embeddings or OCR workloads.

## Layer Boundaries

### Routers
Allowed:
- FastAPI routing, dependencies, request parsing, response wrapping, tags, and HTTP-facing concerns

Forbidden:
- SQLAlchemy queries
- direct DB writes
- business logic
- large mapping loops
- `HTTPException`

### Services
Allowed:
- business rules
- ownership checks
- status transitions
- ticket generation
- token creation
- password hashing
- scoring and knockout orchestration
- audit intent
- `db.commit()`

Forbidden:
- `db.add()`
- `db.flush()`
- `db.refresh()`
- complex query building
- raw HTTP response shaping
- hardcoded DB constraints that belong in repositories or models

### Repositories
Allowed:
- SQLAlchemy selects, inserts, updates, deletes
- pagination
- eager loading
- `db.add()`
- `db.flush()`
- `db.refresh()`

Forbidden:
- business decisions
- password hashing
- token or ticket generation
- AI, OCR, or file-storage orchestration
- HTTP response logic
- `db.commit()`

### Schemas
Use explicit Pydantic request bodies, response shapes, filter objects, form payloads, and DTOs. Prefer typed schemas over raw `dict` payloads.

### Models
Use string-literal relationships and `TYPE_CHECKING` hints when needed. Keep Alembic-visible model aggregation in `app/features/models.py`.

## Core Domain Rules
- AI architecture has 3 layers: deterministic scoring, NLP/embedding matching, and LLM explanation/red-flag analysis.
- No CV parsing in scoring engine. Form answers in `ApplicationAnswer` are source of truth.
- Application flow: `APPLIED -> DOC_CHECK -> AI_PROCESSING -> AI_PASSED/UNDER_REVIEW/KNOCKOUT -> INTERVIEW -> OFFERED -> HIRED`, with rejection and document-failed exits.
- Public applicants have no login. Submission returns `TKT-YYYY-NNNNN`.
- Default scoring weights: Skill Match 40, Experience 20, Education 10, Portfolio 10, Soft Skill 10, Admin Complete 10.
- Knockout actions: `auto_reject` or `pending_review`.
- Screening is **quota-aware by design**. Prefer slower deterministic throughput over aggressive real-time AI fan-out.
- Public application flow must **not** auto-trigger AI screening on submit. New applications stay `APPLIED` and are picked up by batch or manual trigger.
- Manual screening may bypass batch ordering, but must still respect screening guard rules: dedupe, concurrency cap, hourly cap, daily cap.
- Batch screening source is not only `APPLIED`; stale `DOC_CHECK` and stale `AI_PROCESSING` entries may enter recovery path.
- Recovery retries for stale screening must stay bounded. If retry limit is exceeded, fallback target is `UNDER_REVIEW`, not repeated blind retries.
- Dashboard ("Pulse") stays lightweight and real-time oriented. Reports ("Brain") can perform heavier historical aggregation with date filters.

## AI, Storage, and Security Constraints
- Use deterministic fallbacks on final retry instead of hard failure.
- Preload ORM relationships for async worker jobs to avoid `MissingGreenlet`.
- Normalize red-flag payloads to `{message, risk_level, type}`.
- Cache expensive AI calls where project already defines cache paths.
- Redis is approved for screening queue markers, processing locks, retry counters, and quota counters.
- Groq calls may use fallback API key chain when primary key hits provider rate limit. Never hardcode secret keys in tracked files; use env config only.
- Screening orchestration must prevent duplicate enqueue for same application within cooldown window.
- If AI/OCR/LLM pipeline fails repeatedly, status must not remain stuck in `DOC_CHECK` or `AI_PROCESSING`. Force safe handoff to `UNDER_REVIEW` with status log and audit signal.
- Uploads use async wrappers. If DB commit fails after upload, attempt best-effort rollback deletion.
- Use Structlog, not `print()`, for runtime debugging in feature flow.

## Definition of Done
Before finishing any task, verify:
- touched files stay in correct layer
- no forbidden DB calls leaked into services
- no business logic leaked into routers or repositories
- all user-facing responses still use `StandardResponse`
- exceptions use domain exceptions, not `HTTPException`
- async safety and audit requirements remain intact
- domain flows, AI fallbacks, and localization rules still match project rules
- Taskiq command wiring uses correct argument types:
  - object path like `app.core.tkq:broker`
  - import module like `app.main`
  - do **not** pass `app.main:app` as task import module
- screening quota guard, duplicate prevention, and fallback-to-review behavior still work together without race-obvious regressions

## Reference Docs
Read these when task needs deeper context:
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/ai-architecture.md`
- `docs/operations.md`

## Current Screening Runtime Notes
- Screening batch runtime currently starts API, Taskiq worker, and Taskiq scheduler together via `scripts/render-free-start.sh`.
- Correct Taskiq CLI wiring:
  - worker/scheduler target object uses `module:variable`, e.g. `app.core.tkq:broker`
  - imported task modules use plain module path, e.g. `app.main`
  - `app.main:app` is valid for FastAPI object lookup inside `taskiq_fastapi.init(...)`, but invalid as task module import argument
- Screening queue control now uses Redis markers/counters for:
  - duplicate enqueue prevention
  - processing locks
  - hourly and daily quota counters
  - recovery retry counters
