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
- **AI/NLP**: Sentence Transformers, Scikit-learn, NumPy
- **OCR**: EasyOCR, PDF2Image
- **Storage**: Cloudflare R2 (S3-compatible via Boto3)
- **Logging**: Structlog (Structured JSON Logging)

## Architecture Principles

1. **Layer 1 — Deterministic Engine**: All scoring, knockout rules, ranking, and validation are rule-based and reproducible.
2. **Layer 2 — NLP / Embeddings**: Used for skill synonym matching, semantic similarity, and CV parsing assistance.
3. **Layer 3 — LLM**: Used ONLY for natural language explanation generation, summaries, and structured JSON normalization. LLM never computes final scores.

## Project Structure

```text
/app
├── ai/                 # AI Engine logic (scoring, NLP models, OCR)
├── core/               # Global config, DB engine, security, middlewares
│   ├── config/         # Settings & environment variables
│   ├── database/       # SQLAlchemy async engine & Base model
│   └── security/       # JWT & password hashing
├── features/           # Feature-based modules (Domain Driven)
│   └── <feature_name>/ # e.g., auth, jobs, applications
│       ├── router.py   # FastAPI endpoints
│       ├── service.py  # Business logic & DB operations
│       ├── models.py   # SQLAlchemy models
│       └── schemas.py  # Pydantic validation schemas
├── shared/             # Shared utilities & global schemas
│   └── schemas/        # StandardResponse, PaginationParams
├── tests/              # Unit, integration, and E2E tests
└── main.py             # Application entry point
```

## Database Schema (Key Tables)

- `companies` — Tenant / company accounts
- `users` — Super Admin, HR, Applicant
- `jobs` — Vacancies with multi-step setup
- `job_requirements` — Skills, experience, education required
- `job_scoring_templates` — Per-job weighted scoring config
- `job_form_fields` — Custom applicant form fields
- `job_knockout_rules` — Auto-reject / pending rules
- `applications` — Candidate applications
- `application_answers` — Form responses
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

## Coding Standards

- **Naming**: `snake_case` for functions/variables/files, `PascalCase` for classes.
- **Async First**: All I/O operations (DB, API calls, File) must be `async`.
- **Typing**: Use Python type hints for all function signatures.
- **Errors**: Raise custom exceptions from `app.core.exceptions` instead of returning error dictionaries.

## File Storage

- Cloudflare R2 (S3-compatible)
- CVs: `cvs/<uuid>.pdf`
- Documents: `documents/<uuid>.pdf`
- Public URL constructed from `R2_PUBLIC_URL`

## AI Fallback Strategy

If LLM API fails:
1. Use template-based explanation generator
2. Log failure to audit_logs
3. Continue scoring pipeline without LLM enrichment

If OCR fails:
1. Mark document as `ocr_text = null`
2. Allow manual HR review
3. Do not block application

## Development & Commands

- **Run Dev Server**: `uvicorn app.main:app --reload`
- **Migrations**: 
  - Create: `alembic revision --autogenerate -m "description"`
  - Apply: `alembic upgrade head`
- **Testing**: `pytest`
- **Linting**: `ruff check .` / `black .`

## Security

- Passwords hashed with bcrypt via Passlib
- JWT access + refresh tokens
- Rate limiting per IP (60 req/min default)
- File type and size validation
- SQL injection protected by SQLAlchemy ORM
- XSS protected by JSON response serialization

## Testing Strategy

- `unit/` — Pure logic (hashing, JWT, scoring math)
- `integration/` — DB + API flow tests
- `e2e/` — Full application submission → screening → ranking flow
