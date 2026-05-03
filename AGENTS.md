# AGENTS.md — AI Context for Smart Resume Screening System

## System Overview

This is the **backend** of an AI-powered recruitment assistant that helps HR teams:
- Create job vacancies with custom forms
- Accept applications with document uploads
- Automatically screen candidates using a hybrid AI engine
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

1. **Layer 1 — Deterministic Engine**: All scoring, knockout rules, ranking, and validation are rule-based and reproducible.
2. **Layer 2 — NLP / Embeddings**: Skill synonym matching + cosine similarity via `sentence-transformers`. Soft skill scoring via keyword NLP classifier di `app/ai/nlp/soft_skill_scorer.py`.
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
- `application_documents` — Uploaded files (CV, KTP, etc.)
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
| `document` | n/a | Wajib punya CV, KTP, Ijazah |
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
- **Router responsibility**: `routers/router.py` should only handle HTTP concerns: request parameters, FastAPI dependencies, response model, and `StandardResponse` wrapping.
- **Service responsibility**: `services/service.py` should hold business rules, orchestration, validation that is not purely schema-level, status transitions, hashing, code generation, and calls to repositories.
- **Repository responsibility**: `repositories/` should hold SQLAlchemy queries, joins, counts, pagination statements, and persistence helpers. Avoid writing new `db.execute(...)` logic directly in routers.
- **Schema responsibility**: Pydantic request/response models belong in `schemas/`. Avoid growing endpoint signatures with many raw scalar parameters when a schema is appropriate.

## File Storage

- Cloudflare R2 (S3-compatible)
- CVs: `cvs/<uuid>.pdf`
- Documents: `documents/<uuid>.pdf`
- Public URL constructed from `R2_PUBLIC_URL`

## AI Implementation Details

### OCR Pipeline (`app/ai/ocr/engine.py`)
- PDF: `pdfplumber` → extract text per halaman dengan `x_tolerance=3, y_tolerance=3`
- Image: `EasyOCR` dengan bahasa `["id", "en"]`, GPU=False
- Fallback chain: download → deteksi tipe → proses → return `""` jika gagal (tidak blokir pipeline)

### Semantic Matcher (`app/ai/matcher/semantic_matcher.py`)
- Layer 1: Exact string match (case-insensitive)
- Layer 2: Curated synonym dict `_synonym_map()` — 11+ skill group
- Layer 3: `SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")` cosine similarity
- Model di-cache via `@lru_cache(maxsize=1)` (singleton)
- Threshold cosine similarity: `0.65`
- Confidence score: `0.90` jika model tersedia, `0.70` jika fallback exact-only

### Soft Skill Scorer (`app/ai/nlp/soft_skill_scorer.py`)
- 5 dimensi: communication, leadership, teamwork, problem_solving, initiative
- Keyword-based (regex word boundary), no LLM needed
- Output range: 20–100 per dimensi, composite_score = rata-rata 5 dimensi
- Dipanggil dari screening pipeline; fallback ke 60.0 jika error

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
4. **models.py monolitik**: Semua 16 model masih dalam `app/features/models.py` sebagai compatibility layer. Struktur `models/` per feature sudah disiapkan; pecah model per domain secara bertahap dan update import dengan hati-hati.
5. **Revoke Sessions**: Masih no-op — butuh Redis atau token blacklist table
6. **Image-based PDF**: Untuk PDF scan (bukan text), perlu convert page ke image sebelum EasyOCR (belum diimplementasi)
7. **LLM Qwen3**: Target Qwen3 via HuggingFace Gradio Space belum diimplementasi — saat ini menggunakan HF Inference API + OpenRouter fallback
