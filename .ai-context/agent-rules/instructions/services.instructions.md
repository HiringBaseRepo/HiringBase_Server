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
- raising `BaseDomainException` directly (use specific subclasses)
- hardcoded Indonesian strings (use `get_label` in exception or response)
- complex SQLAlchemy query construction that belongs in repositories

## Service Pattern
- Gather data through repositories.
- Use constants from `app/shared/constants` for scoring weights, audit entities, and labels.
- Apply domain rules in the service.
- Commit once the use case is complete.
- If the task updates a record, preserve snapshot and audit requirements.
