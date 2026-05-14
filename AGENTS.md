# AGENTS.md - HiringBase AI Context

## Mission
HiringBase is an AI-powered recruitment backend for HR teams. The system supports vacancy creation, form-based applications without CVs, AI candidate screening and ranking, explainable decisions, and ticket-based applicant tracking.

## Core Stack
- Framework: FastAPI, Python 3.12+
- Database: PostgreSQL, SQLAlchemy 2.0 async, Alembic
- Validation: Pydantic v2
- Security: JWT (`python-jose`), bcrypt (`passlib`)
- AI: HuggingFace Inference API, Mistral OCR, Groq LLM fallback flows
- Tasks and cache: Taskiq + Upstash Redis
- Logging: Structlog with request ID and audit context
- Storage: Cloudflare R2 via async wrappers

## Non-Negotiable Rules
- Keep feature flow directional: `routers -> services -> repositories -> models`.
- Never raise `HTTPException` inside feature code, including routers, services, and dependencies. Raise `BaseDomainException` subclasses only.
- All responses must use `StandardResponse`.
- All I/O must be async-safe. Offload blocking file or SDK work.
- Services own `db.commit()`. Repositories own `db.add()`, `db.flush()`, and `db.refresh()`.
- Never add files directly to a feature root. Use `routers/`, `services/`, `repositories/`, `schemas/`, `models/`, or `tasks/`.
- Backend, database, and AI internals stay in English. User-facing text must map through Indonesian localization helpers.

## Architecture Rules

### Routers
Allowed:
- FastAPI routing, dependencies, request parsing, response wrapping, tags, and status-code-level HTTP concerns

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
- ticket and token generation
- password hashing
- score and knockout orchestration
- audit intent
- `db.commit()`

Forbidden:
- `db.add()`, `db.flush()`, `db.refresh()`
- complex query building
- raw HTTP response shaping
- hardcoded DB constraints that belong in repositories or models

### Repositories
Allowed:
- SQLAlchemy selects, inserts, updates, deletes
- pagination
- eager loading
- `db.add()`, `db.flush()`, `db.refresh()`

Forbidden:
- business decisions
- password hashing
- token or ticket generation
- AI, OCR, file-storage orchestration
- HTTP response logic

### Schemas
Use explicit Pydantic request and response models. Prefer typed DTOs over raw `dict` payloads.

### Models
Use string-based relationships and `TYPE_CHECKING` hints when needed. Keep Alembic-visible model aggregation in `app/features/models.py`.

## Business Constraints
- No CV parsing in the scoring engine. Form answers are the source of truth.
- Application flow: `APPLIED -> DOC_CHECK -> AI_PROCESSING -> AI_PASSED/UNDER_REVIEW/KNOCKOUT -> INTERVIEW -> OFFERED -> HIRED`, with rejection and document-failed exits.
- Public applicants have no login. Submission returns a `TKT-YYYY-NNNNN` ticket.
- AI scoring weight changes must create audit logs.
- Every update must snapshot old values with `get_model_snapshot` before mutation.
- IP and User-Agent come from middleware contextvars. Do not pass them manually.

## AI and Worker Rules
- Heavy AI work must run through Taskiq workers or equivalent async-safe offloading.
- Prefer deterministic fallbacks on final retry rather than hard failure.
- Preload ORM relationships for async worker jobs to avoid `MissingGreenlet`.
- Normalize red-flag payloads to `{message, risk_level, type}`.
- Cache expensive AI outputs when the project already defines a cache path.
- Do not add local ML libraries for embedding or OCR workloads.

## Storage Rules
- Documents: `documents/<uuid>.pdf`
- Portfolios: `portfolios/<uuid>.<ext>`
- Company logos: `company-logos/<uuid>.<ext>`
- Company assets: `company-assets/<uuid>.<ext>`
- Job attachments: `job-attachments/<uuid>.<ext>`
- Uploads must use async wrappers. If DB commit fails after upload, attempt best-effort rollback deletion.

## API Conventions
- Auth uses bearer tokens in the `Authorization` header.
- Use `Annotated` dependencies.
- Reuse dependency aliases from `app.features.auth.dependencies.auth` when available: `DbDep`, `CurrentUserDep`, `HrUserDep`, `SuperAdminDep`.
- Feature routers live at `app.features.<feature>.routers.router`.

## Operational Notes
- Use Structlog, not `print()`, for runtime debugging in feature flow.
- Keep heavy imports lazy when they are not needed on the hot path.
- Dashboard queries should stay lightweight and real-time oriented.
- Reports may contain heavier historical aggregation with date filters.

## Definition of Done for AI Changes
Before finishing a task, verify:
- the touched files stay in the correct layer
- no forbidden DB calls leaked into services
- no business logic leaked into routers or repositories
- all user-facing responses still use `StandardResponse`
- exceptions use domain exceptions, not `HTTPException`
- async safety and audit requirements remain intact
