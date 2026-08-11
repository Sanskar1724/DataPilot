# DataPilot — Project Documentation

*AI-Assisted Data Engineering: profile dirty data deterministically, explain the
problems with a small open LLM, apply only safe transformations, and ship a
clean dataset + quality report.*

---

## 1. What this project is

DataPilot lets a user upload a messy file (CSV / JSON / JSONL / Excel / Parquet)
and get:

1. A **deterministic profile** (rows, columns, duplicates, missing values, stats)
2. A **deterministic quality report** (6 built-in rules, severity-graded)
3. An **AI explanation** of what's wrong (OpenRouter + small open model)
4. An **AI-suggested, schema-guarded Fix Plan**
5. A **clean dataset** produced by *safe, registered transformations only*
6. Downloadable output + a markdown report

The guiding architectural principle:

```
            DATA
             │
             ▼
  Deterministic Processing   (Pandas / rules — never the LLM)
             │
             ▼
          Metadata            (schema + stats + issues, tiny)
             │
             ▼
        7-9B Open LLM         (OpenRouter)
             │
             ▼
  Reasoning / Recommendation  (structured JSON fix plan)
             │
             ▼
  Deterministic Execution     (registered transforms only)
```

**The LLM never touches raw rows.** It reasons over metadata. Deterministic
code does all data processing. This keeps the project cheap, fast, safe, and
credible.

---

## 2. Tech stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ (developed on 3.14) |
| UI | Streamlit |
| Data processing | pandas |
| Quality rules | `app/core/validator.py` (custom, vectorized) |
| Storage | SQLite + Parquet + local files |
| LLM access | OpenRouter (`httpx`) |
| Model (current) | `google/gemma-4-26b-a4b-it:free` |
| Config | `python-dotenv` (`.env`) |
| Testing | pytest (40 tests) |
| Version control | Git / GitHub |

---

## 3. Repository layout

```
S:\DataPilot
├── app/
│   ├── main.py              Streamlit entrypoint (navigation + sidebar)
│   ├── core/
│   │   ├── profiler.py      deterministic column statistics
│   │   ├── validator.py     6 quality detectors + issue model
│   │   ├── transformer.py   safe transform registry + FixPlan
│   │   ├── reporter.py      markdown/structured report
│   │   └── pipeline.py      orchestrator (ingest→profile→validate→plan→apply)
│   ├── data/
│   │   ├── loader.py        CSV/JSON/JSONL/Excel/Parquet (+bytes)
│   │   ├── schema.py        schema inference → LLM-safe metadata
│   │   └── storage.py       SQLite / Parquet / local files
│   ├── ai/
│   │   ├── client.py        OpenRouter wrapper (retries, usage, headers)
│   │   ├── prompts.py       metadata-only prompt builders
│   │   ├── analyzer.py      metadata → LLM → validated plan orchestration
│   │   └── parser.py        Pydantic validation of model JSON
│   ├── ui/
│   │   ├── dashboard.py     overview + severity charts
│   │   ├── upload.py        file upload + run pipeline
│   │   ├── quality_report.py issue table + AI explanation
│   │   ├── pipeline_view.py generate plan → review → apply → download
│   │   └── state.py         shared session state
│   └── utils/
│       ├── config.py        env settings
│       ├── logger.py        logging setup
│       └── helpers.py       JSON-safe serialization, paths, formatting
├── scripts/
│   └── run_pipeline.py      headless CLI (see §9)
├── tests/                   pytest suite (test_loader, profiler, validator,
│                            transformer, pipeline, ai, ui)
├── data/
│   ├── raw/                 user uploads / inputs
│   ├── processed/           cleaned outputs (Parquet/CSV)
│   └── sample/              sales_dirty.csv (12,005 rows)
├── reports/                 generated *_quality_*.md files
├── docs/                    architecture.md, pipeline.md, ai-design.md
├── GUIDE.md                 step-by-step getting-started guide
├── PROJECT_DOCUMENTATION.md this file
├── .env.example             template for configuration
├── .env                     YOUR SECRETS (gitignored)
├── requirements.txt
└── README.md
```

---

## 4. Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | — | OpenRouter key (required for AI) |
| `OPENROUTER_MODEL` | `google/gemma-4-26b-a4b-it:free` | Model id; swap freely |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | API base |
| `OPENROUTER_TIMEOUT` | `60` | Per-call timeout (s) |
| `OPENROUTER_HTTP_REFERER` | — | Optional attribution header |
| `OPENROUTER_APP_NAME` | — | Optional `X-Title` header |
| `DATAPILOT_AI_ENABLED` | `true` | Master switch for the AI layer |
| `DATAPILOT_LOG_LEVEL` | `INFO` | Logging level |

`app/utils/config.py` caches settings via `get_settings()`. Environment
variables are loaded from `.env` (dotenv), and read the same when running on
Streamlit Cloud secrets.

---

## 5. Core engine

### 5.1 Profiler (`app/core/profiler.py`)

- Fully vectorized; never iterates rows, so it stays fast on large frames.
- Produces a `Profile`: rows, columns, duplicate count/pct, memory, and per
  column: dtype, nulls (count + %), unique count, min/max/mean/std, samples.
- `Profile.to_dict()` is a **JSON-safe metadata** object (timestamps/NaN
  normalized) ready for LLM prompts or reports.

### 5.2 Validator (`app/core/validator.py`)

Six deterministic detectors. Each returns `QualityIssue` objects with a
severity (`low|medium|high`) and affected count/%:

| Detector | Detects |
|---|---|
| `detect_missing_values` | per-column null rate |
| `detect_duplicates` | exact duplicate rows |
| `detect_negatives` | negative values in logically-non-negative columns (name-hint based) |
| `detect_dates` | mixed date formats via *format-signature* analysis (handles pandas 3 ISO-only parsing) |
| `detect_constant_columns` | zero-cardinality columns |
| `detect_outliers` | robust z-score (MAD) with classic z-score fallback when MAD=0 |

- Issues are sorted high→low severity, then by row-share.
- A detector exception is logged + skipped — it never aborts the pipeline.

### 5.3 Transformer (`app/core/transformer.py`)

The **only** place where the data can change. A fixed registry:

| name | arguments |
|---|---|
| `drop_duplicates` | `subset: list[str] \| None` |
| `fill_missing` | `strategy: drop\|constant\|mean\|median\|mode\|fwd\|bwd`, `value` |
| `standardize_dates` | — (tries ISO, falls back to `format="mixed"`) |
| `clip_negatives` | — (max 0) |
| `flag_negatives` | `flag_column` |
| `standardize_strings` | `mode: strip\|lower\|title` |

Safety:
- **No arbitrary code.** Transforms are selected by name from
  `TRANSFORMATIONS`; unknown names raise `UnknownTransformationError`.
- **Column-guarded.** Unknown columns are rejected.
- `FixPlan` = ordered list of `TransformStep`; `plan.apply(df)` executes steps
  deterministically on a copy.

### 5.4 Pipeline (`app/core/pipeline.py`)

The orchestrator is AI-free on purpose:

- `run_deterministic(source)` → ingestion → profiling → validation → base report.
- `apply_plan(result, plan)` → executes a validated `FixPlan`, re-profiles the
  cleaned frame, rebuilds the report with transformation history.
- `run_full(source, plan=None)`.

### 5.5 Reporter (`app/core/reporter.py`)

- `Report.summary()` → JSON-safe counts (rows, issues, auto-fixed, review).
- `Report.to_markdown()` → readable REPORT block.
- `write_report_file(report)` → writes `<name>_quality_<timestamp>.md`.

---

## 6. AI layer

Flow:

```
Schema + Profile + Issues  (metadata ONLY)
        │
        ▼
  prompts.py builds messages  (never includes raw rows)
        │
        ▼
  client.py → OpenRouter /chat/completions  (httpx, retries, usage)
        │
        ▼
  parser.py → Pydantic Analysis  (strict, column+transform guarded)
        │
        ▼
  Analysis.to_fix_plan(guard_columns) → FixPlan
        │
        ▼
  transformer executes deterministically
```

### 6.1 What the model is allowed to do

- Understand schema semantics
- Explain data-quality problems
- Classify suspicious columns/values
- Suggest transformations (from the catalog only)
- Generate a structured fix plan

### 6.2 What it must never do

- Process the CSV / iterate rows
- Execute arbitrary Python
- Invent transform names or column names
- Modify files

### 6.3 Validation guarantees

- JSON is extracted (tolerates ``` fences).
- `Analysis.model_validate()` requires the exact contract shape.
- Transform names must exist in the registry.
- Column names must exist in the actual schema (`guard_columns` is derived from
  the real DataFrame, never from model output).
- Failures raise `ValueError` — surfaced as UI warnings, never silently applied.

### 6.4 Robustness (`app/ai/client.py`)

- Exponential-backoff retries for `429 / 5xx / timeout`.
- If a provider rejects `response_format` (structured output), the analyzer
  retries without it via a prompt-only request (`UnsupportedFeatureError`).
- Per-call usage (`prompt_tokens`, `completion_tokens`, `latency_ms`) returned
  and shown in the UI.

### 6.5 Cost control

- Only metadata is sent → prompt size is independent of dataset size.
- `temperature=0`, `max_tokens` capped.
- Current model is a free tier; paid models cost ~fractions of a cent per run.

---

## 7. UI pages (Streamlit)

| Page | Purpose |
|---|---|
| Dashboard | Metrics + severity distribution + applied transforms |
| Upload Data | File upload → run pipeline → profile preview |
| Quality Report | Deterministic issues table, samples, AI explanation |
| AI Fix Plan | Generate plan → review table → approve → apply → download clean CSV/Parquet |

Session state is kept in `app/ui/state.py` (`raw`, `result`, `plan`, `analysis`,
`source_name`) so pages share one pipeline run.

---

## 8. Tests

`tests/` — 40 tests:

| File | Covers |
|---|---|
| `test_loader.py` | file + bytes ingestion, errors |
| `test_profiler.py` | counts, duplicates, nulls, JSON safety |
| `test_validator.py` | each detector + severity sorting |
| `test_transformer.py` | each transform + registry safety |
| `test_pipeline.py` | end-to-end deterministic + plan apply + sample data |
| `test_ai.py` | parser validation, guard rails, fallbacks (mocked, no network) |
| `test_ui.py` | Streamlit app smoke tests (no browser) |

```powershell
python -m pytest -q
```

---

## 9. CLI (`scripts/run_pipeline.py`)

Headless equivalent of the UI:

```powershell
python scripts/run_pipeline.py <file> [--ai] [--no-ai] [--report] [--no-report] [--clean-csv out.csv]
```

Prints the report to stdout; optionally saves the report and cleaned dataset.

---

## 10. Deployment

See **GUIDE.md §8** for the full walkthrough. In short:

1. Push to GitHub (`.env` stays out of git).
2. New app on **https://share.streamlit.io** → repo, branch `main`, file `app/main.py`.
3. Put `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` / `DATAPILOT_AI_ENABLED` in
   **Settings → Secrets** (dotenv reads them too).
4. Open the generated `https://<name>.streamlit.app` URL.

---

## 11. Extending

- **New quality rule**: add a function `detect_*(df) -> list[QualityIssue]` in
  `app/core/validator.py` and append it to `DETECTORS`.
- **New transformation**: add `_name(df, column, args)` in
  `app/core/transformer.py` and register it in `TRANSFORMATIONS` (+ update the
  AI prompt catalog in `app/ai/prompts.py`).
- **New model**: change `OPENROUTER_MODEL` only — no code changes.
- **New file type**: add a reader in `app/data/loader.py` + `SUPPORTED_EXTENSIONS`.

---

## 12. Roadmap (from the original design)

- [x] Phase 1 — Data Engine
- [x] Phase 2 — AI Layer (explanation)
- [x] Phase 3 — AI Recommendations (structured, validated Fix Plan)
- [x] Phase 4 — Transformation (safe execution)
- [x] Phase 5 — UI (loop: Upload → Analyze → Explain → Review → Apply → Download)
- [ ] Phase 6 — Evaluation (measure detection accuracy, recommendation accuracy,
      latency, token usage, failed responses, false +/-). The completion object
      already records latency/tokens to support this.

---

## 13. Safety notes

- The LLM does not execute code; it only emits JSON which is validated.
- All data mutation runs through the transform registry.
- Secrets live only in `.env` / Streamlit secrets, never in the repo.
- Detector failures degrade gracefully (logged, skipped).