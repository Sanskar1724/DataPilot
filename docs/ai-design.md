# AI Design

## Separation of concerns

The model is a *reasoning layer*, never a *processing engine*.

**Model does:**
- understand schema semantics
- explain data-quality problems
- classify suspicious columns/values
- suggest transformations
- map old schema → new schema (future)
- explain pipeline failures
- generate structured fix plans

**Model does NOT:**
- process the whole CSV
- calculate over millions of rows
- replace Pandas / SQL
- execute arbitrary Python
- directly modify files

## What is sent to the model (metadata only)

```json
{
  "profile": {"rows": 12005, "columns": 7, "duplicates": 3, "column_stats": {...}},
  "schema": {"dtypes": {...}, "columns_info": {...}},
  "issues": [{"column": "revenue", "problem": "negative_values", "severity": "high", ...}]
}
```

No raw data rows ever cross the boundary. `build_metadata()` in `ai/analyzer.py`
is the single place that assembles this bundle.

## Response contract

Model is asked for (and validated against):

```json
{
  "explanation": "...",
  "issues": [{
    "column": "revenue",
    "problem": "negative_values",
    "severity": "high",
    "recommendation": "clip to zero",
    "fix": {"name": "clip_negatives", "column": "revenue", "args": {}}
  }],
  "cases_needing_review": ["..."]
}
```

Validation (`ai/parser.py`):
- JSON extracted (tolerates ``` fences)
- `Analysis.model_validate()` (Pydantic) — must pass
- transform names must exist in `TRANSFORMATIONS`
- columns must exist in the real schema (`guard_columns`) — computed from the
  actual DataFrame, never from model output

Failures raise `ValueError` and are surfaced in the UI as warnings. There is no
silent fallback that would let bad output reach the transformer.

## Provider configuration

```env
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
DATAPILOT_AI_ENABLED=true
```

Because the model id is config-only, swapping between 7-9B open models requires
no code change. `ai/client.py` retries 429/5xx/timeouts with exponential backoff
and records token + latency usage per call.

## Cost control

- Only metadata is tokenized → small prompts regardless of dataset size.
- temperature=0 for structured planning.
- `max_tokens` capped.
- Usage (`prompt_tokens`, `completion_tokens`, `latency_ms`) is returned for
  the Phase 6 evaluation and visible in the UI.