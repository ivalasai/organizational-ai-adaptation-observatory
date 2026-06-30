"""Configuration loading utilities for TOML and YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]


def load_config(path: Path | str) -> dict[str, Any]:
    """Load a configuration file from disk.

    Supports ``.toml``, ``.yaml``, and ``.yml`` extensions.

    Args:
        path: Path to the configuration file.

    Returns:
        Parsed configuration as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file extension is unsupported.
    """
    config_path = Path(path)
    if not config_path.exists():
        msg = f"Configuration file not found: {config_path}"
        raise FileNotFoundError(msg)

    suffix = config_path.suffix.lower()
    content = config_path.read_text(encoding="utf-8")

    if suffix == ".toml":
        return dict(tomllib.loads(content))
    if suffix in {".yaml", ".yml"}:
        loaded = yaml.safe_load(content)
        if not isinstance(loaded, dict):
            msg = f"Expected mapping at root of YAML file: {config_path}"
            raise ValueError(msg)
        return loaded

    msg = f"Unsupported configuration format: {suffix}"
    raise ValueError(msg)


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge two configuration dictionaries.

    Values in ``override`` take precedence over ``base``.

    Args:
        base: Base configuration.
        override: Override configuration.

    Returns:
        Merged configuration dictionary.
    """
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value
    return merged
