"""Firm-year panel assembly from feature tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from oaa_observatory.config.loader import load_config
from oaa_observatory.config.models import PanelBuilderConfig
from oaa_observatory.config.settings import Settings, get_settings
from oaa_observatory.utils.duckdb import get_connection, query_to_dataframe
from oaa_observatory.utils.io import write_parquet_atomic
from oaa_observatory.utils.logging import logger


class PanelBuilder:
    """Assemble firm-year panel from multiple feature tables.

    Joins attention, investment, and deployment feature tables on
    ``firm_id`` and ``year``. Outputs structured evidence only —
    no composite indices or latent constructs.
    """

    def __init__(
        self,
        config: PanelBuilderConfig | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize panel builder.

        Args:
            config: Panel assembly configuration.
            settings: Application settings.
        """
        self.config = config or PanelBuilderConfig()
        self.settings = settings or get_settings()
        self.settings.ensure_directories()

    @classmethod
    def from_config_file(cls, path: Path | str) -> PanelBuilder:
        """Create panel builder from a TOML configuration file.

        Args:
            path: Path to panel builder config.

        Returns:
            Configured PanelBuilder instance.
        """
        raw = load_config(path)
        panel_section = raw.get("panel", raw)
        config = PanelBuilderConfig.model_validate(panel_section)
        return cls(config=config)

    def _feature_path(self, table_name: str) -> Path:
        return self.settings.features_dir / table_name / "firm_year.parquet"

    def _load_feature_table(self, table_name: str, prefix: bool) -> pd.DataFrame | None:
        path = self._feature_path(table_name)
        if not path.exists():
            logger.warning("Feature table not found: {}", path)
            return None
        df = pd.read_parquet(path)
        if not prefix:
            return df
        join_keys = set(self.config.join_keys)
        rename_map = {
            col: f"{table_name.replace('/', '_')}_{col}"
            for col in df.columns
            if col not in join_keys and col != "source"
        }
        return df.rename(columns=rename_map)

    def build(self) -> pd.DataFrame:
        """Build the firm-year panel by joining feature tables.

        Returns:
            Assembled firm-year panel DataFrame.
        """
        logger.info(
            "Building firm-year panel from {} feature tables",
            len(self.config.feature_tables),
        )

        panel: pd.DataFrame | None = None
        for table_name in self.config.feature_tables:
            df = self._load_feature_table(table_name, prefix=panel is not None)
            if df is None or df.empty:
                continue

            if self.config.min_year:
                df = df[df["year"] >= self.config.min_year]
            if self.config.max_year:
                df = df[df["year"] <= self.config.max_year]

            if panel is None:
                panel = df
            else:
                panel = panel.merge(
                    df,
                    on=self.config.join_keys,
                    how="outer",
                )

        if panel is None:
            logger.warning("No feature tables available; returning empty panel")
            panel = pd.DataFrame(columns=["firm_id", "year"])

        return panel

    def build_with_duckdb(self) -> pd.DataFrame:
        """Build panel using DuckDB for larger-scale joins.

        Returns:
            Assembled firm-year panel DataFrame.
        """
        conn = get_connection()
        loaded_tables: list[str] = []

        for table_name in self.config.feature_tables:
            path = self._feature_path(table_name)
            if not path.exists():
                continue
            view_name = table_name.replace("/", "_").replace("-", "_")
            conn.execute(
                f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{path}')"
            )
            loaded_tables.append(view_name)

        if not loaded_tables:
            return pd.DataFrame(columns=["firm_id", "year"])

        base = loaded_tables[0]
        sql = f"SELECT * FROM {base}"
        for other in loaded_tables[1:]:
            sql += f" FULL OUTER JOIN {other} USING (firm_id, year)"

        if self.config.min_year:
            sql = f"SELECT * FROM ({sql}) WHERE year >= {self.config.min_year}"
        if self.config.max_year:
            sql = f"SELECT * FROM ({sql}) WHERE year <= {self.config.max_year}"

        return query_to_dataframe(conn, sql)

    def save(self, panel: pd.DataFrame, output_path: Path | None = None) -> Path:
        """Persist panel to configured output formats.

        Args:
            panel: Firm-year panel DataFrame.
            output_path: Override output path.

        Returns:
            Primary output path.
        """
        path = output_path or self.config.output_path
        path.parent.mkdir(parents=True, exist_ok=True)

        primary = write_parquet_atomic(panel, path)
        logger.info("Wrote panel with {} rows to {}", len(panel), primary)

        for fmt in self.config.export_formats:
            if fmt == "csv":
                csv_path = path.with_suffix(".csv")
                panel.to_csv(csv_path, index=False)
                logger.info("Exported CSV to {}", csv_path)
            elif fmt == "duckdb":
                db_path = path.with_suffix(".duckdb")
                conn = get_connection(db_path)
                conn.register("panel", panel)
                conn.execute("CREATE OR REPLACE TABLE firm_year_panel AS SELECT * FROM panel")
                conn.close()
                logger.info("Exported DuckDB to {}", db_path)

        return primary

    def run(self) -> Path:
        """Build and save the firm-year panel.

        Returns:
            Path to primary output file.
        """
        panel = self.build()
        return self.save(panel)
