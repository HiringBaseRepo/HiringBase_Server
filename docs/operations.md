# HiringBase Operations Reference

## File Storage (Cloudflare R2)
- Documents: `documents/<uuid>.pdf`
- Portfolios: `portfolios/<uuid>.<ext>`
- Company Logos: `company-logos/<uuid>.<ext>`
- Company Assets: `company-assets/<uuid>.<ext>`
- Job Attachments: `job-attachments/<uuid>.<ext>`
- Public URL from `R2_PUBLIC_URL`
- Upload operations use async wrappers (`upload_file_async`) via thread offload to keep FastAPI event loop non-blocking.
- Upload rollback strategy: best-effort delete uploaded keys when DB commit fails after upload.

## Security
- Passwords: bcrypt via Passlib (`bcrypt==3.2.0`)
- Stateful JWT: access tokens in JSON body; refresh tokens in HTTP-only cookies
- Advanced auth: Refresh Token Rotation, Reuse Detection, Global Kill Switch via `token_version`
- Rate limiting: 60 requests/minute per IP
- File type + size validation
- SQL injection: protected by SQLAlchemy ORM
- XSS: protected by JSON serialization
- Password reset: `secrets.token_urlsafe(32)` + SHA-256 hash

## Logging & Observability
- Structlog: JSON in production (non-TTY), pretty console in dev (TTY)
- Request tracking: UUID4 per request, returned as `X-Request-ID` header; middleware logs method, path, status, latency
- Exception monitoring: all global handlers log errors; 500s include structured tracebacks
- Context propagation: `structlog.contextvars` for async-safe state
- Runtime debugging should use `structlog`, not `print()`, in feature flow

## Development Commands
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
taskiq worker app.core.tkq:broker app.main:app
alembic revision --autogenerate -m "description"
alembic upgrade head
ruff check . && black .
docker build -t hirebase .
docker run -p 10000:10000 hirebase
```
