"""Command-line interface for the Organizational AI Adaptation Observatory."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from oaa_observatory import __version__
from oaa_observatory.config.settings import get_settings
from oaa_observatory.earnings_calls import EarningsCallsPipeline
from oaa_observatory.entity_resolution import EntityResolver, IdentifierType
from oaa_observatory.jobs import JobsPipeline
from oaa_observatory.panel_builder import PanelBuilder
from oaa_observatory.patents import PatentsPipeline
from oaa_observatory.products import ProductsPipeline
from oaa_observatory.quality_checks import PanelQualityChecker
from oaa_observatory.schemas.records import FirmIdentifier
from oaa_observatory.sec import SECFilingsPipeline
from oaa_observatory.utils.logging import configure_logging

app = typer.Typer(
    name="oaa",
    help="Organizational AI Adaptation Observatory — firm-level AI signal infrastructure",
    no_args_is_help=True,
)
console = Console()

pipeline_app = typer.Typer(help="Run data ingestion pipelines")
panel_app = typer.Typer(help="Build and validate firm-year panels")
entity_app = typer.Typer(help="Entity resolution utilities")

app.add_typer(pipeline_app, name="pipeline")
app.add_typer(panel_app, name="panel")
app.add_typer(entity_app, name="entity")


def _setup(log_level: str) -> None:
    settings = get_settings()
    configure_logging(level=log_level or settings.log_level)
    settings.ensure_directories()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit",
    ),
) -> None:
    """Organizational AI Adaptation Observatory CLI."""
    if version:
        console.print(f"oaa-observatory {__version__}")
        raise typer.Exit()


@pipeline_app.command("list")
def pipeline_list() -> None:
    """List available data pipelines."""
    table = Table(title="Available Pipelines")
    table.add_column("Name", style="cyan")
    table.add_column("Signal Layer", style="green")
    table.add_column("Status")

    pipelines = [
        ("sec", "attention", "skeleton"),
        ("earnings_calls", "attention", "skeleton"),
        ("patents", "investment", "skeleton"),
        ("jobs", "investment", "skeleton"),
        ("products", "deployment", "skeleton"),
    ]
    for name, layer, status in pipelines:
        table.add_row(name, layer, status)

    console.print(table)


@pipeline_app.command("run")
def pipeline_run(
    source: str = typer.Argument(..., help="Pipeline source name"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Run a single data pipeline end-to-end."""
    _setup(log_level)

    pipeline_map = {
        "sec": SECFilingsPipeline,
        "earnings_calls": EarningsCallsPipeline,
        "patents": PatentsPipeline,
        "jobs": JobsPipeline,
        "products": ProductsPipeline,
    }

    if source not in pipeline_map:
        console.print(f"[red]Unknown pipeline: {source}[/red]")
        console.print(f"Available: {', '.join(pipeline_map)}")
        raise typer.Exit(code=1)

    pipeline = pipeline_map[source]()
    output = pipeline.run()
    console.print(f"[green]Pipeline complete:[/green] {output}")


@panel_app.command("build")
def panel_build(
    config: Path = typer.Option(
        Path("configs/pipeline/panel_builder.toml"),
        "--config",
        "-c",
        help="Panel builder configuration file",
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Build firm-year panel from feature tables."""
    _setup(log_level)

    builder = PanelBuilder.from_config_file(config)
    output = builder.run()
    console.print(f"[green]Panel built:[/green] {output}")


@panel_app.command("validate")
def panel_validate(
    panel_path: Path = typer.Argument(..., help="Path to panel Parquet file"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Run quality checks on a firm-year panel."""
    _setup(log_level)

    import pandas as pd

    panel = pd.read_parquet(panel_path)
    checker = PanelQualityChecker()
    report = checker.check(panel)

    table = Table(title="Quality Check Report")
    table.add_column("Check")
    table.add_column("Passed")
    table.add_column("Message")

    for check in report.checks:
        status = "[green]PASS[/green]" if check.passed else "[red]FAIL[/red]"
        table.add_row(check.name, status, check.message)

    console.print(table)

    if not report.passed:
        raise typer.Exit(code=1)


@entity_app.command("resolve")
def entity_resolve(
    identifier_type: str = typer.Argument(..., help="Identifier type (gvkey, cik, ticker, etc.)"),
    value: str = typer.Argument(..., help="Identifier value"),
    mapping_path: Path = typer.Option(
        Path("data/intermediate/entity_resolution/mappings.parquet"),
        "--mapping",
        "-m",
    ),
) -> None:
    """Resolve an identifier to canonical firm_id."""
    resolver = EntityResolver.load(mapping_path)
    firm_id = resolver.resolve(IdentifierType(identifier_type), value)

    if firm_id:
        console.print(f"[green]firm_id:[/green] {firm_id}")
    else:
        console.print("[yellow]No mapping found[/yellow]")
        raise typer.Exit(code=1)


@entity_app.command("register")
def entity_register(
    gvkey: str | None = typer.Option(None, "--gvkey"),
    cik: str | None = typer.Option(None, "--cik"),
    ticker: str | None = typer.Option(None, "--ticker"),
    cusip: str | None = typer.Option(None, "--cusip"),
    permno: int | None = typer.Option(None, "--permno"),
    company_name: str | None = typer.Option(None, "--name"),
    mapping_path: Path = typer.Option(
        Path("data/intermediate/entity_resolution/mappings.parquet"),
        "--mapping",
        "-m",
    ),
) -> None:
    """Register a firm identifier mapping."""
    record = FirmIdentifier(
        firm_id="",
        gvkey=gvkey,
        cik=cik,
        ticker=ticker,
        cusip=cusip,
        permno=permno,
        company_name=company_name,
        source="cli",
    )
    resolver = EntityResolver.load(mapping_path)
    firm_id = resolver.register(record)
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    resolver.save(mapping_path)
    console.print(f"[green]Registered firm_id:[/green] {firm_id}")


if __name__ == "__main__":
    app()
