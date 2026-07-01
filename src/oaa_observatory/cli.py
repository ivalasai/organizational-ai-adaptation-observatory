"""Command-line interface for the Organizational AI Adaptation Observatory."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from oaa_observatory import __version__
from oaa_observatory.config.settings import get_settings
from oaa_observatory.entity_resolution import EntityResolver, IdentifierType
from oaa_observatory.panel_builder import PanelBuilder
from oaa_observatory.quality_checks import PanelQualityChecker
from oaa_observatory.sec import SECFilingsPipeline
from oaa_observatory.utils.logging import configure_logging
from oaa_observatory.validation import (
    compute_validation_metrics,
    generate_validation_sample,
    render_pending_template,
    write_validation_report,
)

app = typer.Typer(
    name="oaa",
    help="Organizational AI Adaptation Observatory — SEC attention signals",
    no_args_is_help=True,
)
console = Console()

pipeline_app = typer.Typer(help="Run data ingestion pipelines")
panel_app = typer.Typer(help="Build and validate firm-year panels")
entity_app = typer.Typer(help="Entity resolution utilities")
validation_app = typer.Typer(help="Classifier validation workflow")

app.add_typer(pipeline_app, name="pipeline")
app.add_typer(panel_app, name="panel")
app.add_typer(entity_app, name="entity")
app.add_typer(validation_app, name="validation")


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
    table.add_column("Layer", style="green")
    table.add_column("Status")
    table.add_row("sec", "attention", "active")
    console.print(table)


@pipeline_app.command("run")
def pipeline_run(
    source: str = typer.Argument(..., help="Pipeline source name (sec)"),
    config: Path = typer.Option(
        Path("configs/datasources/sec.toml"),
        "--config",
        "-c",
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Run a data pipeline end-to-end."""
    _setup(log_level)

    if source != "sec":
        console.print(f"[red]Unknown pipeline: {source}[/red] (only 'sec' is available)")
        raise typer.Exit(code=1)

    pipeline = SECFilingsPipeline.from_config_file(config)
    output = pipeline.run()
    console.print(f"[green]Pipeline complete:[/green] {output}")


@panel_app.command("build")
def panel_build(
    config: Path = typer.Option(
        Path("configs/pipeline/panel_builder.toml"),
        "--config",
        "-c",
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
    report = PanelQualityChecker().check(panel)
    for check in report.checks:
        status = "[green]PASS[/green]" if check.passed else "[red]FAIL[/red]"
        console.print(f"{check.name}: {status} — {check.message}")
    if not report.passed:
        raise typer.Exit(code=1)


@entity_app.command("resolve")
def entity_resolve(
    identifier_type: str = typer.Argument(...),
    value: str = typer.Argument(...),
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


@entity_app.command("bootstrap")
def entity_bootstrap(
    universe_path: Path = typer.Option(Path("data/universe/firm_universe.csv")),
    mapping_path: Path = typer.Option(
        Path("data/intermediate/entity_resolution/mappings.parquet"),
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Bootstrap entity resolution from SEC company_tickers.json."""
    _setup(log_level)
    from oaa_observatory.sec.bootstrap import bootstrap_entity_resolution

    settings = get_settings()
    resolver = bootstrap_entity_resolution(
        universe_path=universe_path,
        mapping_path=mapping_path,
        user_agent=settings.sec_user_agent,
    )
    console.print(f"[green]Mapped {len(resolver.mapping_table)} firms[/green]")


@validation_app.command("sample")
def validation_sample(
    documents: Path = typer.Option(
        Path("data/intermediate/sec/documents.parquet"),
        "--documents",
    ),
    labeling: Path = typer.Option(
        Path("data/validation/attention_labeling.csv"),
        "--labeling",
    ),
    scores: Path = typer.Option(
        Path("data/validation/attention_scores.csv"),
        "--scores",
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Generate blind labeling sample + separate model scores file."""
    _setup(log_level)
    labeling_path, scores_path = generate_validation_sample(documents, labeling, scores)
    console.print(f"[green]Wrote blind labeling file:[/green] {labeling_path}")
    console.print(f"[dim]Wrote model scores (do not open while labeling):[/dim] {scores_path}")


@validation_app.command("run")
def validation_run(
    labels: Path = typer.Option(
        Path("data/validation/attention_labeling.csv"),
        "--labels",
    ),
    scores: Path = typer.Option(
        Path("data/validation/attention_scores.csv"),
        "--scores",
    ),
    report: Path = typer.Option(
        Path("docs/validation/attention_classifier_validation.md"),
        "--report",
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Compute validation metrics or write pending template."""
    _setup(log_level)
    try:
        metrics = compute_validation_metrics(labels, scores)
        write_validation_report(metrics, report, labels, scores)
        console.print(f"[green]Validation report:[/green] {report}")
        console.print(
            f"Precision {metrics['precision']:.3f} | "
            f"Recall {metrics['recall']:.3f} | "
            f"FP {metrics['fp']} | FN {metrics['fn']}"
        )
    except ValueError as exc:
        render_pending_template(report, labels)
        console.print(f"[yellow]{exc}[/yellow]")
        console.print(f"Template written to {report}")


if __name__ == "__main__":
    app()
