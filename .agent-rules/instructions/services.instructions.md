---
applyTo: "app/features/**/services/**/*.py"
---

# Service Layer Rules

Treat matching files as the home for business logic and orchestration.

## Allowed
- permission and ownership checks
- status transitions
- ticket or token generation
- password hashing
- scoring and knockout decisions
- audit-log intent
- coordination across repositories, storage helpers, and background jobs
- `db.commit()`

## Forbidden
- `db.add()`
- `db.flush()`
- `db.refresh()`
- complex SQLAlchemy query construction that belongs in repositories
- HTTP response formatting
- `HTTPException`

## Service Pattern
- Gather data through repositories.
- Apply domain rules in the service.
- Commit once the use case is complete.
- If the task updates a record, preserve snapshot and audit requirements.
