# HiringBase AI Architecture Reference

## Current End-to-End AI Flow
```text
Public Apply
  -> save applicant, application, answers, documents, ticket
  -> status = APPLIED
  -> internal notification only
  -> no direct AI call

Manual Trigger OR Hourly Batch Trigger
  -> Redis dedupe + quota guard
  -> Taskiq task queued

Worker Start
  -> status = DOC_CHECK
  -> check required docs from knockout rules
  -> run non-document knockout rules first
     - fail + auto_reject -> KNOCKOUT
     - fail + pending_review -> UNDER_REVIEW

If knockout passed
  -> status = AI_PROCESSING
  -> OCR required docs via Mistral OCR API
  -> semantic document validation via Groq
  -> build candidate profile from ApplicationAnswer
  -> semantic skill matching via exact + synonym + HF inference API
  -> anchored component scoring (1-5 -> 20-100)
  -> deterministic experience / education / portfolio scoring
  -> soft skill scoring from text answers (keyword baseline + Groq blend)
  -> semantic red-flag detection via Groq + regex fallback
  -> deterministic weighted final score
  -> LLM explanation via Groq, template fallback
  -> save / update CandidateScore + audit log
  -> map final status
     - high-risk red flag -> REJECTED
     - low skill confidence / weak structured requirements -> UNDER_REVIEW
     - final score >= 60 -> AI_PASSED
     - else -> UNDER_REVIEW
  -> internal notification
```

## Actual Trigger Model
- Public application submit does **not** run screening immediately.
- Manual screening uses `POST /screening/applications/{application_id}/run`.
- Hourly batch screening uses Taskiq scheduler cron `0 * * * *`.
- Stale `DOC_CHECK` and `AI_PROCESSING` records can enter bounded recovery path.
- Redis guard prevents duplicate enqueue, overload, and infinite retry churn.

## Distributed Screening Pipeline (Taskiq)
- **Manual Trigger**: HR triggers via "Run Screening". Manual path may bypass batch ordering, but still respects dedupe + quota guard.
- **Auto Trigger**: public apply does **not** call AI directly. New applications remain `APPLIED`.
- **Batch Screening**: hourly periodic task processes small batch, not full fan-out.
- **Recovery Path**: stale `DOC_CHECK` and `AI_PROCESSING` entries may be retried in bounded recovery flow.
- **SmartRetryMiddleware**: exponential backoff + jitter, max 3 retries for transient failures (`Connection`, `Timeout`, `5xx`). Final attempt forces deterministic fallbacks.
- **ORM Preloading**: all relationships pre-fetched via `selectinload` to prevent `MissingGreenlet` in async workers.
- **Redis Guard Layer**: queue markers, processing locks, hourly/day quota counters, and recovery retry counters enforce safe throughput.

## Scoring Pipeline (`app/ai/scoring/engine.py`)
No CV parsing. All data comes from `ApplicationAnswer` via standard `field_key`:
- `experience_years` -> experience score
- `education_level` -> education score (`SMA`, `D3`, `S1`, `S2`, `S3`)
- `skills` -> comma-separated list for Semantic Matcher
- `github_url`, `portfolio_url`, `live_project_url` -> portfolio score

**Mathematical Integrity**: single source of truth in `engine.py`. Education ranks sync with `EDUCATION_RANK` constants. Missing requirements return full score (`100%`).

Scoring hardening:
- each component now passes anchored rating layer (`1..5`) before final weighted score
- current default map: `1=20`, `2=40`, `3=60`, `4=80`, `5=100`
- skill confidence does not reduce numeric final score directly, but can gate status to `UNDER_REVIEW`
- education and experience relevance rely on structured `JobRequirement`, not `job.description`
- scoring flow persists `CandidateScore.scoring_breakdown` for explainability and future UI/API use

## Scoring Breakdown Contract
- `CandidateScore.scoring_breakdown` stores:
  - component score
  - anchored rating `1..5`
  - rubric text
  - confidence
  - evidence summary
  - gate reasons
- Application detail may expose this payload directly.
- Ranking should continue using persisted `final_score`, not breakdown internals.

Final weighted score uses:
- Skill Match `40`
- Experience `20`
- Education `10`
- Portfolio `10`
- Soft Skill `10`
- Administrative Completeness `10`

Pass threshold:
- `>= 60` -> `AI_PASSED`
- `< 60` -> `UNDER_REVIEW`
- high-risk red flag override -> `REJECTED`

## OCR & Validation (`app/ai/ocr/engine.py` + `app/ai/validator/`)
Mistral Document AI performs async PDF/image text extraction via R2 URLs. LLM validation checks:
1. name matches applicant
2. valid date or lifetime
3. valid document number
4. correct document type
5. semantic reasonableness

Anomalies become `red_flags` with high risk.
- Groq-backed validation may use fallback API key chain when primary key returns provider rate limit (`429`).

## Semantic Matcher (`app/ai/matcher/semantic_matcher.py`)
3-layer skill matching:
- Layer 1: exact match
- Layer 2: synonym map, including Indonesian terms
- Layer 3: Hugging Face Inference API cosine similarity

Important:
- This is not local `sentence-transformers` runtime in current main flow.
- Current code calls HF Inference API with model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.

## Soft Skill Scorer (`app/ai/nlp/soft_skill_scorer.py`)
Analyzes concatenated text answers. Hybrid scoring uses 30% keyword baseline + 70% LLM. Falls back to pure keyword if LLM fails. Output range: 20-100 per dimension.

## Semantic Red Flag Detector (`app/ai/redflag/detector.py`)
LLM-powered analysis of form data + OCR text. Cross-checks mismatches such as experience years vs degree graduation year. Falls back to regex-based detection. Output is in Indonesian.
- Red flag payload must normalize to dict list with shape `{message, risk_level, type}`.

## AI Caching Strategy (`app/core/cache/`)
- Semantic Matcher: HF Inference API results cached for 24 hours.
- OCR Engine: Mistral OCR text results cached for 1 hour.
- Soft Skill Scorer: LLM scoring results cached for 24 hours.
- Keys use MD5 hashing to minimize memory usage on 256MB free tier.

## AI Fallback Strategy (Retry-Then-Fallback)
1. Phase 1: Taskiq retries up to 3 times with increasing delay.
2. Phase 2 (final attempt):
   - OCR -> empty string, flagged for manual review
   - LLM Validation -> "Fallback Pass" + warning flag
   - Red Flag -> regex-based detection
   - Soft Skill -> pure keyword scoring
   - Explanation -> template-based logic
3. If screening orchestration still fails repeatedly, application must not remain stuck in `DOC_CHECK` or `AI_PROCESSING`; safe fallback target is `UNDER_REVIEW`.
4. All failures and fallback triggers are logged.

## Old Flow vs Current Flow
| Topic | Old Flow | Current Repo State |
|---|---|---|
| Screening trigger | implied immediate pipeline after apply | async screening only after manual trigger or hourly batch |
| Source of truth | form + possible CV | form answers in `ApplicationAnswer`; CV parsing not core scoring path |
| OCR engine | EasyOCR / Tesseract | Mistral OCR API over R2 public file URL |
| Skill semantic engine | local sentence transformers | HF Inference API + cache |
| Document validation | generic LLM validator | Groq validation after OCR, high-risk doc flags affect admin score |
| Knockout stage | mentioned before scoring | implemented before AI scoring, can stop at `KNOCKOUT` or `UNDER_REVIEW` |
| Final status after AI | ranking focus only | `AI_PASSED` / `UNDER_REVIEW` / `REJECTED` with audit + notifications |
| Retry/fallback | not detailed | Taskiq retry, Redis quota guard, stale recovery, deterministic fallback |
| Candidate ranking | after scoring | separate feature reads saved `CandidateScore`, not part of worker itself |
| Fake visual document detection | not available | still not available in current repo |

## Important Non-Core Artifact
- Current product rule remains: no CV parsing in scoring engine; structured form answers are primary input.

## Screening Throughput Policy
- Default batch size per hourly run: `5`
- Default total active screening concurrency: `2`
- Default manual active concurrency: `1`
- Default quota ceilings:
  - `20` screenings per hour
  - `100` screenings per day
- Batch pacing intentionally delays enqueue between candidates to avoid API burst and token waste.
