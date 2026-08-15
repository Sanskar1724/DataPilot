"""Headless CLI to run the DataPilot pipeline on a file.

Usage:
    python scripts/run_pipeline.py <file> [--ai|--no-ai]
                                   [--report] [--no-report] [--clean-csv out.csv]

Examples:
    python scripts/run_pipeline.py data/sample/sales_dirty.csv --ai
    python scripts/run_pipeline.py data/sample/sales_dirty.csv --no-ai --clean-csv data/processed/clean.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.analyzer import Analyzer, build_metadata  # noqa: E402
from app.core.pipeline import Pipeline  # noqa: E402
from app.core.reporter import write_report_file  # noqa: E402
from app.data.schema import infer_schema  # noqa: E402
from app.utils.config import get_settings  # noqa: E402
from app.utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the DataPilot pipeline on a file.")
    p.add_argument("file", help="Path to a CSV/JSON/JSONL/Excel/Parquet file")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--ai", action="store_true", default=None, help="Use the AI fix plan (default if key set)")
    group.add_argument("--no-ai", action="store_true", help="Deterministic only")
    p.add_argument("--report", action="store_true", default=True, help="Write the markdown report (default)")
    p.add_argument("--no-report", action="store_true", help="Skip writing the report file")
    p.add_argument("--clean-csv", help="Also save the clean dataset to this CSV path")
    p.add_argument("--clean-parquet", help="Also save the clean dataset to this Parquet path")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = get_settings()

    pipe = Pipeline(name="cli")
    result, _ = pipe.run_deterministic(args.file)
    print(result.report.to_markdown())
    print()

    if args.ai is True:
        use_ai = True
    elif args.no_ai:
        use_ai = False
    else:
        use_ai = settings.ai_enabled and settings.has_api_key

    if use_ai:
        schema = infer_schema(result.raw)
        metadata = build_metadata(
            result.profile.to_dict(), schema.to_dict(), result.issues
        )
        guard = set(result.raw.columns)
        print("Asking the model for a fix plan...")
        analyzer = Analyzer()
        try:
            analysis, plan, completion = analyzer.analyze_and_plan(metadata, guard)
            print(f"  explanation: {analysis.explanation or '(none)'}")
            print(f"  issues: {len(analysis.issues)} | steps: {len(plan.steps)}")
            print(f"  tokens: {completion.total_tokens} | latency: {completion.latency_ms} ms")
            result = pipe.apply_plan(result, plan)
        except Exception as exc:  # noqa: BLE001 — CLI should never crash hard
            print(f"  AI step failed: {exc}")
            print("  Falling back to the deterministic-only result.")
        print()
        print(result.report.to_markdown())

    if args.report and not args.no_report:
        path = write_report_file(result.report, directory="reports")
        print(f"Report: {path}")
    if args.clean_csv:
        result.cleaned.to_csv(args.clean_csv, index=False, encoding="utf-8")
        print(f"Clean CSV: {args.clean_csv}")
    if args.clean_parquet:
        result.cleaned.to_parquet(args.clean_parquet, index=False)
        print(f"Clean Parquet: {args.clean_parquet}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))