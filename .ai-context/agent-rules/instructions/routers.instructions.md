---
applyTo: "app/features/**/routers/**/*.py"
---

# Router Layer Rules

Treat matching files as HTTP-only entry points.

## Allowed
- `APIRouter` setup
- path operations
- dependency wiring
- request parsing
- response model selection
- `StandardResponse` wrapping
- lightweight translation between HTTP input/output and service calls

## Forbidden
- SQLAlchemy queries
- direct database mutation
- business rules or orchestration
- hardcoded Indonesian strings (use `get_label`)
- `HTTPException`

## Routing Pattern
- Call a service method for business behavior.
- Let domain exceptions bubble to the global handler.
- Use `get_label` for any user-facing messages.
- Use Enums in schemas for type safety and consistency.
- Keep route functions thin and readable.
- Prefer shared schema objects over ad-hoc dictionaries.
