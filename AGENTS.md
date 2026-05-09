# AGENTS.md — AI Context for HiringBase..

## System Overview

This is the **backend** of an AI-powered recruitment assistant that helps HR teams:
- Create job vacancies with custom forms
- Accept applications via form responses and document uploads (Non-CV)
- Automatically screen candidates using a hybrid AI engine based on form data
- Rank applicants by weighted score
- Provide explainable AI reasoning for every decision
- Track application status via tickets

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous)
- **Language**: Python 3.12+
- **Database**: PostgreSQL with [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async) & [Alembic](https://alembic.sqlalchemy.org/)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/)
- **Security**: JWT (python-jose), Bcrypt (passlib)
- **AI/NLP**: Sentence Transformers (`paraphrase-multilingual-MiniLM-L12-v2`), Scikit-learn, NumPy
- **OCR**: Mistral Document AI (PDF & Image via URL)
- **Background Tasks**: [Taskiq](https://taskiq-python.github.io/) with Redis Broker & **SmartRetryMiddleware**
- **Logging**: [Structlog](https://www.structlog.org/) with JSON & Request Context
- **Middleware**: Custom Logging Middleware with UUID Request-ID and **Audit Context Extraction**
- **Context Management**: Python `contextvars` for async-safe request metadata (IP, User-Agent)
- **Storage**: Cloudflare R2 (S3-compatible via Boto3)
- **Message Broker**: [Upstash Redis](https://upstash.com/) (Serverless)

## Architecture Principles

1. **Layer 1 — Deterministic Engine**: All scoring, knockout rules, ranking, and validation are rule-based and reproducible, primarily using form answers (`ApplicationAnswer`).
2. **Layer 2 — NLP / Embeddings**: Skill matching + cosine similarity via `sentence-transformers` using skills from form data. Soft skill scoring via keyword NLP classifier on concatenated text answers.
3. **Layer 3 — LLM**: Used for natural language explanation generation and **Semantic Red Flag Detection**.
4. **Exception Handling**: Centrally managed via `BaseDomainException`. Service layers raise domain exceptions which are mapped to HTTP responses by a global exception handler.
5. **Distributed Processing — Taskiq**: Heavy AI workloads (OCR, LLM Validation, Semantic Matching) are offloaded to background workers using Taskiq and Redis to maintain API responsiveness.
6. **Localization Strategy — English Core, Localized Presentation**: The backend logic, database enums, and API identifiers use English to ensure stability and AI compatibility. Presentation for end-users (Labels, Status, AI Explanations, Error Messages, and API Success Messages) is mapped to Indonesian via display labels in API schemas, centralized exception handlers, and a specialized localization helper for all user-facing strings.
7. **Security & Audit Logging Standard**: 
    - **Otomatisasi IP & User-Agent**: Metadata request ditangkap otomatis oleh middleware dan disimpan di `contextvars`. Jangan meneruskan IP secara manual di fungsi service.
    - **Snapshot Data (Old Values)**: Setiap `UPDATE` wajib merekam data lama menggunakan `get_model_snapshot` sebelum modifikasi dilakukan untuk transparansi penuh di Audit Log.
    - **Transparansi AI**: Perubahan bobot kriteria penilaian kandidate harus dicatat sebagai audit log agar keputusan AI tetap dapat dipertanggungjawabkan.
    - **Data Aggregation Strategy**: 
        - **Dashboard ("The Pulse")**: Menggunakan query agregasi ringan untuk data operasional real-time (total aplikasi, kampanye aktif).
        - **Reports ("The Brain")**: Menggunakan query agregasi kompleks (`to_char`, `group_by`) untuk analisis tren historis, distribusi skor, dan efisiensi perusahaan dengan dukungan filter rentang tanggal.

## Project Structure

```text
/app
├── ai/                 # AI Engine logic
│   ├── ocr/            # OCR: Mistral Document AI API integration
│   ├── parser/         # Resume text parser (regex-based)
│   ├── matcher/        # Semantic skill matcher (3-layer: exact, synonym, embedding)
│   ├── nlp/            # Soft skill keyword scorer
│   ├── scoring/        # Standalone scoring engine
│   ├── redflag/        # Red flag detector (Async + LLM-based)
│   ├── explanation/    # Template-based explanation generator
│   ├── validator/      # Semantic document validator (Groq-based)
│   └── llm/            # LLM client (Groq-based)
├── core/               # Global config, DB engine, security, middlewares
│   ├── config/         # Settings & environment variables
│   ├── database/       # SQLAlchemy async engine & Base model
│   ├── exceptions/     # Custom exceptions & Global handlers
│   ├── security/       # JWT & password hashing
│   └── tkq.py          # Taskiq broker configuration
├── features/           # Feature-based modules (Domain Driven)
│   └── <feature_name>/ # e.g., auth, jobs, applications
│       ├── routers/        # FastAPI endpoints only
│       │   └── router.py
│       ├── tasks/          # Background tasks (e.g., screening/tasks.py)
│       ├── services/       # Business logic / orchestration
│       │   ├── service.py  # Main orchestration
│       │   ├── mapper.py   # Data mapping helpers
│       │   ├── validator.py # Validation helpers
│       │   └── parser.py    # Data parsing helpers
│       ├── repositories/   # SQLAlchemy query/data access layer
│       ├── schemas/        # Pydantic validation schemas
│       └── models/         # SQLAlchemy models (Package)
│           └── __init__.py
│   # Central aggregator for Alembic:
│   └── models.py       # Aggregates and re-exports all models from features/*/models
├── shared/             # Shared utilities & global schemas
│   ├── enums/          # Application enums (UserRole, ApplicationStatus, etc)
│   ├── constants/      # scoring.py, storage.py, errors.py
│   └── schemas/        # StandardResponse, PaginationParams
├── tests/              # Unit, integration, and E2E tests
│   ├── unit/           # test_auth.py, test_ai_scoring.py, test_knockout_rules.py, test_semantic_matcher.py
│   ├── integration/    # DB + API flow tests
│   └── e2e/            # Full screening flow tests
└── main.py             # Application entry point
```

## Database Schema (Key Tables)

- `companies` — Tenant / company accounts
- `users` — Super Admin, HR (Applicants use ticket-based public flow without login)
- `jobs` — Vacancies with multi-step setup
- `job_requirements` — Skills, experience, education required
- `job_scoring_templates` — Per-job weighted scoring config
- `job_form_fields` — Custom applicant form fields
- `job_knockout_rules` — Auto-reject / pending rules (`field_key` for lookup answers)
- `applications` — Candidate applications
- `application_answers` — Form responses (`value_text`, `value_number`)
- `application_documents` — Uploaded files (Identity Card, Degree, etc. — **NO CV**)
- `candidate_scores` — AI computed scores + explanation
- `application_status_logs` — Full status history
- `tickets` — Public tracking codes (TKT-YYYY-NNNNN)
- `interviews` — Scheduled interviews
- `notifications` — User notifications
- `audit_logs` — Immutable change log

## Business Rules

### Scoring Weights (Default)
- Skill Match: 40%
- Experience: 20%
- Education: 10%
- Portfolio: 10%
- Soft Skill: 10%
- Administrative Complete: 10%

### Knockout Rule Types (ALL IMPLEMENTED)

| Type | Operator | Example |
|---|---|---|
| `document` | n/a | Must have Identity Card, Degree |
| `experience` | gte, gt, lt, lte, eq | Min 2 years experience |
| `education` | gte | Min Bachelor's Degree |
| `boolean` | eq, neq | Willing to WFO = yes |
| `range` | lte, gte | Expected salary <= 10jt |

### Knockout Actions
- `auto_reject` — Immediate rejection
- `pending_review` — Flag for manual review

### Application Status Flow
```
APPLIED → DOC_CHECK → [DOC_FAILED]
        → AI_PROCESSING → AI_PASSED / UNDER_REVIEW / KNOCKOUT
        → INTERVIEW → OFFERED → HIRED
        → REJECTED (at any stage)
```

### Public Applicant Flow (Ticket-Based)
Applicants do not have login accounts. The application flow is entirely public:
1. Applicants fill out the public form and upload mandatory documents.
2. System validates mandatory fields, required documents (based on filename), file formats, and email duplication before saving data.
3. Atomic transaction saves data to R2 and Database, then returns a Ticket number (`TKT-YYYY-NNNNN`) to the applicant for status tracking.
Applicants are represented internally in the `users` table (as contacts) without access credentials.

## API Conventions

- **Standard Response**: All responses MUST use `StandardResponse` wrapper: `{success, message, data, errors, meta}`.
- **Pagination**: Use `PaginationParams` with `page` and `per_page`.
- **Auth**: Bearer Token in `Authorization` header.
- **Dependency**: Use `Annotated` for FastAPI dependencies (e.g., `db: Annotated[AsyncSession, Depends(get_db)]`).
- **Router imports**: Routers live in `app.features.<feature>.routers.router`.
- **Auth dependencies**: Import auth dependencies from `app.features.auth.dependencies.auth`.

## Coding Standards

- **Naming**: `snake_case` for functions/variables/files, `PascalCase` for classes.
- **Async First**: All I/O operations (DB, API calls, File) must be `async`.
- **Typing**: Use Python type hints for all function signatures.
- **Errors**: Raise custom exceptions from `app.core.exceptions` (inheriting from `BaseDomainException`). **DO NOT raise `HTTPException` in service layers.**
- **Import lazy**: Heavy libraries (sentence-transformers) are imported inside functions or managed via background workers.
- **Feature layout**: Do not add new route/service/schema files directly under a feature root. Use `routers/`, `services/`, `repositories/`, `schemas/`, and `models/`.

## Feature Layer Rules

Every feature must keep HTTP, business logic, database access, schemas, and model exports separated. When adding or refactoring a feature, follow this direction:

```text
routers/ -> services/ -> repositories/ -> models.py or models/
          -> schemas/
```

### Routers

`routers/router.py` is only for FastAPI HTTP concerns:
- Define `APIRouter`, path operations, tags, response models, and route metadata.
- Receive request data through Pydantic schemas, `Form`, `File`, `Query`, or `Path`.
- Declare dependencies such as `Depends(get_db)`, `require_hr`, `require_super_admin`, and `get_current_user`.
- Call one service function per endpoint whenever possible.
- Wrap successful responses with `StandardResponse`.

Routers must not contain:
- SQLAlchemy statements such as `select(...)`, joins, counts, or filters.
- Direct DB operations such as `db.execute(...)`, `db.add(...)`, `db.delete(...)`, `db.commit(...)`, or `db.refresh(...)`.
- Business decisions such as duplicate application rules, status transition rules, scoring decisions, password hashing, ticket/apply-code generation, or storage workflows.
- Large response mapping loops. Prefer schema serializers or service-level DTO helpers.

### Services

`services/service.py` is for business logic and orchestration:
- Enforce domain rules, permissions beyond simple route dependencies, ownership checks, and validation that is not purely Pydantic validation.
- Coordinate multiple repositories in one workflow, e.g. public application submission, screening, ranking, job publishing, and password reset.
- Own status transitions, ticket/apply-code generation, password hashing, token creation, score decisions, knockout decisions, and audit-log intent.
- Call AI helpers, storage helpers, security helpers, and repositories.
- Control transaction boundaries consistently. If a workflow changes multiple records, commit at the service boundary after all records are prepared.

Services may receive `AsyncSession`, but they MUST NOT contain:
- Direct ORM mutation logic such as `db.flush()`, `db.refresh()`, or `db.add()`. These are handled by **Repositories**.
- Complex SQLAlchemy query building.
- Hardcoded database constraints.

**Transaction Rule**: Services own the `db.commit()`. Repositories prepare the state (flush), and Services finalize the transaction.

### Repositories

`repositories/` is only for database access:
- Build SQLAlchemy `select`, `insert`, `update`, `delete`, joins, counts, filters, ordering, and pagination queries.
- Provide functions such as `get_by_id`, `get_by_email`, `list_paginated`, `create`, `update`, `soft_delete`, `exists`, and domain-specific query helpers.
- **ORM Synchronization**: Repositories are responsible for `db.add()`, `db.flush()`, and `db.refresh()` to ensure the Model state is synchronized with the database session.
- Return ORM models, scalar values, or simple query result objects to services.
- Keep persistence details in one place so services do not duplicate SQL.

Repositories must not contain business decisions:
- Do not decide whether a candidate should be rejected, whether an HR user may publish a job, or whether an application may proceed.
- Do not hash passwords, generate tokens, generate ticket/apply codes, call AI/OCR, upload files, or format API responses.
- Do not return `StandardResponse` or raise HTTP-layer exceptions.

### Schemas

`schemas/` is for Pydantic request and response contracts:
- Put request bodies, form payload models, filter objects, list item responses, detail responses, and command DTOs here.
- Prefer explicit schemas over raw `dict`, `List[dict]`, or long endpoint parameter lists.
- Use Pydantic validation for field-level rules such as required fields, numeric ranges, enum values, and string formats.
- Keep API response shapes consistent and avoid hand-built dictionaries scattered across routers.

### Models

`models/` is the per-feature package for SQLAlchemy models.
- All models reside in `app/features/<feature>/models/__init__.py`.
- Relationships use string literals (late-binding) to avoid circular imports.
- `TYPE_CHECKING` blocks are used for cross-domain type hinting.
- `app/features/models.py` acts as a central aggregator for Alembic discovery.
- **Migration Status**: Completed. All domain models are now decentralized.

### Layer Compliance Audit

Current status of `app/features` after the router/service/repository/schema migration:

| Feature | Status | Notes |
|---|---|---|
| `users` | Fully compliant | Router delegates to service; Repositories and Schemas active; Models migrated to `users/models`. |
| `auth` | Fully compliant | Refresh token rotation, reuse detection, and custom domain exceptions implemented. |
| `jobs` | Fully compliant | Multi-step vacancy logic decentralized; integrated with Audit Logs. |
| `applications` | Fully compliant | Public apply and status tracking logic decentralized. Models in `applications/models`. |
| `screening` | Fully compliant | Scoring and knockout rules logic decentralized. Models in `screening/models`. |
| `companies` | Fully compliant | Multi-tenant logic decentralized. Models in `companies/models`. |
| `documents` | Fully compliant | R2 and validation logic decentralized. |
| `job_forms` | Fully compliant | Form builder logic decentralized. |
| `scoring` | Fully compliant | Scoring templates decentralized. |
| `ranking` | Fully compliant | Ranking queries decentralized. |
| `tickets` | Fully compliant | Ticket tracking decentralized. |
| `notifications` | Fully compliant | Notification logic decentralized. |
| `reports` | Fully compliant | Migrated to real SQL aggregation (Screening Volume, Match Distribution, Company Activity). |
| `dashboard` | Fully compliant | Optimized as operational "Pulse" with real-time system stats. |
| `interviews` | Fully compliant | Interview scheduling logic decentralized. |
| `audit_logs` | Fully compliant | Audit trail logic decentralized with **Automatic Context Injection** and **Old Value Snapshots**. |

## File Storage

- Cloudflare R2 (S3-compatible)
- Documents: `documents/<uuid>.pdf`
- Portfolios: `portfolios/<uuid>.<ext>`
- Company Assets: `company-assets/<uuid>.<ext>`
- Job Attachments: `job-attachments/<uuid>.<ext>`
- Public URL constructed from `R2_PUBLIC_URL`

## AI Implementation Details

### Distributed Screening Pipeline
Workloads are processed asynchronously using **Taskiq**. When screening is triggered, the API server queues a task in Redis, which is then picked up by a separate worker process. 

**Manual vs Auto Trigger**:
- **Manual Trigger (Default)**: HR users can manually trigger screening for specific applications via the "Run Screening" button in the Dashboard. This is the standard behavior to optimize external AI API costs (Mistral/Groq).
- **Auto Trigger**: Jobs can be configured to automatically trigger screening upon application submission if the `auto_screening` flag is enabled (to be implemented).
- **Batch Screening**: A scheduled background task runs periodically to process pending applications in bulk (implemented).

**Retry Mechanism**:
- **SmartRetryMiddleware**: Implemented with exponential backoff and jitter.
- **Max Retries**: 3 attempts for transient failures (Connection, Timeout, 5xx).
- **Last Attempt Logic**: On the final retry, the system is instructed to use deterministic fallbacks instead of raising exceptions to ensure the screening process completes.

### Scoring Pipeline (Form-based)
The system no longer parses CV files. Data for scoring is taken from `ApplicationAnswer` with standard `field_key`:
- `experience_years`: Used for experience score.
- `education_level`: Used for education score (SMA, D3, S1, S2, S3).
- `skills`: List of skills (comma-separated) for `Semantic Matcher`.
- `github_url`, `portfolio_url`, `live_project_url`: For portfolio score.

### OCR & Validation Pipeline (`app/ai/ocr/engine.py` & `app/ai/validator/`)
- Used for text extraction from supporting documents (Identity Card, Degree).
- **Mistral Document AI**: Fully asynchronous OCR pipeline that handles both text-based and scanned PDFs, as well as images, directly via Cloudflare R2 public URLs.
- **Semantic Document Validation**: OCR text is validated using LLM (Groq) to verify:
  1. Name matches applicant data
  2. Active validity date (or lifetime)
  3. Valid document number format
  4. Correct document type
  5. Content reasonableness (semantic anomaly detection)
  Anomalies are recorded as `red_flags` with a high risk level.

### Semantic Matcher (`app/ai/matcher/semantic_matcher.py`)
- Matches skill list from form answers with `JobRequirement`.
- Layer 1: Exact match, Layer 2: Synonym map, Layer 3: Sentence Transformer.

### Soft Skill Scorer (`app/ai/nlp/soft_skill_scorer.py`)
- Analyzes **combined text from all form answers**.
- Hybrid Engine: Blends keyword baseline (30%) with deep LLM analysis (70%).
- Fallback: Reverts to pure keyword-based if LLM fails.
- Output range: 20–100 per dimension.

### Semantic Red Flag Detector (`app/ai/redflag/detector.py`)
- **LLM-powered**: Analyzes parsed data + raw document text for professional risks.
- **Logical Cross-Check**: Detects mismatches between form data (e.g., Exp Years) vs OCR results (e.g., Degree Grad Year).
- **Deterministic Fallback**: Reverts to regex-based detection if LLM API unavailable.
- **Language Standard**: Logic in English. Human-readable flags + AI summaries in Indonesian.

### AI Fallback Strategy

The system follows a **Retry-then-Fallback** strategy for external API dependencies (Groq/Mistral).

1. **Phase 1: Automatic Retry**: If a transient error occurs (Connection Timeout, Network Error, HTTP 5xx), Taskiq retries the task up to 3 times with increasing delays.
2. **Phase 2: Forced Fallback**: On the final attempt, if the API still fails:
    - **OCR**: Returns empty string (flags for manual review).
    - **LLM Validation**: Returns "Fallback Pass" with warning flag.
    - **Red Flag Detector**: Reverts to deterministic regex-based detection.
    - **Soft Skill Scorer**: Reverts to pure keyword-based scoring.
    - **Explanation Generator**: Reverts to template-based logic.
3. **Audit**: All AI API failures and fallback triggers are logged for observability.

## Development & Commands

- **Run Dev Server**: `uvicorn app.main:app --reload`
- **Run Background Worker**: `taskiq worker app.core.tkq:broker app.main:app`
- **Migrations**:
  - Create: `alembic revision --autogenerate -m "description"`
  - Apply: `alembic upgrade head`
- **Testing**: `pytest app/tests/ -v` (All **107 tests PASSED** — 86 unit + 21 integration)
- **Test AI only**: `pytest app/tests/unit/test_ai_scoring.py -v`
- **Test Knockout**: `pytest app/tests/unit/test_knockout_rules.py -v`
- **Test Semantic Matcher**: `pytest app/tests/unit/test_semantic_matcher.py -v`
- **Test Screening Pipeline**: `pytest app/tests/unit/test_screening_pipeline.py -v`
- **Test Validator Step**: `pytest app/tests/unit/test_validator_step.py -v`
- **Test Document Validator**: `pytest app/tests/unit/test_document_validator.py -v`
- **Test Integration only**: `pytest app/tests/integration/ -v`
- **Linting**: `ruff check .` / `black .`

## Security

- Passwords hashed with bcrypt via Passlib (Pinned: `bcrypt==3.2.0` for compatibility)
- **Stateful JWT Auth**: Access tokens via JSON body, Refresh tokens via **HTTP-Only Cookies**.
- **Advanced Auth Security**: Features **Refresh Token Rotation** (one-time use), **Reuse Detection** (force logout on theft), and **Global Kill Switch** via `token_version`.
- Rate limiting per IP (60 req/min default)
- File type and size validation
- SQL injection protected by SQLAlchemy ORM
- XSS protected by JSON response serialization
- Password reset: token `secrets.token_urlsafe(32)`, SHA-256 hash

## Logging & Observability

### Structured Logging (Structlog)
- **JSON Output**: Automatically enabled in non-TTY or production environments for log aggregation (ELK, Datadog).
- **Pretty Console**: Enabled in development (TTY) with colors and formatted tracebacks.
- **Context Propagation**: Uses `structlog.contextvars` to maintain state across async tasks.

### Request Tracking
- **Request ID**: Every request is assigned a unique UUID4.
- **Middleware**: `LoggingMiddleware` captures:
    - HTTP Method & Path
    - Response Status Code
    - Processing Latency (Duration)
- **Traceability**: The `request_id` is returned in the `X-Request-ID` header and attached to every log entry within that request's scope.

### Exception Monitoring
- **Automatic Logging**: All global exception handlers (`validation`, `sqlalchemy`, `integrity`, `generic`) now log error details.
- **Tracebacks**: Internal Server Errors (500) automatically include structured tracebacks in logs for rapid debugging.

## Testing Strategy

### Unit Tests (89 tests)
- `test_auth.py` — JWT encode/decode, password hashing (2 tests)
- `test_ai_scoring.py` — Resume parser, red flag detector, soft skill scorer, scoring helpers (21 tests)
- `test_explanation_logic.py` — **NEW**: AI explanation template and fallback logic (3 tests)
- `test_knockout_rules.py` — All knockout rule types with mocks (20 tests)
- `test_semantic_matcher.py` — Skill matching logic with exact, synonym, and embedding layers (10 tests)
- `test_screening_pipeline.py` — Orchestrator `process_screening`: DOC_FAILED, KNOCKOUT, AI_PASSED, UNDER_REVIEW, red flags, weighted score (11 tests)
- `test_validator_step.py` — `run_document_semantic_check`: routing OCR+LLM, flag generation, non-required doc skip (8 tests)
- `test_document_validator.py` — `validate_document_content` (LLM fallback, parse response) + OCR engine internals `_download_file`, `_extract_text_pdf`, `_extract_text_image`, `_is_image` (14 tests)

### Integration Tests (32 tests)
- `test_public_application.py` — Public application submission, duplicate 409, ticket tracking (3 tests)
- `test_auth_flows.py` — **NEW**: Registration, Login, Get Me, and Logout flows (4 tests)
- `test_user_management.py` — **NEW**: RBAC and tenant isolation for user listing (2 tests)
- `test_scoring_templates.py` — **NEW**: CRUD for weighted scoring templates (1 test)
- `test_job_forms.py` — **NEW**: Custom form field management (1 test)
- `test_companies.py` — **NEW**: Super Admin company management (1 test)
- `test_audit_logs.py` — **NEW**: Audit trail verification for company actions (1 test)
- `test_notifications.py` — **NEW**: Notification listing and read status management (1 test)
- `test_hr_workflows.py` — HR vacancy lifecycle, screening run, tenant isolation, interview scheduling (4 tests)
- `test_jobs_public.py` — Public jobs endpoints (list, detail with form fields) (2 tests)
- `test_auth_security.py` — Refresh token rotation, reuse detection kill switch, concurrent rotation, invalid format, token version (5 tests)
- `test_document_pipeline.py` — Document completeness check, full pipeline with all docs, tenant isolation (3 tests)
- `test_ranking.py` — Ranking with custom weights, tenant isolation, top-N limit, pagination (4 tests)

### Total Status: 121 Tests PASSED (100% Feature Coverage)

### Mocking Infrastructure
Global test fixtures in `app/tests/conftest.py` provide comprehensive mocking:

- **R2 Storage**: `mock_r2` fixture mocks `boto3.client()` for Cloudflare R2 operations
- **Groq LLM**: `mock_groq` fixture mocks `app.ai.llm.client.call_llm` and `app.ai.validator.document_validator.validate_document_content`
- **OCR Engine**: `mock_ocr_engine` fixture mocks `extract_text_from_document()` for text extraction
- **Database Isolation**: `test_db_session` fixture — function-scoped engine per-test, auto-rollback after completion. Override via `override_db` autouse fixture.
- **Authentication**: `auth_headers` fixture generates valid JWT tokens (with `token_version` and integer `sub`) for HR user testing

### Unit Test Isolation (Local Conftest)
`app/tests/unit/conftest.py` overrides **all** autouse fixtures from root conftest so AI module unit tests can call original functions:
- `mock_ocr_engine`, `mock_groq`, `mock_r2` → no-op in unit scope
- `db_cleanup`, `override_db`, `mock_get_session` → no-op in unit scope
- Internal AI tests (`validate_document_content`, `extract_text_from_document`) are tested via **direct module namespace patching** (`validator_module.settings`, `ocr_module._download_file`) to avoid conflicts with global mocks.

### Call-Site Mocking Pattern
To avoid lazy import issues in `process_screening` (which imports `get_session` inside the function body):
- Patch `app.core.database.session.get_session` (source module) — not the attribute in the service module.
- Use `@asynccontextmanager` wrapper as mock session context.
- Patch all repository functions in service namespace: `app.features.screening.services.service.<func_name>`.

### Zero External Dependency Testing
All tests run successfully without external API credentials:
- Groq LLM mocks return structured responses when `GROQ_API_KEY` is missing
- R2 storage mocks simulate successful file uploads and URL generation
- OCR engine mocks provide consistent text extraction results
- All AI services have proper fallback mechanisms implemented

### Test Execution Commands
```bash
# Run all tests (107 total)
venv/bin/pytest app/tests/ -v --tb=short

# Run unit tests only (86 tests)
venv/bin/pytest app/tests/unit/ -v

# Run integration tests only (21 tests)
venv/bin/pytest app/tests/integration/ -v

# Run specific test file
venv/bin/pytest app/tests/unit/test_screening_pipeline.py -v
venv/bin/pytest app/tests/integration/ranking/test_ranking.py -v

# With coverage
venv/bin/pytest --cov=app --cov-report=term-missing app/tests/
```

## Known Limitations & TODO

### Resolved Issues ✅
- **Testing Infrastructure**: Fixed NameError in mapper.py, added comprehensive mocking for external services.
- **Integration Tests**: Resolved `InterfaceError` and `RuntimeError: Task attached to different loop` by changing `asyncio_default_test_loop_scope` to `function` in `pytest.ini` and using per-test engine lifecycle in `conftest.py`.
- **API Assertions**: Fixed `test_jobs_public.py` assertions to match `PaginatedResponse` and `PublicJobDetailResponse` schemas.
- **Lifespan Stability**: Prevented premature engine disposal in `app/main.py` during test runs.
- **Zero Dependency Testing**: System now works without external API credentials for testing.
- **Unit Test Cleanup**: Eliminated 21 duplicated helper functions from `test_ai_scoring.py`, now uses actual service functions.
- **Public Application Flow**: Implemented complete public application submission and ticket tracking tests.
- **HR Workflow Testing**: Added vacancy lifecycle, screening, tenant isolation, and interview scheduling tests.
- **Enum Fix**: All `Job` model instantiations in tests now use `EmploymentType.FULL_TIME` (Enum object) instead of string `"FULL_TIME"`.
- **Mock Path Fix**: Validator module path in `conftest.py` corrected to `app.ai.validator.document_validator.validate_document_content`.
- **Assertion Alignment**: Duplicate application status code is `409` (not 400); interview response uses key `interview_id`; screening triggered via `POST /screening/applications/{id}/run`.
- **Auth Security Tests**: Added 5 integration tests for refresh token rotation, reuse detection (kill switch), concurrent rotation, invalid format rejection, and token version tracking.
- **Document Pipeline Tests**: Added 3 integration tests validating OCR+LLM pipeline through API.
- **Ranking Tests**: Added 4 integration tests with direct `CandidateScore` DB injection for determinism.
- **AI Unit Test Coverage**: Added 3 new unit test files: `test_screening_pipeline.py`, `test_validator_step.py`, and `test_document_validator.py`.
- **Architecture Stabilization**:
  - Implemented **Global Domain Exception Handling** via `BaseDomainException` and centralized `handlers.py`.
  - Removed all `HTTPException` references from service layers (`auth`, `jobs`, `applications`).
  - Standardized all codebase comments and documentation to **English**.
  - Integrated **Audit Logs** for critical job administrative actions (publish, close).
  - Upgraded **Red Flag Detector** to an asynchronous LLM-powered engine with deterministic fallback.
  - Achieved **100% test pass rate** (107/107) across unit and integration pyramids.
  - Completed **Indonesian Localization Audit (COMPLETED)**:
    - **Centralized Mapping**: All Enums, internal keys, and common API success messages are mapped to Indonesian display labels in `app/shared/helpers/localization.py`.
    - **Localized API Schemas**: Major response schemas now include `*_label` fields (e.g., `status_label`, `employment_type_label`) providing Indonesian display names directly.
    - **Service & Router Audit**: Hardcoded English success messages in `auth`, `jobs`, `applications`, and `screening` routers have been refactored to use the localization helper.
    - **AI Validator Localization**: Technical fallback reasons and error messages in the AI Document Validator are now presented in Indonesian for HR users.
    - **Recruitment Context**: `Semantic Matcher` synonym map enriched with Indonesian professional terms (Akuntansi, Pemasaran, Desain, dll).
    - **Public Experience**: Ticket subjects and status tracking are fully in Indonesian for a native applicant experience.
    - **Stability**: 107/107 tests PASSED with localized logic.
- **Distributed Background Tasks (COMPLETED)**:
    - **Taskiq Integration**: Migrated heavy AI screening from internal `FastAPI BackgroundTasks` to a distributed queue using Taskiq.
    - **Upstash Redis Broker**: Integrated serverless Upstash Redis as the message broker for background tasks.
    - **Modular Task Layout**: Background tasks now reside in `app/features/<feature>/tasks.py` for better separation of concerns.
    - **Worker Stability**: Implemented automatic broker startup/shutdown in FastAPI lifespan.
- **Mistral OCR Migration (COMPLETED)**:
    - **API-First Engine**: Replaced local `EasyOCR` and `pdfplumber` with **Mistral Document AI**.
    - **Scanned PDF Support**: Enabled high-accuracy text extraction for scanned documents, crucial for Degrees and IDs.
    - **Infrastructure Optimization**: Uninstalled 2GB+ of heavy local dependencies (`torch-gpu`, `opencv`, `easyocr`), resulting in a lean, optimized virtual environment using **Torch-CPU**.
    - **Markdown Extraction**: OCR results now preserve document structure (tables, headers) in Markdown for better LLM validation.
- **AI Reliability & Retry (COMPLETED)**:
    - **Taskiq SmartRetry**: Integrated exponential backoff for all external AI API calls.
    - **Transient Error Handling**: Implemented specific `AIAPIException` hierarchy to distinguish between retryable and non-retryable failures.
    - **Last-Chance Fallback**: Guaranteed screening completion by forcing deterministic fallbacks on final retry attempt.
- **Batch Screening (COMPLETED)**:
    - **Hourly Automation**: Implemented `run_batch_screening` task via Taskiq periodic scheduler.
    - **Bulk Processing**: Automatically enqueues screening for all applications in `APPLIED` status every hour.

### Current Limitations
1. **Password Reset Table**: Needs `password_reset_tokens` table via Alembic migration for full persistent implementation.
2. **Email Delivery**: SMTP/SendGrid not yet configured — tokens logged to console during development.
3. **LLM Groq**: Implementation uses Groq API with `qwen/qwen3-32b` or `llama3-70b-8192` for document validation and AI explanations.

### Test Coverage Status
- **Unit Tests**: 86 tests (all passing ✅)
- **Integration Tests**: 21 tests (all passing ✅)
- **Total**: **107 tests PASSED** (0 failed)
- **E2E Tests**: Ready with proper mocking infrastructure
- **Coverage**: High coverage across AI orchestration, Auth security, and Core workflows.

### Feature Coverage Gap (Pending Integration Tests)
1. `scoring_templates` — create/update/get scoring weight templates.
2. `companies` — multi-tenant management (super admin).
3. `users` — HR account management.
4. `notifications` — list, mark read/unread.
5. `job_forms` — form field builder (create/update/delete/reorder).
6. `audit_logs` — list audit trail.

### AI Module Coverage Gap (Pending Unit Tests)
1. `app/ai/explanation/generator.py` — template-based explanation logic.
2. `app/ai/llm/client.py` — Groq API client wrapper.
3. `app/ai/scoring/engine.py` — standalone scoring engine.

### Important Notes for Testing
- `employment_type` field on `Job` model MUST use `EmploymentType.FULL_TIME` (enum object).
- `description` field on `Job` model is NOT NULL — required in all test fixtures.
- JWT tokens for tests must include `token_version: int` and `sub: str(user_id)`.
- Duplicate applications return `409 Conflict`.
- `InterviewScheduledResponse` uses field `interview_id`, not `id`.
- Screening triggered via `POST /api/v1/screening/applications/{id}/run`.
- `pytest.ini` configured with `asyncio_default_test_loop_scope = function` for full isolation.
- **Unit test AI module** uses local `app/tests/unit/conftest.py` — do not delete.
- **Ranking tests** use direct `CandidateScore` injection for full determinism.
- `doc_type.value` on `DocumentType` enum is sent as **lowercase** to LLM validator (e.g., `"identity_card"`).