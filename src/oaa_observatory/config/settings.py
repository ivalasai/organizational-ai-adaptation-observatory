"""Application settings loaded from environment variables and config files."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the observatory.

    Credentials and path overrides are loaded from environment variables.
    Pipeline behavior is configured via TOML/YAML files in ``configs/``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="OAA_",
        extra="ignore",
    )

    data_root: Path = Field(default=Path("data"), description="Root directory for all data stages")
    output_root: Path = Field(
        default=Path("output"),
        description="Directory for exports and reports",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_file: Path | None = Field(default=None, description="Optional log file path")

    # External credentials (never hardcoded)
    wrds_username: str | None = None
    wrds_password: str | None = None
    sec_user_agent: str = "OAA Observatory research@example.com"

    @property
    def raw_dir(self) -> Path:
        """Path to immutable raw data."""
        return self.data_root / "raw"

    @property
    def intermediate_dir(self) -> Path:
        """Path to standardized intermediate tables."""
        return self.data_root / "intermediate"

    @property
    def features_dir(self) -> Path:
        """Path to firm-year feature tables."""
        return self.data_root / "features"

    @property
    def panel_dir(self) -> Path:
        """Path to assembled firm-year panels."""
        return self.data_root / "panel"

    @property
    def exports_dir(self) -> Path:
        """Path to researcher-facing exports."""
        return self.data_root / "exports"

    def ensure_directories(self) -> None:
        """Create standard data directories if they do not exist."""
        for directory in (
            self.raw_dir,
            self.intermediate_dir,
            self.features_dir,
            self.panel_dir,
            self.exports_dir,
            self.output_root,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Return application settings singleton."""
    return Settings()
