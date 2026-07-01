#!/usr/bin/env python3
"""Run SEC pipeline, validation sample, and panel build."""

from __future__ import annotations

from oaa_observatory.cli import panel_build, pipeline_run, validation_run, validation_sample


def main() -> None:
    pipeline_run(source="sec", log_level="INFO")
    validation_sample()
    validation_run()
    panel_build()


if __name__ == "__main__":
    main()
