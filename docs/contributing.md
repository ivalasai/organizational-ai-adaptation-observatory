# Contributing

Thank you for contributing to the Organizational AI Adaptation Observatory.

## Development Setup

```bash
git clone https://github.com/organizational-ai-adaptation/organizational-ai-adaptation-observatory.git
cd organizational-ai-adaptation-observatory

# Install with uv
uv sync --all-extras
uv run pre-commit install
```

## Code Standards

- Python 3.12+
- All public functions typed (mypy strict)
- Google-style docstrings
- Ruff for linting and formatting
- pytest for testing

```bash
make lint      # ruff check
make format    # ruff format
make typecheck # mypy
make test      # pytest
```

## Adding a Data Source

1. **Config** — Add `configs/datasources/your_source.toml`
2. **Pipeline** — Create `src/oaa_observatory/your_source/pipeline.py` subclassing `BasePipeline`
3. **Tests** — Add tests in `tests/`
4. **CLI** — Register in `cli.py` pipeline_map
5. **Panel** — Add feature table path to `configs/pipeline/panel_builder.toml`
6. **Docs** — Update README data sources table

## What NOT to Contribute

- Composite indices or scores (AI Adaptation Index, readiness scores, etc.)
- Sentiment models or hype classifiers (unless as optional, clearly separated modules)
- Econometric analysis or regression examples
- Paper-specific hypotheses or constructs
- Governance signals (CAO appointments, board committees, etc.)

## Pull Request Checklist

- [ ] Tests pass (`make test`)
- [ ] Types check (`make typecheck`)
- [ ] Lint passes (`make lint`)
- [ ] Docstrings on all public functions
- [ ] Config files for any new data sources
- [ ] No hardcoded paths or credentials
- [ ] No composite constructs introduced

## Commit Messages

Use conventional prefixes:

- `feat:` new data source or capability
- `fix:` bug fix
- `docs:` documentation only
- `refactor:` code restructuring
- `test:` test additions
- `chore:` tooling, CI, dependencies
