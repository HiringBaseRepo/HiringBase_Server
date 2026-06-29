# HiringBase Domain Rules Reference

## Database Schema (Key Tables)
`companies`, `users`, `jobs`, `job_requirements`, `job_scoring_templates`, `job_form_fields`, `job_knockout_rules`, `applications`, `application_answers` (`value_text`, `value_number`), `application_documents` (**NO CV**), `candidate_scores`, `application_status_logs`, `tickets` (`TKT-YYYY-NNNNN`), `interviews`, `notifications`, `audit_logs`, `password_reset_otps`

## Default Scoring Weights
Skill Match 40% | Experience 20% | Education 10% | Portfolio 10% | Soft Skill 10% | Admin Complete 10%
**Note**: All weights and their labels are managed via `app/shared/constants/scoring.py` and `app/shared/helpers/localization.py`.

## Current Scoring Rules
- Final score remains weighted deterministic `0-100`.
- Each component passes anchored internal rating layer `1-5`, mapped to `20-100`, before weighted aggregation.
- Skill matching uses structured `JobRequirement` only. Do **not** infer requirements from `job.description`.
- `confidence_score` is review-governance signal. It does not directly reduce numeric final score.
- Low skill confidence or insufficient structured skill requirements must force `UNDER_REVIEW`.
- Education and experience relevance must come from structured `JobRequirement`.
- `CandidateScore.scoring_breakdown` is explainability payload for component evidence, rating, confidence, and gate reasons.
- Ranking continues to use persisted `final_score`, not anchored rating directly.

## Constants and Enums Strategy
- **Single Source of Truth**: All domain constants (audit entities, scoring keys, error labels) and enums must reside in `app/shared/constants` or `app/shared/enums`.
- **Localization**: User-facing messages and labels must use `get_label()` with internal keys (e.g., `ERR_*`). Hardcoded Indonesian strings are strictly forbidden in app logic.
- **English Core**: Backend logic, database values, and code stay in English. Indonesian is only for presentation/user-facing layer.

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

Scoring status override rules:
- high-risk red flag -> `REJECTED`
- low confidence / insufficient structured requirements -> `UNDER_REVIEW`
- otherwise final score threshold applies

## Screening Execution Rules
- Public apply does not auto-run AI screening.
- Manual trigger returns queued/pending style response and may skip immediate enqueue if duplicate or quota guard blocks it.
- Hourly batch picks oldest eligible records first, with small capped batch size.
- Recovery candidates may come from stale `DOC_CHECK` and stale `AI_PROCESSING`.
- Recovery retries are bounded. If retry limit is exceeded, final safe state is `UNDER_REVIEW`.
- Duplicate screening enqueue for same application must be prevented within cooldown window.

## Public Applicant Flow (Ticket-Based)
Applicants have no login. Flow: fill form + upload docs (explicit `file_<DocumentType>` multipart keys) -> system validates fields, requested docs, file format, email deduplication, and rejects unrequested `OTHERS` uploads -> atomic save to R2 + DB -> returns `TKT-YYYY-NNNNN`. Applicants are stored in `users` table as contacts without credentials.

## Password Reset Flow
Local users (non-public applicants) can reset their password via a 2-stage OTP flow:
1. **Request**: Generates a 6-digit OTP, stores its SHA-256 hash in `password_reset_otps` table with a 15-minute expiry, records the `PASSWORD_RESET_REQUESTED` audit log, and offloads sending the email to Taskiq (`send_password_reset_otp_email`).
2. **Confirm**: Validates the email and OTP hash, verifies the OTP has not expired, takes an audit snapshot of the user model, updates the password, increments user `token_version` to invalidate all active refresh tokens/sessions, generates a new token pair (auto-login), deletes the OTP, records the `PASSWORD_RESET_CONFIRMED` audit log, and commits the transaction.

## Notification Rules
- Notification v1 is **internal in-app** only for active `HR` and `SUPER_ADMIN` users.
- Public applicants do **not** receive in-app notifications. They stay on ticket tracking and email updates.
- Delivery model for notification v1 is polling REST, not WebSocket.
- Primary API contract:
  - `GET /notifications`
  - `GET /notifications/summary`
  - `POST /notifications/{notification_id}/read`
  - `POST /notifications/read-all`
- Notification read state uses both `is_read` and `read_at`.
- Frontend navigation contract uses `entity_type` + `entity_id`, not backend-owned route strings as primary source.
- Current `NotificationType` source of truth:
  - `NEW_APPLICATION`
  - `SCREENING_PASSED`
  - `SCREENING_UNDER_REVIEW`
  - `SCREENING_REJECTED`
  - `DOCUMENT_FAILED`
  - `INTERVIEW_SCHEDULED`
  - `APPLICATION_OFFERED`
  - `APPLICATION_HIRED`
  - `APPLICATION_REJECTED`

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

## Big Data Market Intelligence Rules
- **Access Control**: Limited to `SUPER_ADMIN` (`require_super_admin`).
- **Database Engine**: Async MongoDB via `motor` client. Scrape jobs are stored in `hiringbase_bigdata.jobs`.
- **Fault Tolerance**: If `MONGODB_URL` is not defined or MongoDB is offline, database helpers must catch the exception, log it, and return a clean default response (e.g. empty lists) instead of crashing.
- **Scraper Scheduling**: Triggered every 6 hours via GitHub Actions workflow `scrape-jobs.yml` inside the server repo.
- **Manual Refresh**: Invoked via `POST /big-data/refresh` which triggers a GitHub API `workflow_dispatch` call using `GITHUB_PAT` and `GITHUB_REPO` credentials.
