# HiringBase Domain Rules Reference

## Database Schema (Key Tables)
`companies`, `users`, `jobs`, `job_requirements`, `job_scoring_templates`, `job_form_fields`, `job_knockout_rules`, `applications`, `application_answers` (`value_text`, `value_number`), `application_documents` (**NO CV**), `candidate_scores`, `application_status_logs`, `tickets` (`TKT-YYYY-NNNNN`), `interviews`, `notifications`, `audit_logs`

## Default Scoring Weights
Skill Match 40% | Experience 20% | Education 10% | Portfolio 10% | Soft Skill 10% | Admin Complete 10%

## Knockout Rule Types
| Type | Operators | Example |
|---|---|---|
| `document` | n/a | Must have Identity Card, Degree |
| `experience` | gte, gt, lt, lte, eq | Min 2 years |
| `education` | gte | Min Bachelor's |
| `boolean` | eq, neq | Willing to WFO = yes |
| `range` | lte, gte | Salary <= 10jt |

**Knockout Actions**: `auto_reject` or `pending_review`

## Application Status Flow
```text
APPLIED -> DOC_CHECK -> [DOC_FAILED]
        -> AI_PROCESSING -> AI_PASSED / UNDER_REVIEW / KNOCKOUT
        -> INTERVIEW -> OFFERED -> HIRED
        -> REJECTED (any stage)
```

## Screening Execution Rules
- Public apply does not auto-run AI screening.
- Manual trigger returns queued/pending style response and may skip immediate enqueue if duplicate or quota guard blocks it.
- Hourly batch picks oldest eligible records first, with small capped batch size.
- Recovery candidates may come from stale `DOC_CHECK` and stale `AI_PROCESSING`.
- Recovery retries are bounded. If retry limit is exceeded, final safe state is `UNDER_REVIEW`.
- Duplicate screening enqueue for same application must be prevented within cooldown window.

## Public Applicant Flow (Ticket-Based)
Applicants have no login. Flow: fill form + upload docs (explicit `file_<DocumentType>` multipart keys) -> system validates fields, requested docs, file format, email deduplication, and rejects unrequested `OTHERS` uploads -> atomic save to R2 + DB -> returns `TKT-YYYY-NNNNN`. Applicants are stored in `users` table as contacts without credentials.

## API Conventions
- All responses use `StandardResponse` wrapper `{success, message, data, errors, meta}`.
- Pagination uses `PaginationParams` (`page`, `per_page`).
- Auth uses Bearer Token in `Authorization` header.
- Use `Annotated` for FastAPI dependencies.
- Dependency aliases available in `app.features.auth.dependencies.auth`:
  - `DbDep`
  - `CurrentUserDep`
  - `HrUserDep`
  - `SuperAdminDep`
- Router imports: `app.features.<feature>.routers.router`
- Auth dependencies: `app.features.auth.dependencies.auth`
