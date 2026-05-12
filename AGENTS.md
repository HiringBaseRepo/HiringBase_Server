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
