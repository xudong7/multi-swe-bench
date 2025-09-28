# Local Setup Instructions

```bash
uv init && uv sync
```

```bash
uv pip install -e .
uv add dataclasses-json docker tqdm gitpython toml pyyaml PyGithub unidiff swe-rex
```

```bash
uv run download.py
```

```bash
uv run python -m multi_swe_bench.harness.run_evaluation --config config.json
```