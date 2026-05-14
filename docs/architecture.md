# HiringBase Architecture Reference

## System Overview
AI-powered recruitment backend for HR teams: job vacancy creation, form-based applications (No CV), AI candidate screening and ranking, explainable AI decisions, and ticket-based status tracking.

## Tech Stack
| Layer | Technology |
|---|---|
| Framework | FastAPI (Async), Python 3.12+ |
| Database | PostgreSQL (cloud) Neon DB | SQLAlchemy 2.0 (Async), Alembic |
| Validation | Pydantic v2 |
| Security | JWT (python-jose), Bcrypt (passlib) |
| AI/NLP | HuggingFace Inference API (`paraphrase-multilingual-MiniLM-L12-v2`). No local ML libs. |
| OCR | Mistral Document AI (PDF & Image via R2 URL) |
| Cache & Tasks | Upstash Redis (256MB) - Taskiq Broker + Async Caching |
| Logging | Structlog (JSON/pretty), UUID Request-ID, Audit Context |
| Storage | Cloudflare R2 (S3-compatible, Boto3) |

## Architecture Principles
1. **Layer 1 - Deterministic**: Scoring, knockout, ranking via form answers (`ApplicationAnswer`).
2. **Layer 2 - NLP/Embeddings**: Skill matching (cosine similarity) + soft skill keyword scorer.
3. **Layer 3 - LLM**: Natural language explanation + Semantic Red Flag Detection.
4. **Exception Handling**: `BaseDomainException` -> global HTTP handler. Never raise `HTTPException` anywhere in features, including services, routers, and dependencies.
5. **Distributed Processing**: Heavy AI (OCR, LLM, Semantic Matching) offloaded via Taskiq + Redis.
6. **Localization**: Backend, DB, and AI use English; all user-facing strings map to Indonesian via `app/shared/helpers/localization.py`.
7. **Security & Audit**:
   - IP & User-Agent auto-captured by middleware via `contextvars`.
   - Every `UPDATE` must snapshot old values with `get_model_snapshot` before modifying.
   - AI scoring weight changes must be recorded in audit log.
   - Dashboard ("Pulse") is lightweight real-time aggregation. Reports ("Brain") are complex historical aggregation with date filters.
8. **Deployment (Render)**: current free-tier runtime starts Web API, Taskiq Worker, and Taskiq Scheduler together from one container entrypoint. Heavy inference stays offloaded to external APIs to fit memory limits.
9. **Quota-Aware Screening**:
   - Screening throughput is intentionally rate-limited by Redis-backed guards.
   - Manual screening can jump batch order, but not quota/concurrency rules.
   - Failed or stale AI screening must degrade to `UNDER_REVIEW`, not loop forever.

## Project Structure
```text
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
└── main.py
```

## Coding Standards
- `snake_case` for functions, variables, and files; `PascalCase` for classes.
- All I/O must be `async`.
- Full type hints on all function signatures.
- Raise `BaseDomainException` subclasses only.
- Heavy libraries imported lazily, inside functions or via background workers.
- Never add files directly to feature root.
- Taskiq CLI semantics matter:
  - broker/scheduler object path uses `module:variable`
  - task import modules use plain module path only
