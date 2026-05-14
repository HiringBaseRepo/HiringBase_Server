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
- heavy loops that map domain objects into custom payloads when that logic belongs elsewhere
- `HTTPException`

## Routing Pattern
- Call a service method for business behavior.
- Let domain exceptions bubble to the global handler.
- Keep route functions thin and readable.
- Prefer shared schema objects over ad-hoc dictionaries.
