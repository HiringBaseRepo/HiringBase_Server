# AGENTS.md — HiringBase AI Context

## System Overview
AI-powered recruitment backend for HR teams: job vacancy creation, form-based applications (No CV), AI candidate screening & ranking, explainable AI decisions, and ticket-based status tracking.

## Tech Stack
| Layer | Technology |
|---|---|
| Framework | FastAPI (Async), Python 3.12+ |
| Database | PostgreSQL (cloud) Neon DB | SQLAlchemy 2.0 (Async), Alembic |
| Validation | Pydantic v2 |
| Security | JWT (python-jose), Bcrypt (passlib) |
| AI/NLP | HuggingFace Inference API (`paraphrase-multilingual-MiniLM-L12-v2`). No local ML libs. |
| OCR | Mistral Document AI (PDF & Image via R2 URL) |
| Cache & Tasks | Upstash Redis (256MB) — Taskiq Broker + Async Caching |
| Logging | Structlog (JSON/pretty), UUID Request-ID, Audit Context |
| Storage | Cloudflare R2 (S3-compatible, Boto3) |

## Architecture Principles
1. **Layer 1 — Deterministic**: Scoring, knockout, ranking via form answers (`ApplicationAnswer`).
2. **Layer 2 — NLP/Embeddings**: Skill matching (cosine similarity) + soft skill keyword scorer.
3. **Layer 3 — LLM**: Natural language explanation + Semantic Red Flag Detection.
4. **Exception Handling**: `BaseDomainException` → global HTTP handler. Never raise `HTTPException` anywhere in features (including Services, Routers, and Dependencies).
5. **Distributed Processing**: Heavy AI (OCR, LLM, Semantic Matching) offloaded via Taskiq + Redis.
6. **Localization**: Backend/DB/AI use English; all user-facing strings (labels, status, messages, errors) mapped to Indonesian via `app/shared/helpers/localization.py`.
7. **Security & Audit**:
   - IP & User-Agent auto-captured by middleware via `contextvars` — do NOT pass manually.
   - Every `UPDATE` must snapshot old values with `get_model_snapshot` before modifying.
   - AI scoring weight changes must be recorded in Audit Log.
   - Dashboard ("Pulse"): lightweight real-time aggregation. Reports ("Brain"): complex historical aggregation with date filters.
8. **Deployment (Render)**: Web API and Taskiq Worker run as separate Docker services. Heavy inference offloaded to external APIs to fit 512MB RAM free tier limit.

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
- Raise `BaseDomainException` subclasses only — **never** `HTTPException` in any feature layer (Routers, Dependencies, Services)
- Heavy libraries imported lazily (inside functions or via background workers)
- Never add files directly to feature root — always use `routers/`, `services/`, `repositories/`, `schemas/`, `models/`

## Feature Layer Rules

**Direction**: `routers/ → services/ → repositories/ → models/`

### Routers (`routers/router.py`) — HTTP concerns only
✅ `APIRouter`, path ops, tags, response models, `StandardResponse` wrapping  
❌ **No `HTTPException`** (use `BaseDomainException`), no SQLAlchemy queries, no DB operations, no business logic, no large mapping loops

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

### AI Caching Strategy (`app/core/cache/`)
To optimize API costs and latency, expensive AI results are cached in Upstash Redis:
- **Semantic Matcher**: HF Inference API results cached for **24 hours**.
- **OCR Engine**: Mistral OCR text results cached for **1 hour**.
- **Soft Skill Scorer**: LLM scoring results cached for **24 hours**.
- **Efficiency**: Keys use MD5 hashing to minimize memory usage on 256MB free tier.

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
ruff check . && black .                                    # Lint + format
docker build -t hirebase .                                # Build Docker image
docker run -p 10000:10000 hirebase                        # Test Docker locally
```