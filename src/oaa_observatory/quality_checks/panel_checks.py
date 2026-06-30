"""Data quality validation for pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from oaa_observatory.utils.logging import logger


@dataclass
class QualityCheckResult:
    """Result of a single quality check."""

    name: str
    passed: bool
    message: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass
class QualityReport:
    """Aggregated quality check report."""

    checks: list[QualityCheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return True if all checks passed."""
        return all(c.passed for c in self.checks)

    def add(self, result: QualityCheckResult) -> None:
        """Add a check result to the report."""
        self.checks.append(result)
        level = "info" if result.passed else "warning"
        getattr(logger, level)(
            "Quality check [{}]: {} - {}",
            result.name,
            result.passed,
            result.message,
        )


class PanelQualityChecker:
    """Run quality checks on firm-year panel data."""

    REQUIRED_COLUMNS = ("firm_id", "year")

    def check(self, panel: pd.DataFrame) -> QualityReport:
        """Run all quality checks on a panel.

        Args:
            panel: Firm-year panel DataFrame.

        Returns:
            QualityReport with all check results.
        """
        report = QualityReport()
        report.add(self._check_required_columns(panel))
        report.add(self._check_duplicate_keys(panel))
        report.add(self._check_year_range(panel))
        report.add(self._check_null_firm_ids(panel))
        return report

    def _check_required_columns(self, panel: pd.DataFrame) -> QualityCheckResult:
        missing = [c for c in self.REQUIRED_COLUMNS if c not in panel.columns]
        return QualityCheckResult(
            name="required_columns",
            passed=len(missing) == 0,
            message="All required columns present" if not missing else f"Missing: {missing}",
            details={"missing_columns": missing},
        )

    def _check_duplicate_keys(self, panel: pd.DataFrame) -> QualityCheckResult:
        if panel.empty:
            return QualityCheckResult(
                name="duplicate_keys",
                passed=True,
                message="Empty panel; no duplicates",
            )
        dupes = panel.duplicated(subset=["firm_id", "year"], keep=False).sum()
        return QualityCheckResult(
            name="duplicate_keys",
            passed=dupes == 0,
            message=f"Found {dupes} duplicate firm_id-year rows",
            details={"duplicate_count": int(dupes)},
        )

    def _check_year_range(self, panel: pd.DataFrame) -> QualityCheckResult:
        if panel.empty or "year" not in panel.columns:
            return QualityCheckResult(
                name="year_range",
                passed=True,
                message="No year data to validate",
            )
        min_year = int(panel["year"].min())
        max_year = int(panel["year"].max())
        return QualityCheckResult(
            name="year_range",
            passed=True,
            message=f"Year range: {min_year}-{max_year}",
            details={"min_year": min_year, "max_year": max_year},
        )

    def _check_null_firm_ids(self, panel: pd.DataFrame) -> QualityCheckResult:
        if panel.empty:
            return QualityCheckResult(
                name="null_firm_ids",
                passed=True,
                message="Empty panel",
            )
        null_count = int(panel["firm_id"].isna().sum())
        return QualityCheckResult(
            name="null_firm_ids",
            passed=null_count == 0,
            message=f"Found {null_count} null firm_id values",
            details={"null_count": null_count},
        )
