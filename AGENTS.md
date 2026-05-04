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
│   └── llm/            # LLM client (HuggingFace + OpenRouter fallback)
├── core/               # Global config, DB engine, security, middlewares
│   ├── config/         # Settings & environment variables
│   ├── database/       # SQLAlchemy async engine & Base model
│   └── security/       # JWT & password hashing
├── features/           # Feature-based modules (Domain Driven)
│   └── <feature_name>/ # e.g., auth, jobs, applications
│       ├── routers/        # FastAPI endpoints only
│       │   └── router.py
│       ├── services/       # Business logic / orchestration
│       │   └── service.py
│       ├── repositories/   # SQLAlchemy query/data access layer
│       ├── schemas/        # Pydantic validation schemas
│       └── models/         # Per-feature model exports / future split target
│
│   # Current shared compatibility model file:
│   └── models.py       # SQLAlchemy models are still centralized here for now
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
- `users` — Super Admin, HR, Applicant
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

`models/` is the per-feature target for SQLAlchemy model exports. For now, all SQLAlchemy models still live in `app/features/models.py` as a compatibility layer.

When splitting models later:
- Move one domain at a time.
- Update imports carefully.
- Preserve table names, constraints, indexes, and relationships.
- Keep Alembic autogenerate stable and review migrations before applying.

### Refactor Priority

All existing feature routers have now been split into active router/service/repository/schema layers. Future refactors should focus on:
1. Replacing service-level `HTTPException` with domain/custom exceptions once `app.core.exceptions` defines them.
2. Moving SQLAlchemy models out of `app/features/models.py` into per-feature `models/` packages one domain at a time.
3. Adding focused unit tests for each service/repository workflow.
4. Reviewing API clients where endpoints moved from many scalar parameters to Pydantic body schemas.

### Layer Compliance Audit

Current status of `app/features` after the router/service/repository/schema migration:

| Feature | Status | Notes |
|---|---|---|
| `users` | Mostly compliant | Router delegates to service; DB access lives in `users/repositories/repository.py`; request/response contracts live in `users/schemas/schema.py`. |
| `auth` | Mostly compliant | User/company lookup and persistence live in `auth/repositories/repository.py`; service keeps hashing, token generation, password reset orchestration, and commits. Router still raises route-level `HTTPException`, which is acceptable for HTTP auth failures. |
| `jobs` | Partially compliant | Router delegates to service and has active repository/schema layers. Service still raises `HTTPException`; future cleanup should replace this with domain/custom exceptions if `app.core.exceptions` is expanded. |
| `applications` | Mostly compliant | Public jobs, public apply, listing, and status update delegate to service/repository/schema layers. Upload/R2 and ticket/status-log orchestration live in service. |
| `screening` | Mostly compliant | Knockout rule CRUD, screening enqueue, background pipeline, scoring, and manual override delegate to service/repository/schema layers. AI helpers stay in `app/ai`; knockout helper stays in `screening/services/helpers.py`. |
| `companies` | Mostly compliant | Company CRUD, suspend/activate, statistics, and overview delegate to service/repository/schema layers. |
| `documents` | Mostly compliant | Upload validation, R2 upload, ownership check, and document persistence live in service/repository layers. |
| `job_forms` | Mostly compliant | Form-field CRUD and reorder logic live in service/repository/schema layers. |
| `scoring` | Mostly compliant | Scoring-template CRUD and weight validation live in service/repository/schema layers. |
| `ranking` | Mostly compliant | Ranking query, applicant lookup, pagination, and response mapping live in service/repository/schema layers. |
| `tickets` | Mostly compliant | Ticket tracking lookup and response mapping live in service/repository/schema layers. |
| `notifications` | Mostly compliant | List/read/read-all query and update operations live in service/repository/schema layers. |
| `interviews` | Mostly compliant | Scheduling and detail lookup live in service/repository/schema layers. |
| `audit_logs` | Mostly compliant | Filtering, pagination count, query execution, and response mapping live in service/repository/schema layers. |

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

### OCR Pipeline (`app/ai/ocr/engine.py`)
- Digunakan untuk ekstraksi teks dari dokumen pendukung (KTP, Ijazah) jika diperlukan validasi tambahan.
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
3. Continue scoring pipeline without LLM enrichment

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
- JWT access + refresh tokens (JOSE `sub` field must be a string)
- Rate limiting per IP (60 req/min default)
- File type and size validation
- SQL injection protected by SQLAlchemy ORM
- XSS protected by JSON response serialization
- Password reset: token `secrets.token_urlsafe(32)`, SHA-256 hash

## Testing Strategy

### Unit Tests (Tersedia)
- `test_auth.py` — JWT encode/decode, password hashing
- `test_ai_scoring.py` — Resume parser, red flag detector, soft skill scorer, scoring helpers (30+ cases)
- `test_knockout_rules.py` — Semua tipe knockout rule dengan mock (document, experience, education, boolean, range)
- `test_semantic_matcher.py` — 3-layer matching dengan model di-mock

### Integration Tests (TODO)
- DB + API flow: create vacancy → apply → screening → ranking
- Upload dokumen → OCR → parsing

### E2E Tests (TODO)
- Full application submission → screening → ranking flow

## Known Limitations & TODO

1. **Password Reset DB**: Butuh tabel `password_reset_tokens` via Alembic migration untuk implementasi penuh (`confirm_password_reset` mengembalikan False sampai tabel dibuat)
2. **Email Delivery**: SMTP/SendGrid belum dikonfigurasi — token di-log ke console saat development (`structlog` level INFO)
3. **Import Errors Fix**: `PaginatedResponse` telah dipindahkan ke `app.shared.schemas.response` untuk memperbaiki `ImportError` yang terjadi di hampir semua router fitur.
4. **Feature layer migration**: Semua feature router sudah dipisah ke layer aktif `routers/`, `services/`, `repositories/`, dan `schemas/`. Sisa cleanup: ganti `HTTPException` service-level dengan custom/domain exceptions saat tersedia, tambah test service/repository, dan review API clients yang terdampak body schema baru.
5. **models.py monolitik**: Semua 16 model masih dalam `app/features/models.py` sebagai compatibility layer. Struktur `models/` per feature sudah disiapkan; pecah model per domain secara bertahap dan update import dengan hati-hati.
6. **Revoke Sessions**: Masih no-op — butuh Redis atau token blacklist table
7. **Image-based PDF**: Untuk PDF scan (bukan text), perlu convert page ke image sebelum EasyOCR (belum diimplementasi)
8. **LLM Qwen3**: Target Qwen3 via HuggingFace Gradio Space belum diimplementasi — saat ini menggunakan HF Inference API + OpenRouter fallback
