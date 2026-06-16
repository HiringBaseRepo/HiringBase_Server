# AGENTS.md - HiringBase AI Context

## Mission
AI-powered recruitment backend for HR teams: job vacancy creation, form-based applications without CVs, AI candidate screening and ranking, explainable AI decisions, and ticket-based status tracking.

## Critical Rules
- Keep feature flow directional: `routers -> services -> repositories -> models`.
- Never raise `HTTPException` anywhere in feature code, including routers, services, and dependencies. Raise `BaseDomainException` subclasses only. Never raise `BaseDomainException` directly.
- All responses must use `StandardResponse` with `{success, message, data, errors, meta}`.
- All user-facing messages, labels, statuses, and errors must map through Indonesian localization helpers (`get_label` with `ERR_*` constants). Never use hardcoded Indonesian strings in app logic.
- Domain constants and enums must have a single source of truth in `app/shared/constants` or `app/shared/enums`. Avoid duplicate definitions in `settings.py`.
- All I/O must be async-safe. Offload blocking SDK or file work.
- Services own `db.commit()`. Repositories own `db.add()`, `db.flush()`, and `db.refresh()`.
- Never add files directly to feature root. Use `routers/`, `services/`, `repositories/`, `schemas/`, `models/`, or `tasks/`.
- Backend, database, and AI internals stay in English.
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
- Skill matching must use structured `JobRequirement` only. Never infer skill requirements from `job.description`.
- `confidence_score` is governance signal, not direct numeric penalty. Low confidence or insufficient structured skill requirements must force `UNDER_REVIEW`.
- Component scoring uses anchored internal ratings `1-5`, mapped deterministically to `20-100`, then combined by weighted final score.
- Education and experience relevance must come from structured `JobRequirement`, not free-text description fallback.
- `CandidateScore.scoring_breakdown` is required explainability payload for current scoring flow.
- Application flow: `APPLIED -> DOC_CHECK -> AI_PROCESSING -> AI_PASSED/UNDER_REVIEW/KNOCKOUT -> INTERVIEW -> OFFERED -> HIRED`, with rejection and document-failed exits.
- Public applicants have no login. Submission returns `TKT-YYYY-NNNNN`.
- Notification v1 is internal in-app only for active `HR` and `SUPER_ADMIN` users. Applicants stay on email/ticket flow.
- Notification delivery v1 uses polling REST, not WebSocket. Primary endpoints are list + unread summary.
- Notification payload contract uses `entity_type` + `entity_id` for frontend navigation. `read_at` must be maintained with `is_read`.
- Default scoring weights: Skill Match 40, Experience 20, Education 10, Portfolio 10, Soft Skill 10, Admin Complete 10.
- Knockout actions: `auto_reject` or `pending_review`.
- Dashboard ("Pulse") stays lightweight and real-time oriented. Reports ("Brain") can perform heavier historical aggregation with date filters.
- Password reset uses a 2-stage OTP flow: request (6-digit OTP generated, hashed in `PasswordResetOtp` table, and sent via Taskiq) and confirm (verifies OTP, resets password, increments user `token_version` to invalidate old sessions, and auto-logins user).
- Private job access is supported via a unique `apply_code`. If a public applicant searches using an exact `apply_code` (as query `q`), the system will return the matching private job.
- Document upload validation uses case-insensitive enum value mapping (matching lowercase values of `DocumentType` like `identity_card`, `degree`, etc.) when receiving files prefixed with `file_`.
- User and Company pagination queries must always return results ordered by `created_at` in descending order by default.

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
- scoring changes do not reintroduce CV-centric parsing path
- scoring changes preserve `scoring_breakdown` explainability payload
- skill scoring never falls back to `job.description`
- low confidence / insufficient structured requirements still map to `UNDER_REVIEW`

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
