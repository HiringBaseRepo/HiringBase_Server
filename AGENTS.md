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
- Dashboard ("Pulse") stays lightweight and real-time oriented. Reports ("Brain") can perform heavier historical aggregation with date filters.

## AI, Storage, and Security Constraints
- Use deterministic fallbacks on final retry instead of hard failure.
- Preload ORM relationships for async worker jobs to avoid `MissingGreenlet`.
- Normalize red-flag payloads to `{message, risk_level, type}`.
- Cache expensive AI calls where project already defines cache paths.
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

## AI Context Map
- Main workflow guide: `.ai-context/agent-rules/agent-instructions.md`
- Layer-specific rules: `.ai-context/agent-rules/instructions/`
- Deep reference docs: `.ai-context/docs/`

## Reference Docs
Read these when task needs deeper context:
- `.ai-context/docs/architecture.md`
- `.ai-context/docs/domain-rules.md`
- `.ai-context/docs/ai-architecture.md`
- `.ai-context/docs/operations.md`
