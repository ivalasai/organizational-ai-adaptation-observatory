"""Example: build firm-year panel from feature tables."""

from pathlib import Path

from oaa_observatory.panel_builder import PanelBuilder
from oaa_observatory.quality_checks import PanelQualityChecker
from oaa_observatory.utils.logging import configure_logging


def main() -> None:
    configure_logging(level="INFO")

    config_path = Path("configs/pipeline/panel_builder.toml")
    builder = PanelBuilder.from_config_file(config_path)
    output = builder.run()
    print(f"Panel written to: {output}")

    import pandas as pd

    panel = pd.read_parquet(output)
    report = PanelQualityChecker().check(panel)
    print(f"Quality checks passed: {report.passed}")
    for check in report.checks:
        print(f"  [{check.name}] {check.message}")


if __name__ == "__main__":
    main()
