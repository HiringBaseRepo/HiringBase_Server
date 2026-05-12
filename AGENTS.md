# AGENTS.md — HiringBase AI Context

## System Overview
AI-powered recruitment backend for HR teams: job vacancy creation, form-based applications (No CV), AI candidate screening & ranking, explainable AI decisions, and ticket-based status tracking.

## Tech Stack
| Layer | Technology |
|---|---|
| Framework | FastAPI (Async), Python 3.12+ |
| Database | PostgreSQL, SQLAlchemy 2.0 (Async), Alembic |
| Validation | Pydantic v2 |
| Security | JWT (python-jose), Bcrypt (passlib) |
| AI/NLP | Sentence Transformers (`paraphrase-multilingual-MiniLM-L12-v2`), Scikit-learn, NumPy |
| OCR | Mistral Document AI (PDF & Image via R2 URL) |
| Background Tasks | Taskiq + Upstash Redis (SmartRetryMiddleware) |
| Logging | Structlog (JSON/pretty), UUID Request-ID, Audit Context |
| Storage | Cloudflare R2 (S3-compatible, Boto3) |

## Architecture Principles
1. **Layer 1 — Deterministic**: Scoring, knockout, ranking via form answers (`ApplicationAnswer`).
2. **Layer 2 — NLP/Embeddings**: Skill matching (cosine similarity) + soft skill keyword scorer.
3. **Layer 3 — LLM**: Natural language explanation + Semantic Red Flag Detection.
4. **Exception Handling**: `BaseDomainException` → global HTTP handler. Never raise `HTTPException` in services.
5. **Distributed Processing**: Heavy AI (OCR, LLM, Semantic Matching) offloaded via Taskiq + Redis.
6. **Localization**: Backend/DB/AI use English; all user-facing strings (labels, status, messages, errors) mapped to Indonesian via `app/shared/helpers/localization.py`.
7. **Security & Audit**:
   - IP & User-Agent auto-captured by middleware via `contextvars` — do NOT pass manually.
   - Every `UPDATE` must snapshot old values with `get_model_snapshot` before modifying.
   - AI scoring weight changes must be recorded in Audit Log.
   - Dashboard ("Pulse"): lightweight real-time aggregation. Reports ("Brain"): complex historical aggregation with date filters.

## Project Structure
```
/app
├── ai/          # ocr/, parser/, matcher/, nlp/, scoring/, redflag/, explanation/, validator/, llm/
├── core/        # config/, database/, exceptions/, security/, tkq.py
├── features/    # Feature-based DDD modules
│   └── <feature>/
│       ├── routers/      # HTTP only (router.py)
│       ├── tasks/        # Background tasks
│       ├── services/     # Business logic & orchestration
│       ├── repositories/ # SQLAlchemy data access
│       ├── schemas/      # Pydantic schemas
│       └── models/       # SQLAlchemy models (__init__.py)
│   └── models.py         # Central aggregator for Alembic
├── shared/      # enums/, constants/, schemas/, helpers/localization.py
├── tests/       # unit/, integration/, e2e/
└── main.py
```

## Database Schema (Key Tables)
`companies`, `users`, `jobs`, `job_requirements`, `job_scoring_templates`, `job_form_fields`, `job_knockout_rules`, `applications`, `application_answers` (`value_text`, `value_number`), `application_documents` (**NO CV**), `candidate_scores`, `application_status_logs`, `tickets` (TKT-YYYY-NNNNN), `interviews`, `notifications`, `audit_logs`

## Business Rules

### Default Scoring Weights
Skill Match 40% | Experience 20% | Education 10% | Portfolio 10% | Soft Skill 10% | Admin Complete 10%

### Knockout Rule Types
| Type | Operators | Example |
|---|---|---|
| `document` | n/a | Must have Identity Card, Degree |
| `experience` | gte, gt, lt, lte, eq | Min 2 years |
| `education` | gte | Min Bachelor's |
| `boolean` | eq, neq | Willing to WFO = yes |
| `range` | lte, gte | Salary ≤ 10jt |

**Knockout Actions**: `auto_reject` or `pending_review`

### Application Status Flow
```
APPLIED → DOC_CHECK → [DOC_FAILED]
        → AI_PROCESSING → AI_PASSED / UNDER_REVIEW / KNOCKOUT
        → INTERVIEW → OFFERED → HIRED
        → REJECTED (any stage)
```

### Public Applicant Flow (Ticket-Based)
Applicants have no login. Flow: fill form + upload docs → system validates (fields, docs, file format, email dedup) → atomic save to R2 + DB → returns `TKT-YYYY-NNNNN`. Applicants stored in `users` table as contacts without credentials.

## API Conventions
- All responses: `StandardResponse` wrapper `{success, message, data, errors, meta}`
- Pagination: `PaginationParams` (`page`, `per_page`)
- Auth: Bearer Token in `Authorization` header
- Use `Annotated` for FastAPI dependencies
- Router imports: `app.features.<feature>.routers.router`
- Auth dependencies: `app.features.auth.dependencies.auth`

## Coding Standards
- `snake_case` for functions/variables/files, `PascalCase` for classes
- All I/O must be `async`
- Full type hints on all function signatures
- Raise `BaseDomainException` subclasses only — **never** `HTTPException` in services
- Heavy libraries imported lazily (inside functions or via background workers)
- Never add files directly to feature root — always use `routers/`, `services/`, `repositories/`, `schemas/`, `models/`

## Feature Layer Rules

**Direction**: `routers/ → services/ → repositories/ → models/`

### Routers (`routers/router.py`) — HTTP concerns only
✅ `APIRouter`, path ops, tags, response models, dependencies, `StandardResponse` wrapping  
❌ No SQLAlchemy queries, no DB operations, no business logic, no large mapping loops

### Services (`services/service.py`) — Business logic & orchestration
✅ Domain rules, permissions, ownership checks, status transitions, ticket generation, password hashing, token creation, score/knockout decisions, audit-log intent, `db.commit()`  
❌ No `db.flush()`, `db.refresh()`, `db.add()`, no complex query building, no hardcoded DB constraints

### Repositories (`repositories/`) — Data access only
✅ SQLAlchemy queries (select/insert/update/delete), pagination, `db.add()`, `db.flush()`, `db.refresh()`  
❌ No business decisions, no password hashing, no token/ticket generation, no AI/OCR/file ops, no HTTP responses

### Schemas (`schemas/`) — Pydantic contracts
Request bodies, response shapes, filter objects, form payloads, DTOs. Explicit schemas over raw `dict`.

### Models (`models/__init__.py`) — SQLAlchemy models
String-literal relationships, `TYPE_CHECKING` for cross-domain hints. Aggregated in `app/features/models.py` for Alembic.

**Transaction Rule**: Services own `db.commit()`. Repositories handle flush/refresh. Services finalize.

## File Storage (Cloudflare R2)
- Documents: `documents/<uuid>.pdf`
- Portfolios: `portfolios/<uuid>.<ext>`
- Company Logos: `company-logos/<uuid>.<ext>`
- Company Assets: `company-assets/<uuid>.<ext>`
- Job Attachments: `job-attachments/<uuid>.<ext>`
- Public URL from `R2_PUBLIC_URL`

## AI Implementation

### Distributed Screening Pipeline (Taskiq)
- **Manual Trigger** (default): HR triggers via "Run Screening" to manage API costs.
- **Auto Trigger**: Via `auto_screening` flag on job (to be implemented).
- **Batch Screening**: Hourly periodic task processes all `APPLIED` applications.
- **SmartRetryMiddleware**: Exponential backoff + jitter, max 3 retries for transient failures (Connection/Timeout/5xx). Final attempt forces deterministic fallbacks.
- **ORM Preloading**: All relationships pre-fetched via `selectinload` to prevent `MissingGreenlet` in async workers.

### Scoring Pipeline (Form-based, `app/ai/scoring/engine.py`)
No CV parsing. All data from `ApplicationAnswer` via standard `field_key`:
- `experience_years` → experience score
- `education_level` → education score (SMA, D3, S1, S2, S3)
- `skills` → comma-separated list for Semantic Matcher
- `github_url`, `portfolio_url`, `live_project_url` → portfolio score

**Mathematical Integrity**: Single source of truth in `engine.py`. Education ranks synced with `EDUCATION_RANK` constants. Missing requirements → full score (100%).

### OCR & Validation (`app/ai/ocr/engine.py` + `app/ai/validator/`)
Mistral Document AI for async PDF/image text extraction via R2 URLs. LLM (Groq) validates:
1. Name matches applicant | 2. Valid date/lifetime | 3. Valid document number | 4. Correct doc type | 5. Semantic reasonableness  
Anomalies → `red_flags` (high risk).

### Semantic Matcher (`app/ai/matcher/semantic_matcher.py`)
3-layer skill matching: **Layer 1** Exact → **Layer 2** Synonym map (includes Indonesian terms) → **Layer 3** Sentence Transformer (cosine similarity).

### Soft Skill Scorer (`app/ai/nlp/soft_skill_scorer.py`)
Analyzes all concatenated text answers. Hybrid: 30% keyword baseline + 70% LLM. Fallback to pure keyword if LLM fails. Output: 20–100 per dimension.

### Semantic Red Flag Detector (`app/ai/redflag/detector.py`)
LLM-powered analysis of form data + OCR text. Cross-checks data mismatches (e.g., exp years vs. degree grad year). Fallback to regex-based detection. Output in Indonesian.

### AI Fallback Strategy (Retry-then-Fallback)
1. **Phase 1**: Taskiq retries up to 3× with increasing delay.
2. **Phase 2 (final attempt)**:
   - OCR → empty string (flag for manual review)
   - LLM Validation → "Fallback Pass" + warning flag
   - Red Flag → regex-based detection
   - Soft Skill → pure keyword scoring
   - Explanation → template-based logic
3. All failures and fallback triggers are logged.

## Security
- Passwords: bcrypt via Passlib (`bcrypt==3.2.0`)
- **Stateful JWT**: Access tokens in JSON body; Refresh tokens in HTTP-Only Cookies
- **Advanced Auth**: Refresh Token Rotation (one-time use), Reuse Detection (force logout on theft), Global Kill Switch via `token_version`
- Rate limiting: 60 req/min per IP
- File type + size validation
- SQL injection: protected by SQLAlchemy ORM
- XSS: protected by JSON serialization
- Password reset: `secrets.token_urlsafe(32)` + SHA-256 hash

## Logging & Observability
- **Structlog**: JSON in production (non-TTY), pretty console in dev (TTY)
- **Request Tracking**: UUID4 per request, returned as `X-Request-ID` header; middleware logs method, path, status, latency
- **Exception Monitoring**: All global handlers log errors; 500s include structured tracebacks
- **Context Propagation**: `structlog.contextvars` for async-safe state

## Development Commands
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload                            # Dev server
taskiq worker app.core.tkq:broker app.main:app            # Background worker
alembic revision --autogenerate -m "description"          # Create migration
alembic upgrade head                                       # Apply migration
pytest app/tests/ -v                                       # All tests (121)
pytest app/tests/unit/ -v                                  # Unit only (89)
pytest app/tests/integration/ -v                           # Integration only (32)
ruff check . && black .                                    # Lint + format
```

## Testing

### Test Summary: 121 Tests PASSED (89 unit + 32 integration)

**Unit Tests (89)**
| File | Coverage | Count |
|---|---|---|
| `test_auth.py` | JWT, password hashing | 2 |
| `test_ai_scoring.py` | Parser, red flags, soft skill, scoring helpers | 21 |
| `test_explanation_logic.py` | Explanation template + fallback | 3 |
| `test_knockout_rules.py` | All knockout types with mocks | 20 |
| `test_semantic_matcher.py` | Exact, synonym, embedding layers | 10 |
| `test_screening_pipeline.py` | Orchestrator: DOC_FAILED, KNOCKOUT, AI_PASSED, UNDER_REVIEW, red flags, weighted score | 11 |
| `test_validator_step.py` | OCR+LLM routing, flag generation, non-required skip | 8 |
| `test_document_validator.py` | LLM fallback, parse response, OCR internals | 14 |

**Integration Tests (32)**
| File | Count |
|---|---|
| `test_public_application.py` (submit, duplicate 409, ticket tracking) | 3 |
| `test_auth_flows.py` (register, login, get me, logout) | 4 |
| `test_user_management.py` (RBAC, tenant isolation) | 2 |
| `test_scoring_templates.py`, `test_job_forms.py`, `test_companies.py`, `test_audit_logs.py`, `test_notifications.py` | 1 each |
| `test_hr_workflows.py` (vacancy lifecycle, screening, interviews) | 4 |
| `test_jobs_public.py` | 2 |
| `test_auth_security.py` (token rotation, reuse detection, kill switch) | 5 |
| `test_document_pipeline.py` | 3 |
| `test_ranking.py` (custom weights, tenant isolation, top-N, pagination) | 4 |

### Mocking Infrastructure (`app/tests/conftest.py`)
- `mock_r2` → mocks `boto3.client()` for R2
- `mock_groq` → mocks `call_llm` and `validate_document_content`
- `mock_ocr_engine` → mocks `extract_text_from_document()`
- `test_db_session` → function-scoped engine, auto-rollback per test
- `auth_headers` → valid JWT with `token_version` + `sub: str(user_id)`

### Unit Test Isolation (`app/tests/unit/conftest.py`)
Overrides all autouse fixtures so AI module tests call real functions. Internal AI modules tested via **direct namespace patching** (`validator_module.settings`, `ocr_module._download_file`).

### Call-Site Mocking Pattern
- Patch `app.core.database.session.get_session` (source), not the service attribute.
- Use `@asynccontextmanager` wrapper as mock session.
- Patch repo functions in service namespace: `app.features.screening.services.service.<func>`.

### Zero External Dependency Testing
All 121 tests pass without external API credentials (Groq/R2/Mistral all mocked).

## Critical Testing Notes
- `employment_type` → must use `EmploymentType.FULL_TIME` (enum object, not string)
- `description` on `Job` → NOT NULL, required in all fixtures
- JWT tokens → must include `token_version: int` and `sub: str(user_id)`
- Duplicate applications → `409 Conflict`
- `InterviewScheduledResponse` → field is `interview_id` (not `id`)
- Screening endpoint → `POST /api/v1/screening/applications/{id}/run`
- `pytest.ini` → `asyncio_default_test_loop_scope = function`
- Do NOT delete `app/tests/unit/conftest.py`
- `doc_type.value` sent to LLM validator as **lowercase** (e.g., `"identity_card"`)

## Known Limitations
1. `password_reset_tokens` table not yet created (needs Alembic migration).
2. Email delivery not configured — tokens logged to console in dev.
3. LLM: Groq with `qwen/qwen3-32b` or `llama3-70b-8192`.

## Pending Work
**Integration Tests Needed**: `scoring_templates`, `companies`, `users`, `notifications`, `job_forms`, `audit_logs`  
**Unit Tests Needed**: `app/ai/explanation/generator.py`, `app/ai/llm/client.py`, `app/ai/scoring/engine.py`  
**Feature**: `auto_screening` flag on job (auto-trigger on submission)