# Development

```bash
uv sync --all-extras   # installs the lint/type/test extras too
```

```bash
uv run ruff check .   # lint, rules live in pyproject.toml
uv run ruff format .  # format
uv run ty check .     # type check
uv run pytest         # test
uv run coverage run && uv run coverage report   # coverage, config in pyproject.toml
```

See [CLAUDE.md](CLAUDE.md) for the module layout and non-obvious behaviour.
