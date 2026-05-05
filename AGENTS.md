# AGENTS.md — AI Context for Smart Resume Screening System

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
- **Testing**: `pytest app/tests/ -v` (Semua 59 unit tests PASSED)
- **Test AI only**: `pytest app/tests/unit/test_ai_scoring.py -v`
- **Test Knockout**: `pytest app/tests/unit/test_knockout_rules.py -v`
- **Test Semantic Matcher**: `pytest app/tests/unit/test_semantic_matcher.py -v`
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

### Unit Tests
- `test_auth.py` — JWT encode/decode, password hashing
- `test_ai_scoring.py` — Resume parser, red flag detector, soft skill scorer, scoring helpers
- `test_knockout_rules.py` — Semua tipe knockout rule dengan mock

### Integration Tests
- `test_applications.py` — Public application flow, job listing
- `test_jobs_public.py` — Public jobs endpoints with full database setup

### Mocking Infrastructure
The test suite includes comprehensive mocking for external services:

- **R2 Storage**: `mock_r2` fixture using `unittest.mock` to simulate Cloudflare R2
- **Groq LLM**: `mock_groq` fixture for AI explanation services
- **Document Validator**: `mock_document_validator` fixture for semantic validation
- **OCR Engine**: `mock_ocr_engine` fixture for text extraction

### Zero External Dependency Testing
The system is designed to work without external API credentials:
- Groq LLM returns `None` when `GROQ_API_KEY` is not configured
- Document validator returns valid response when API key is missing
- All AI services have proper fallback mechanisms

### Test Execution Commands
```bash
# Run all tests
venv/bin/pytest app/tests/ -v --tb=short

# Run unit tests only
venv/bin/pytest app/tests/unit/ -v

# Run integration tests only
venv/bin/pytest app/tests/integration/ -v

# Run specific test
venv/bin/pytest app/tests/integration/jobs/test_jobs_public.py -v

# With coverage
venv/bin/pytest --cov=app --cov-report=term-missing app/tests/
```

## Known Limitations & TODO

### Resolved Issues ✅
- **Testing Infrastructure**: Fixed NameError in mapper.py, added comprehensive mocking for external services
- **Integration Tests**: Enhanced conftest.py with R2, Groq, OCR, and document validator mocks
- **Zero Dependency Testing**: System now works without external API credentials for testing

### Current Limitations
1. **Password Reset Table**: Butuh tabel `password_reset_tokens` via Alembic migration untuk implementasi penuh fitur reset password.
2. **Email Delivery**: SMTP/SendGrid belum dikonfigurasi — token di-log ke console saat development (`structlog` level INFO).
3. **Image-based PDF**: Untuk PDF scan (bukan text), perlu convert page ke image sebelum EasyOCR (belum diimplementasi).
4. **LLM Groq**: Implementasi menggunakan Groq API dengan model `qwen/qwen3-32b` (atau `llama3-70b-8192` tergantung config) untuk validasi dokumen dan penjelasan AI.

### Test Coverage Status
- **Unit Tests**: 59 tests (all passing)
- **Integration Tests**: Enhanced with jobs module tests
- **E2E Tests**: Ready with proper mocking infrastructure
- **Coverage**: Can be measured with `pytest-cov`
