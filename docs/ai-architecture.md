# HiringBase AI Architecture Reference

## Distributed Screening Pipeline (Taskiq)
- **Manual Trigger** (default): HR triggers via "Run Screening" to manage API costs.
- **Auto Trigger**: via `auto_screening` flag on job (to be implemented).
- **Batch Screening**: hourly periodic task processes all `APPLIED` applications.
- **SmartRetryMiddleware**: exponential backoff + jitter, max 3 retries for transient failures (`Connection`, `Timeout`, `5xx`). Final attempt forces deterministic fallbacks.
- **ORM Preloading**: all relationships pre-fetched via `selectinload` to prevent `MissingGreenlet` in async workers.

## Scoring Pipeline (`app/ai/scoring/engine.py`)
No CV parsing. All data comes from `ApplicationAnswer` via standard `field_key`:
- `experience_years` -> experience score
- `education_level` -> education score (`SMA`, `D3`, `S1`, `S2`, `S3`)
- `skills` -> comma-separated list for Semantic Matcher
- `github_url`, `portfolio_url`, `live_project_url` -> portfolio score

**Mathematical Integrity**: single source of truth in `engine.py`. Education ranks sync with `EDUCATION_RANK` constants. Missing requirements return full score (`100%`).

## OCR & Validation (`app/ai/ocr/engine.py` + `app/ai/validator/`)
Mistral Document AI performs async PDF/image text extraction via R2 URLs. LLM validation checks:
1. name matches applicant
2. valid date or lifetime
3. valid document number
4. correct document type
5. semantic reasonableness

Anomalies become `red_flags` with high risk.

## Semantic Matcher (`app/ai/matcher/semantic_matcher.py`)
3-layer skill matching:
- Layer 1: exact match
- Layer 2: synonym map, including Indonesian terms
- Layer 3: sentence transformer cosine similarity

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
3. All failures and fallback triggers are logged.
