"""Tests for configuration loading."""

from pathlib import Path

from oaa_observatory.config.loader import load_config, merge_configs
from oaa_observatory.config.models import SECConfig


class TestConfigLoader:
    """Configuration loader test cases."""

    def test_load_toml(self) -> None:
        config = load_config(Path("configs/datasources/sec.toml"))
        assert config["name"] == "sec_filings"
        assert config["signal_layer"] == "attention"

    def test_merge_configs(self) -> None:
        base = {"a": 1, "b": {"c": 2}}
        override = {"b": {"d": 3}}
        merged = merge_configs(base, override)
        assert merged == {"a": 1, "b": {"c": 2, "d": 3}}

    def test_sec_config_model(self) -> None:
        raw = load_config(Path("configs/datasources/sec.toml"))
        config = SECConfig.model_validate(raw)
        assert config.signal_layer == "attention"
        assert config.filing_types == ["10-K", "10-Q"]
        assert config.start_year == 2015
