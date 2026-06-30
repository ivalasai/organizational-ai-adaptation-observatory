#!/usr/bin/env python3
"""Run all enabled pipelines sequentially."""

from __future__ import annotations

from oaa_observatory.cli import pipeline_run
from oaa_observatory.utils.logging import configure_logging

PIPELINES = ["sec", "earnings_calls", "patents", "jobs", "products"]


def main() -> None:
    configure_logging(level="INFO")
    for source in PIPELINES:
        print(f"\n=== Running {source} pipeline ===")
        pipeline_run(source=source, log_level="INFO")


if __name__ == "__main__":
    main()
