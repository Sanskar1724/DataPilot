"""Report generation: human-readable quality report + structured summary."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.profiler import Profile
from app.core.validator import QualityIssue

from app.utils.helpers import human_number, ensure_dir
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Report:
    """Aggregated pipeline result (deterministic, JSON-safe)."""

    profile: Profile
    issues: list[QualityIssue] = field(default_factory=list)
    auto_fixed_count: int = 0
    needs_review_count: int = 0
    transformations: list[dict[str, Any]] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())

    def summary(self) -> dict[str, Any]:
        issues_found = len(self.issues)
        return {
            "rows_processed": self.profile.rows,
            "columns": self.profile.columns,
            "issues_found": issues_found,
            "auto_fixed": self.auto_fixed_count,
            "needs_review": self.needs_review_count,
            "generated_at": self.generated_at,
        }

    def to_markdown(self) -> str:
        """Render a `REPORT`-style block (like the architecture diagram)."""
        p = self.profile
        lines = [
            "                    REPORT",
            "─────────────────────────────────────────────",
            f"Dataset             {p.name}",
            f"Rows processed      {human_number(p.rows)}",
            f"Columns             {p.columns}",
            f"Duplicates          {human_number(p.duplicates)} ({p.duplicate_pct:.1%})",
            "",
            f"Issues found        {len(self.issues)}",
            f"Auto-fixed          {self.auto_fixed_count}",
            f"Needs review        {self.needs_review_count}",
            "",
            "Definitions by column:",
        ]
        for col, stats in p.column_stats.items():
            lines.append(f"  {col}: {stats.dtype}, nulls {stats.null_pct:.1%}")
        if self.issues:
            lines.append("")
            lines.append("Quality issues:")
            for issue in self.issues:
                lines.append(
                    f"  [{issue.severity.upper():6s}] {issue.column or '(dataset)'}: "
                    f"{issue.problem} ({human_number(issue.count)})"
                )
        if self.transformations:
            lines.append("")
            lines.append("Applied transformations:")
            for t in self.transformations:
                lines.append(f"  - {t.get('name', '')} on {t.get('column', '-')}")
        lines.append(f"Generated: {self.generated_at}")
        return "\n".join(lines)


def build_report(
    profile: Profile,
    issues: list[QualityIssue],
    transformations: list[dict[str, Any]] | None = None,
) -> Report:
    """Assemble a Report from profile + issues + applied transforms."""
    report = Report(
        profile=profile,
        issues=issues,
        transformations=transformations or [],
    )
    report.auto_fixed_count = len(report.transformations)
    report.needs_review_count = len(issues)
    return report


def write_report_file(report: Report, directory: str = "reports") -> str:
    """Write the markdown report to the reports directory, return its path."""
    out_dir = ensure_dir(directory)
    safe_name = "".join(c for c in report.profile.name if c.isalnum() or c in "_-") or "dataset"
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"{safe_name}_quality_{stamp}.md"
    path.write_text(report.to_markdown(), encoding="utf-8")
    logger.info("Wrote report to %s", path)
    return str(path)