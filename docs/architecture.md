# Architecture

## Core principle

**LLM ≠ Data Processing Engine.** The model never cleans rows. Deterministic code
(Pandas / rules) does the heavy lifting; the LLM only reasons over metadata.

```
DATA → Deterministic Processing → Metadata → 7-9B LLM → 
      Reasoning/Plan → Deterministic Execution → Clean Dataset
```

## Module responsibilities

| Layer         | Module                    | Responsibility                                          |
|---------------|---------------------------|---------------------------------------------------------|
| Core          | `core/profiler.py`        | Vectorized statistics per column (no row iteration)     |
| Core          | `core/validator.py`       | 6 deterministic quality detectors                       |
| Core          | `core/transformer.py`     | Fixed transform registry + `FixPlan` (safe execution)   |
| Core          | `core/reporter.py`        | Markdown/structured report                              |
| Core          | `core/pipeline.py`        | Stage orchestration (no AI inside)                      |
| Data          | `data/loader.py`          | CSV/JSON/JSONL/Excel/Parquet ingestion                  |
| Data          | `data/schema.py`          | Schema inference → LLM-safe metadata                    |
| Data          | `data/storage.py`         | SQLite / Parquet / local files                          |
| AI            | `ai/client.py`            | OpenRouter chat wrapper (httpx)                         |
| AI            | `ai/prompts.py`           | Metadata-only prompt builders                           |
| AI            | `ai/analyzer.py`          | Orchestrates metadata → LLM → validated output          |
| AI            | `ai/parser.py`            | Strict Pydantic validation of model output              |
| UI            | `ui/*.py`                 | Streamlit pages                                         |

## Data flow

1. **Ingestion** — `loader` → DataFrame
2. **Profiling** — `profiler` → compact stats (rows, nulls, dupes, dtypes)
3. **Validation** — `validator` → deterministic `QualityIssue[]`
4. **AI analysis** — schema + profile + issues (metadata ONLY) → OpenRouter → JSON
5. **Validation of AI output** — `parser` (Pydantic) → `Analysis` / `FixPlan`
6. **Execution** — `transformer` applies only registered transforms
7. **Report** — `reporter` → markdown + summary

## Safety invariants

- The LLM only ever sees `profile.to_dict()`, `schema.to_dict()`, and issue dicts.
- Model output must pass Pydantic validation and column-guard checks before execution.
- All transforms are selected from `TRANSFORMATIONS` by name; unknown names and
  unknown columns raise errors. There is no `eval` / dynamic code anywhere.
- Software versions: Python 3.14, pandas 3.0 (ISO8601-only `to_datetime` by
  default; `standardize_dates` retries with `format="mixed"`).