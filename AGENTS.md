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

