# HiringBase

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Groq](https://img.shields.io/badge/AI-Groq%20Qwen3-orange?style=flat-square)](https://groq.com/)

**HiringBase** is an AI-powered recruitment assistant that streamlines the hiring process through automated document validation, semantic skill matching, and deterministic weighted scoring.

---

## 🚀 Quick Start

### 1. Clone & Environment Setup
```bash
git clone https://github.com/boyblanco/HireBase_Server.git
cd HireBase_Server
python -m venv venv
source venv/bin/activate  # Linux/macOS
# pip install -r requirements.txt
```

### 2. Configuration
```bash
cp .env.example .env
# Configure NEON_DATABASE_URL, R2_BUCKET, and GROQ_API_KEY
```

### 3. Database & Run
```bash
alembic upgrade head
uvicorn app.main:app --reload
```

---

## 🏗️ Project Architecture

HiringBase follows a **Domain-Driven Design (DDD)** approach with a clean, layered architecture:

```text
app/
├── ai/                 # AI Engine (OCR, Matcher, Scoring, LLM)
├── core/               # System Core (Config, Auth, Database, Exceptions)
├── shared/             # Global Resources (Enums, Schemas, Constants)
├── features/           # Feature-based Modules (Auth, Jobs, Applications, etc.)
│   └── <domain>/
│       ├── routers/    # API Endpoints
│       ├── services/   # Business Logic
│       ├── repositories/ # Data Access
│       ├── schemas/    # Pydantic Models
│       └── models/     # SQLAlchemy ORM Models
├── workers/            # Async Background Tasks
└── main.py             # Entry Point
```

---

## 🤖 AI Hybrid Engine

We use a 3-layer intelligence strategy to ensure both accuracy and explainability.

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Layer 1: Deterministic** | Rule Engine | Knockout rules, scoring formula, ranking. |
| **Layer 2: Semantic** | Sentence-Transformers | Semantic skill matching & synonym detection. |
| **Layer 3: Reasoning** | Groq (Qwen3-32B) | Document validation & HR explanation generation. |

> [!IMPORTANT]
> **Scoring Philosophy**: The LLM is never used to compute the final score. Scores are calculated using a deterministic, weighted formula based on verified form data.

---

## ✨ Key Capabilities

- **Ticket-Based Public Flow**: No applicant login required; track status via `TKT-YYYY-NNNNN`.
- **Custom Form Builder**: Create job-specific forms with varied field types and knockout logic.
- **Semantic Document Validation**: Groq-powered verification of KTP, Ijazah, and Certifications.
- **Advanced Auth Security**: Stateful JWT with rotation, reuse detection, and global kill-switch.
- **Structured Logging**: JSON-based logging via `structlog` for easy monitoring.

---

## 🛠️ Tech Stack

- **Core**: FastAPI (Async), Pydantic v2
- **Persistence**: PostgreSQL, SQLAlchemy 2.0 (Async), Alembic
- **AI/ML**: EasyOCR, pdfplumber, Sentence-Transformers, Groq Cloud
- **Infrastructure**: Cloudflare R2 (S3-compatible storage)
- **Security**: python-jose, passlib (bcrypt)

---

## 📈 Roadmap

- [ ] **V2**: WhatsApp/Email auto-notifications for candidate status updates.
- [ ] **V2**: Computer Vision for advanced fake document detection.
- [ ] **V2**: Integrated Interview Scheduler with Google/Outlook Calendar.
- [ ] **V2**: Multi-tenant Dashboard for Super Admins.

---

## 🧪 Testing

```bash
pytest app/tests -v
```
Currently, there are **59+ unit tests** covering Auth, AI Scoring, and Knockout Rules.
