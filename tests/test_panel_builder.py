"""Tests for panel builder."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from oaa_observatory.config.models import PanelBuilderConfig
from oaa_observatory.panel_builder import PanelBuilder
from oaa_observatory.quality_checks import PanelQualityChecker


class TestPanelBuilder:
    """Panel builder test cases."""

    def test_build_empty_panel(self, tmp_path: Path) -> None:
        settings_data = tmp_path / "data"
        config = PanelBuilderConfig(
            output_path=settings_data / "panel" / "firm_year_panel.parquet",
            feature_tables=["attention/sec"],
        )
        from oaa_observatory.config.settings import Settings

        settings = Settings(data_root=settings_data)
        builder = PanelBuilder(config=config, settings=settings)
        panel = builder.build()
        assert list(panel.columns) == ["firm_id", "year"] or panel.empty

    def test_build_with_features(self, tmp_path: Path) -> None:
        features_dir = tmp_path / "data" / "features" / "attention" / "sec"
        features_dir.mkdir(parents=True)
        df = pd.DataFrame(
            {
                "firm_id": ["OAA-abc", "OAA-abc", "OAA-def"],
                "year": [2020, 2021, 2020],
                "source": ["sec"] * 3,
                "ai_mention_count": [5, 10, 2],
            }
        )
        df.to_parquet(features_dir / "firm_year.parquet")

        from oaa_observatory.config.settings import Settings

        settings = Settings(data_root=tmp_path / "data")
        config = PanelBuilderConfig(
            feature_tables=["attention/sec"],
            output_path=tmp_path / "data" / "panel" / "panel.parquet",
        )
        builder = PanelBuilder(config=config, settings=settings)
        panel = builder.build()
        assert len(panel) == 3
        assert "attention_sec_ai_mention_count" in panel.columns

    def test_quality_checks_pass(self) -> None:
        panel = pd.DataFrame(
            {
                "firm_id": ["OAA-a", "OAA-b"],
                "year": [2020, 2021],
                "ai_mention_count": [1, 2],
            }
        )
        checker = PanelQualityChecker()
        report = checker.check(panel)
        assert report.passed

    def test_quality_checks_duplicate_fail(self) -> None:
        panel = pd.DataFrame(
            {
                "firm_id": ["OAA-a", "OAA-a"],
                "year": [2020, 2020],
            }
        )
        checker = PanelQualityChecker()
        report = checker.check(panel)
        assert not report.passed
