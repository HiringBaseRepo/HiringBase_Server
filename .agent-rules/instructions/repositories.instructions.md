---
applyTo: "app/features/**/repositories/**/*.py"
---

# Repository Layer Rules

Treat matching files as data-access-only modules.

## Allowed
- SQLAlchemy `select`, `insert`, `update`, and `delete`
- eager loading and pagination
- persistence helpers
- `db.add()`
- `db.flush()`
- `db.refresh()`

## Forbidden
- business decisions
- permission logic
- password hashing
- token or ticket generation
- AI, OCR, file-upload, or storage orchestration
- HTTP response shaping
- `db.commit()`

## Repository Pattern
- Return domain data needed by services.
- Keep query methods focused and composable.
- Push branching business behavior back to services.
