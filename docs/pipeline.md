# Pipeline

## Stages

| Stage         | Module            | Output                              |
|---------------|-------------------|-------------------------------------|
| Ingestion     | `data.loader`     | `pd.DataFrame`                      |
| Profiling     | `core.profiler`   | `Profile` (stats per column)        |
| Validation    | `core.validator`  | `list[QualityIssue]`                |
| AI analysis   | `ai.analyzer`     | `Analysis` + `FixPlan` + `Completion` |
| Transformation| `core.transformer`| Clean `pd.DataFrame`                |
| Reporting     | `core.reporter`   | `Report` (markdown + summary)       |

Usage (headless, no UI):

```python
from app.core.pipeline import Pipeline
from app.core.transformer import FixPlan, TransformStep

pipe = Pipeline(name="sales")
result, _ = pipe.run_deterministic("data/sample/sales_dirty.csv")

plan = FixPlan(steps=[
    TransformStep("drop_duplicates"),
    TransformStep("fill_missing", column="customer_id",
                  args={"strategy": "constant", "value": "UNKNOWN"}),
    TransformStep("clip_negatives", column="revenue"),
])
result = pipe.apply_plan(result, plan)
print(result.report.to_markdown())
```

## Quality detectors (`core.validator.py`)

1. `detect_missing_values` — per-column null rate → low/medium/high
2. `detect_duplicates` — exact duplicate rows
3. `detect_negatives` — negative values in logically non-negative columns
   (name-hint based: count, qty, revenue, price, ...)
4. `detect_dates` — mixed date-format detection via format signatures
   (catches `2024-01-01` mixed with `01/02/2024`; pandas 3 default parser
   would otherwise miss it)
5. `detect_constant_columns` — single distinct value
6. `detect_outliers` — robust z-score (MAD); falls back to classic z-score
   when MAD == 0

All detectors are vectorized and never iterate rows. A detector failure is
logged and skipped, it does not abort the pipeline.

## Transformation registry (`core.transformer.py`)

| name                  | args                                                                |
|-----------------------|---------------------------------------------------------------------|
| `drop_duplicates`     | `subset: list[str] \| None`                                        |
| `fill_missing`        | `strategy: drop\|constant\|mean\|median\|mode\|fwd\|bwd`, `value`   |
| `standardize_dates`   | —                                                                   |
| `clip_negatives`      | —                                                                   |
| `flag_negatives`      | `flag_column: str`                                                  |
| `standardize_strings` | `mode: strip\|lower\|title`                                         |

Unknown names / missing columns raise `UnknownTransformationError`.