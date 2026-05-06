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
- **OCR**: EasyOCR (image), pdfplumber (PDF text), PDF2Image, Pillow
- **Storage**: Cloudflare R2 (S3-compatible via Boto3)
- **Logging**: Structlog (Structured JSON Logging)

## Architecture Principles

1. **Layer 1 — Deterministic Engine**: All scoring, knockout rules, ranking, and validation are rule-based and reproducible, primarily using form answers (`ApplicationAnswer`).
2. **Layer 2 — NLP / Embeddings**: Skill matching + cosine similarity via `sentence-transformers` using skills from form data. Soft skill scoring via keyword NLP classifier on concatenated text answers.
3. **Layer 3 — LLM**: Used ONLY for natural language explanation generation. LLM never computes final scores.

## Project Structure

```text
/app
├── ai/                 # AI Engine logic
│   ├── ocr/            # OCR: pdfplumber (PDF) + EasyOCR (image)
│   ├── parser/         # Resume text parser (regex-based)
│   ├── matcher/        # Semantic skill matcher (3-layer: exact, synonym, embedding)
│   ├── nlp/            # Soft skill keyword scorer
│   ├── scoring/        # Standalone scoring engine
│   ├── redflag/        # Red flag detector
│   ├── explanation/    # Template-based explanation generator
│   ├── validator/      # Semantic document validator (Groq-based)
│   └── llm/            # LLM client (Groq-based)
├── core/               # Global config, DB engine, security, middlewares
│   ├── config/         # Settings & environment variables
│   ├── database/       # SQLAlchemy async engine & Base model
│   └── security/       # JWT & password hashing
├── features/           # Feature-based modules (Domain Driven)
│   └── <feature_name>/ # e.g., auth, jobs, applications
│       ├── routers/        # FastAPI endpoints only
│       │   └── router.py
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
│   ├── enums/          # Application enums (UserRole, ApplicationStatus, dll)
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
- `users` — Super Admin, HR (Pelamar menggunakan alur publik berbasis tiket tanpa sesi login)
- `jobs` — Vacancies with multi-step setup
- `job_requirements` — Skills, experience, education required
- `job_scoring_templates` — Per-job weighted scoring config
- `job_form_fields` — Custom applicant form fields
- `job_knockout_rules` — Auto-reject / pending rules (`field_key` untuk lookup answers)
- `applications` — Candidate applications
- `application_answers` — Form responses (`value_text`, `value_number`)
- `application_documents` — Uploaded files (KTP, Ijazah, etc. — **NO CV**)
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

### Knockout Rule Types (SEMUA TERIMPLEMENTASI)

| Type | Operator | Contoh |
|---|---|---|
| `document` | n/a | Wajib punya KTP, Ijazah |
| `experience` | gte, gt, lt, lte, eq | Minimal 2 tahun pengalaman |
| `education` | gte | Minimal S1 |
| `boolean` | eq, neq | Bersedia WFO = ya |
| `range` | lte, gte | Gaji expected <= 10jt |

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
Pelamar tidak memiliki akun yang dapat dilogin. Alur pelamaran sepenuhnya publik:
1. Pelamar mengisi form publik dan mengunggah dokumen wajib.
2. Sistem memvalidasi kelengkapan bidang wajib, dokumen wajib (berdasarkan nama file), format file, dan duplikasi surel sebelum menyimpan data.
3. Transaksi atomik menyimpan data ke R2 dan Database, lalu mengembalikan nomor Tiket (`TKT-YYYY-NNNNN`) kepada pelamar untuk pelacakan status.
Pelamar direpresentasikan secara internal dalam tabel `users` (sebagai kontak) tanpa kredensial akses.

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
- **Errors**: Raise custom exceptions from `app.core.exceptions` instead of returning error dictionaries.
- **Import lazy**: Library berat (pdfplumber, easyocr) diimport di dalam fungsi untuk menghindari crash jika belum terinstall.
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

Services may receive `AsyncSession`, but should not build complex SQLAlchemy queries directly. Move reusable or non-trivial DB access into repositories.

### Repositories

`repositories/` is only for database access:
- Build SQLAlchemy `select`, `insert`, `update`, `delete`, joins, counts, filters, ordering, and pagination queries.
- Provide functions such as `get_by_id`, `get_by_email`, `list_paginated`, `create`, `update`, `soft_delete`, `exists`, and domain-specific query helpers.
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

### Refactor Priority

1. Replacing service-level `HTTPException` with domain/custom exceptions once `app.core.exceptions` defines them.
2. Adding focused unit tests for each service/repository workflow.
3. Reviewing API clients where endpoints moved from many scalar parameters to Pydantic body schemas.
4. Further modularization of service files by extracting helper functions to separate modules (parser, validator, mapper).

### Layer Compliance Audit

Current status of `app/features` after the router/service/repository/schema migration:

| Feature | Status | Notes |
|---|---|---|
| `users` | Fully compliant | Router delegates to service; Repositories and Schemas active; Models migrated to `users/models`. |
| `auth` | Mostly compliant | Hashing, rotation, and detection implemented. Needs `PasswordResetToken` table migration. |
| `jobs` | Fully compliant | Multi-step vacancy and requirements logic decentralized to domain models. |
| `applications` | Fully compliant | Public apply and status tracking logic decentralized. Models in `applications/models`. |
| `screening` | Fully compliant | Scoring and knockout rules logic decentralized. Models in `screening/models`. |
| `companies` | Fully compliant | Multi-tenant logic decentralized. Models in `companies/models`. |
| `documents` | Fully compliant | R2 and validation logic decentralized. |
| `job_forms` | Fully compliant | Form builder logic decentralized. |
| `scoring` | Fully compliant | Scoring templates decentralized. |
| `ranking` | Fully compliant | Ranking queries decentralized. |
| `tickets` | Fully compliant | Ticket tracking decentralized. |
| `notifications` | Fully compliant | Notification logic decentralized. |
| `interviews` | Fully compliant | Interview scheduling logic decentralized. |
| `audit_logs` | Fully compliant | Audit trail logic decentralized. |

Routers should remain thin. The last full scan found no `select(`, `db.execute`, `db.add`, `db.delete`, `db.commit`, `db.refresh`, `StandardResponse.error`, `put_object`, `json.loads`, `generate_ticket_code`, `generate_apply_code`, or `get_password_hash` usage inside `app/features/*/routers`.

When continuing the refactor, preserve public endpoint paths and response wrappers unless the user explicitly asks to change API contracts. If an endpoint must change from scalar query/body parameters to a Pydantic body schema, call that out because frontend clients may need payload adjustments.

Before editing a feature, quickly scan its router for these patterns: `select(`, `db.execute`, `db.add`, `db.delete`, `db.commit`, `db.refresh`, `StandardResponse.error`, `HTTPException`, `put_object`, `json.loads`, `generate_ticket_code`, and `generate_apply_code`. These usually indicate logic that belongs in services or repositories.

## File Storage

- Cloudflare R2 (S3-compatible)
- Documents: `documents/<uuid>.pdf`
- Portfolios: `portfolios/<uuid>.<ext>`
- Company Assets: `company-assets/<uuid>.<ext>`
- Job Attachments: `job-attachments/<uuid>.<ext>`
- Public URL constructed from `R2_PUBLIC_URL`

## AI Implementation Details

### Scoring Pipeline (Form-based)
Sistem tidak lagi melakukan parsing file CV. Data untuk scoring diambil dari `ApplicationAnswer` dengan `field_key` standar:
- `experience_years`: Digunakan untuk skor pengalaman.
- `education_level`: Digunakan untuk skor pendidikan (SMA, D3, S1, S2, S3).
- `skills`: List skill (comma-separated) untuk `Semantic Matcher`.
- `github_url`, `portfolio_url`, `live_project_url`: Untuk skor portfolio.

### OCR & Validation Pipeline (`app/ai/ocr/engine.py` & `app/ai/validator/`)
- Digunakan untuk ekstraksi teks dari dokumen pendukung (KTP, Ijazah).
- **Semantic Document Validation**: Teks hasil OCR divalidasi menggunakan LLM (Groq) untuk memverifikasi:
  1. Nama sesuai data pelamar
  2. Tanggal berlaku aktif (atau seumur hidup)
  3. Format nomor dokumen yang valid
  4. Kesesuaian jenis dokumen
  5. Kewajaran isi dokumen (deteksi anomali/rekayasa semantik)
  Anomali dicatat sebagai `red_flags` dengan tingkat risiko tinggi.
- PDF: `pdfplumber`, Image: `EasyOCR`.

### Semantic Matcher (`app/ai/matcher/semantic_matcher.py`)
- Mencocokkan list skill dari form jawaban dengan `JobRequirement`.
- Layer 1: Exact match, Layer 2: Synonym map, Layer 3: Sentence Transformer.

### Soft Skill Scorer (`app/ai/nlp/soft_skill_scorer.py`)
- Menganalisis **gabungan teks dari semua jawaban form** pelamar.
- Keyword-based (regex word boundary), no LLM needed.
- Output range: 20–100 per dimensi.

### AI Fallback Strategy

If LLM API fails:
1. Use template-based explanation generator (`app/ai/explanation/generator.py`)
2. Log failure to audit_logs
3. Skip semantic document validation (mark as "Fallback Pass") and continue scoring pipeline

If OCR fails:
1. Log error, return empty string
2. Soft skill scoring uses empty string → returns default 30.0
3. Do not block application — flag untuk manual HR review

## Development & Commands

- **Run Dev Server**: `uvicorn app.main:app --reload`
- **Migrations**:
  - Create: `alembic revision --autogenerate -m "description"`
  - Apply: `alembic upgrade head`
- **Testing**: `pytest app/tests/ -v` (Semua **107 tests PASSED** — 86 unit + 21 integration)
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

## Testing Strategy

### Unit Tests (86 tests)
- `test_auth.py` — JWT encode/decode, password hashing (2 tests)
- `test_ai_scoring.py` — Resume parser, red flag detector, soft skill scorer, scoring helpers (21 tests)
- `test_knockout_rules.py` — Semua tipe knockout rule dengan mock (20 tests)
- `test_semantic_matcher.py` — Skill matching logic with exact, synonym, and embedding layers (10 tests)
- `test_screening_pipeline.py` — Orchestrator `process_screening`: DOC_FAILED, KNOCKOUT, AI_PASSED, UNDER_REVIEW, red flags, weighted score (11 tests)
- `test_validator_step.py` — `run_document_semantic_check`: routing OCR+LLM, flag generation, non-required doc skip (8 tests)
- `test_document_validator.py` — `validate_document_content` (LLM fallback, parse response) + OCR engine internals `_download_file`, `_extract_text_pdf`, `_extract_text_image`, `_is_image` (15 tests)

### Integration Tests (21 tests)
- `test_public_application.py` — Public application submission, duplicate 409, ticket tracking (3 tests)
- `test_hr_workflows.py` — HR vacancy lifecycle, screening run, tenant isolation, interview scheduling (4 tests)
- `test_jobs_public.py` — Public jobs endpoints (list, detail dengan form fields) (2 tests)
- `test_auth_security.py` — Refresh token rotation, reuse detection kill switch, concurrent rotation, invalid format, token version (5 tests)
- `test_document_pipeline.py` — Document completeness check, full pipeline with all docs, tenant isolation (3 tests)
- `test_ranking.py` — Ranking dengan custom weights, tenant isolation, top-N limit, pagination (4 tests)

### Mocking Infrastructure
Global test fixtures in `app/tests/conftest.py` provide comprehensive mocking:

- **R2 Storage**: `mock_r2` fixture mocks `boto3.client()` for Cloudflare R2 operations
- **Groq LLM**: `mock_groq` fixture mocks `app.ai.llm.client.call_llm` dan `app.ai.validator.document_validator.validate_document_content`
- **OCR Engine**: `mock_ocr_engine` fixture mocks `extract_text_from_document()` for text extraction
- **Database Isolation**: `test_db_session` fixture — function-scoped engine per-test, auto-rollback setelah selesai. Override via `override_db` autouse fixture.
- **Authentication**: `auth_headers` fixture generates valid JWT tokens (dengan `token_version` dan integer `sub`) for HR user testing

### Unit Test Isolation (Local Conftest)
`app/tests/unit/conftest.py` meng-override **semua** autouse fixture dari root conftest sehingga unit test AI module dapat memanggil fungsi aslinya:
- `mock_ocr_engine`, `mock_groq`, `mock_r2` → no-op di scope unit
- `db_cleanup`, `override_db`, `mock_get_session` → no-op di scope unit
- Test AI internal (`validate_document_content`, `extract_text_from_document`) di-test melalui **direct module namespace patching** (`validator_module.settings`, `ocr_module._download_file`) untuk menghindari konflik dengan mock global.

### Call-Site Mocking Pattern
Untuk menghindari masalah lazy import pada `process_screening` (yang import `get_session` di dalam function body):
- Patch `app.core.database.session.get_session` (source module) — bukan attribute di service module
- Gunakan `@asynccontextmanager` wrapper sebagai mock session context
- Patch semua repository functions di namespace service: `app.features.screening.services.service.<func_name>`

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
- **Testing Infrastructure**: Fixed NameError in mapper.py, added comprehensive mocking for external services
- **Integration Tests**: Resolved `InterfaceError` dan `RuntimeError: Task attached to different loop` dengan mengubah `asyncio_default_test_loop_scope` ke `function` di `pytest.ini` dan menggunakan per-test engine lifecycle di `conftest.py`.
- **API Assertions**: Fixed `test_jobs_public.py` assertions to match `PaginatedResponse` and `PublicJobDetailResponse` schemas.
- **Lifespan Stability**: Prevented premature engine disposal in `app/main.py` during test runs.
- **Zero Dependency Testing**: System now works without external API credentials for testing.
- **Unit Test Cleanup**: Eliminated 21 duplicated helper functions from `test_ai_scoring.py`, now uses actual service functions.
- **Public Application Flow**: Implemented complete public application submission and ticket tracking tests.
- **HR Workflow Testing**: Added vacancy lifecycle, screening, tenant isolation, and interview scheduling tests.
- **Enum Fix**: Semua instansiasi model `Job` di test kini menggunakan `EmploymentType.FULL_TIME` (Enum object) bukan string `"FULL_TIME"` untuk menghindari `AttributeError` di mapper dan `NotNullViolationError` di DB.
- **Mock Path Fix**: Path modul validator di `conftest.py` diperbaiki ke `app.ai.validator.document_validator.validate_document_content`.
- **Assertion Alignment**: Status code duplikasi aplikasi adalah `409` (bukan `400`); interview response menggunakan key `interview_id`; screening dipicu via `POST /screening/applications/{id}/run`.
- **Auth Security Tests**: Added 5 integration tests for refresh token rotation, reuse detection (kill switch), concurrent rotation, invalid format rejection, dan token version tracking.
- **Document Pipeline Tests**: Added 3 integration tests validating OCR+LLM pipeline through API (completeness check, full pipeline, tenant isolation).
- **Ranking Tests**: Added 4 integration tests dengan DB injection `CandidateScore` langsung untuk determinisme (custom weights, tenant isolation, top-N, pagination).
- **AI Unit Test Coverage**: Tambah 3 file unit test baru:
  - `test_screening_pipeline.py` — orchestrator `process_screening` dengan lazy import handling via `app.core.database.session.get_session` patch.
  - `test_validator_step.py` — `run_document_semantic_check` OCR+LLM orchestration.
  - `test_document_validator.py` — `validate_document_content` LLM parsing + OCR engine internal helpers.
- **Unit Test Isolation**: Tambah `app/tests/unit/conftest.py` lokal yang override semua autouse fixture root agar AI unit test bisa memanggil fungsi asli tanpa konflik mock global.
- **Lazy Import Handling**: `process_screening` menggunakan lazy import `get_session` — di-patch via source module (`app.core.database.session.get_session`) menggunakan `@asynccontextmanager` wrapper, bukan via service module attribute.

### Current Limitations
1. **Password Reset Table**: Butuh tabel `password_reset_tokens` via Alembic migration untuk implementasi penuh fitur reset password.
2. **Email Delivery**: SMTP/SendGrid belum dikonfigurasi — token di-log ke console saat development (`structlog` level INFO).
3. **Image-based PDF**: Untuk PDF scan (bukan text), perlu convert page ke image sebelum EasyOCR (belum diimplementasi).
4. **LLM Groq**: Implementasi menggunakan Groq API dengan model `qwen/qwen3-32b` (atau `llama3-70b-8192` tergantung config) untuk validasi dokumen dan penjelasan AI.

### Test Coverage Status
- **Unit Tests**: 86 tests (all passing ✅)
  - `test_auth.py`: 2 tests
  - `test_ai_scoring.py`: 21 tests
  - `test_knockout_rules.py`: 20 tests (semua tipe rule)
  - `test_semantic_matcher.py`: 10 tests (exact, synonym, embedding)
  - `test_screening_pipeline.py`: 11 tests (status transitions, weighted score, red flags)
  - `test_validator_step.py`: 8 tests (OCR+LLM orchestration)
  - `test_document_validator.py`: 15 tests (LLM response parsing, OCR routing, fallbacks)
- **Integration Tests**: 21 tests (all passing ✅)
  - `test_public_application.py`: 3 tests
  - `test_hr_workflows.py`: 4 tests
  - `test_jobs_public.py`: 2 tests
  - `test_auth_security.py`: 5 tests (refresh rotation, reuse detection, kill switch)
  - `test_document_pipeline.py`: 3 tests
  - `test_ranking.py`: 4 tests (custom weights, tenant isolation, pagination)
- **Total**: **107 tests PASSED** (0 failed)
- **E2E Tests**: Ready with proper mocking infrastructure
- **Coverage**: Can be measured with `pytest-cov`

### Feature Coverage Gap (Belum Ada Integration Test)
Feature berikut belum memiliki integration test dan menjadi prioritas berikutnya:
1. `scoring_templates` — create/update/get scoring weight template
2. `companies` — multi-tenant management (super admin)
3. `users` — HR account management
4. `notifications` — list, mark read/unread
5. `job_forms` — form field builder (create/update/delete/reorder)
6. `auth` login/logout/register/me — endpoint dasar belum punya dedicated test
7. `audit_logs` — list audit trail

### AI Module Coverage Gap (Belum Ada Unit Test)
1. `app/ai/explanation/generator.py` — template-based explanation
2. `app/ai/llm/client.py` — Groq API client wrapper
3. `app/ai/scoring/engine.py` — standalone scoring engine

### Catatan Penting untuk Test
- Field `employment_type` pada model `Job` WAJIB diisi dengan `EmploymentType.FULL_TIME` (enum object), bukan string `"FULL_TIME"`.
- Field `description` pada model `Job` adalah NOT NULL — wajib disertakan di semua test fixture.
- JWT token untuk test harus menyertakan claim `token_version: int` dan `sub: str(user_id)` (integer sebagai string).
- Duplikasi lamaran mengembalikan status `409 Conflict` (bukan 400).
- Response `InterviewScheduledResponse` menggunakan field `interview_id`, bukan `id`.
- Screening dipicu via `POST /api/v1/screening/applications/{id}/run` — tidak ada GET endpoint untuk hasil screening langsung.
- `pytest.ini` dikonfigurasi dengan `asyncio_default_test_loop_scope = function` untuk isolasi penuh antar test.
- **Unit test AI module** menggunakan `app/tests/unit/conftest.py` lokal yang meng-override autouse fixture root — jangan hapus file ini.
- **Ranking test** menggunakan injeksi langsung `CandidateScore` ke DB (bukan `process_screening`) untuk determinisme penuh.
- `doc_type.value` pada `DocumentType` enum dikirim sebagai **lowercase** ke LLM validator (contoh: `"ktp"`, bukan `"KTP"`).
 