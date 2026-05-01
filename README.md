# Smart Resume Screening System — Backend

AI-Based Recruitment Assistant Backend built with **FastAPI**, **SQLAlchemy**, **PostgreSQL**, and **AI Hybrid Engine**.

## Quick Start

### 1. Clone & Setup Environment

```bash
cd smart-resume-screening
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Neon PostgreSQL URL, R2 credentials, and HF token
```

### 3. Run Database Migrations

```bash
alembic upgrade head
```

### 4. Start Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
app/
├── core/               # Config, DB, Security, Middleware, Utils
├── shared/             # Enums, Constants, Schemas, Helpers
├── features/           # Domain APIs (Auth, Jobs, Applications, etc.)
│   └── models.py       # All SQLAlchemy models
├── ai/                 # AI Engine (Parser, Matcher, Scoring, LLM, NLP, OCR, RedFlag)
├── workers/            # Background task workers
├── tests/              # Pytest suites
└── main.py             # FastAPI application entrypoint
```

## Key Features

| Module | Description |
|--------|-------------|
| **Auth** | JWT + RBAC (Super Admin, HR, Applicant) with refresh tokens |
| **Companies** | Multi-tenant company management (Super Admin) |
| **Jobs** | Multi-step vacancy builder with publish control |
| **Form Builder** | Custom per-job applicant forms |
| **Knockout Rules** | Deterministic pre-screening filters |
| **Scoring Templates** | Dynamic weighted scoring per position |
| **Public Apply** | Public job board + form submission + document upload |
| **AI Screening** | CV parsing → skill matching → weighted scoring → ranking |
| **Explanation** | Human-readable AI score reasoning |
| **Red Flags** | Risk detection (gaps, hopping, typos) |
| **Ranking** | Score-based applicant ranking with filters |
| **Tickets** | Applicant status tracking by code |
| **Manual Override** | HR can adjust scores with audit trail |
| **Audit Logs** | Full change tracking |

## AI Architecture

| Layer | Engine | Purpose |
|-------|--------|---------|
| **Layer 1** | Rule Engine | Knockout, validation, scoring formula, ranking |
| **Layer 2** | NLP / Embeddings | Skill matching, synonym detection, parser helper |
| **Layer 3** | LLM (Qwen3 / Llama3) | Explanation text, summary, reasoning, and structured JSON normalization |

> **Principle**: LLM never computes final score. Score is always rule-based + deterministic.

## Testing

```bash
pytest app/tests -v --cov=app --cov-report=html
```

## Deployment

Use Uvicorn with Gunicorn for production:

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4
```

## V2 Roadmap

- [ ] Computer vision fake document detection
- [ ] WhatsApp API notifications
- [ ] Interview auto-scheduler
- [ ] Multi-tenant SaaS billing
- [ ] Redis caching layer
- [ ] Celery task queue
- [ ] Fine-tuned hiring LLM
