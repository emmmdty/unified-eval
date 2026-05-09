# Release Manifest: v0.9.0-rc1

## Release Identity

- Intended tag: `v0.9.0-rc1`
- Manifest generation commit: `10984f6eb55de27601a307c54b6d4bfc57466596`
- Manifest generation commit message: `Phase 11: produce final freeze report`
- Phase 12 commit hash: reported after commit creation
- Package version in `pyproject.toml`: `0.9.0-rc1`
- Installed package metadata version: `0.9.0rc1`

## Environment

- Python version: `3.13.12`
- Python executable:
  `/home/tjk/myProjects/masterProjects/DEE/unified-eval/.venv/bin/python3`
- SciPy version: `1.17.1`
- uv lock status: `uv lock --check` passed after updating `uv.lock` for
  `unified-eval==0.9.0rc1`

Dependency versions captured with `uv run`:

- `unified-eval==0.9.0rc1`
- `scipy==1.17.1`
- `pytest==9.0.3`
- `ruff==0.15.12`

## Golden Artifact Hashes

Golden artifact directory:
`release_artifacts/v0.9.0-rc1/golden/`

- Schema hash:
  `sha256:5ee9c2e6c273bcc5eac765b2572bd230084ec1e0d0c551fe9ca2085c2eff0c9b`
- Split hash:
  `sha256:9582165e37f78826677a7f341d52e044c36b89062a5902cb5ab30bb8414d8df4`
- Strict normalizer config hash:
  `sha256:698f7ef6fc58c459f132c93e8ae337798558e1228a4e8f8d5f90f44d9c44e487`
- Matcher config hash:
  `sha256:83bf8563da60a0a98511b431b96eb5bcb3140be55e387d98254976193eb27abb`

File hashes use SHA-256 over file bytes:

| File | SHA-256 |
| --- | --- |
| `config.json` | `d12c3519b5615790c5c277968e4536dbd40885f5fde41cd86eaba262b5d848b8` |
| `duplicate_log.csv` | `9ee3ec654a9a8e51af23a903a3707e71a7b5299904b1f15336f41d2317edbfba` |
| `error_cases.csv` | `9610db02f29d781b2cf114b2d7def79498031f108f59d4f2f883561200e8e2f9` |
| `inputs/gold.jsonl` | `9582165e37f78826677a7f341d52e044c36b89062a5902cb5ab30bb8414d8df4` |
| `inputs/pred.jsonl` | `d35c91dd4936bcab6c5ab5407d24105fe994e3fd1d523ea47b7506829b07df4c` |
| `inputs/schema.json` | `5ee9c2e6c273bcc5eac765b2572bd230084ec1e0d0c551fe9ca2085c2eff0c9b` |
| `invalid_cases.csv` | `216afab377491b34ae5818bf4e9e5661ef08bbb6ff0ce1e884bc216197301a58` |
| `matching_log.csv` | `d7d83b20e03be2b9d34521e86bafdcfbda018ae88a8c3de573b79616d414c10e` |
| `normalization_log.csv` | `38511242a10a51f9c9041b9919366c1af80ef2e94f0221898f26c2b028deb271` |
| `overall_metrics.json` | `bce94101f8dc53fefd188f0da45edcef797e232b5fff3eb3246e07d5a6057143` |
| `unmatched_cases.csv` | `5072024f6b38a47ffdd388cd91a53c241f3510974affacd05e892f3683723294` |

## Exact Commands Used

Version and dependency setup:

```bash
uv lock
uv sync
uv lock --check
uv run python - <<'PY'
import importlib.metadata, platform, sys
for pkg in ('unified-eval', 'scipy', 'pytest', 'ruff'):
    try:
        version = importlib.metadata.version(pkg)
    except importlib.metadata.PackageNotFoundError:
        version = 'not-installed'
    print(f'{pkg}=={version}')
print('python_version=' + platform.python_version())
print('python_executable=' + sys.executable)
PY
```

Golden artifact generation:

```bash
uv run python scripts/generate_release_golden.py --output-dir release_artifacts/v0.9.0-rc1/golden
```

Release gates:

```bash
uv sync
uv lock --check
uv run python scripts/generate_release_golden.py --output-dir release_artifacts/v0.9.0-rc1/golden
uv run pytest tests/test_release_artifacts.py
uv run pytest tests/protocol_v1/test_t24*.py
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

Boundary audits:

```bash
git diff --name-only
git diff -- src/unified_eval/matching.py src/unified_eval/scoring.py src/unified_eval/validation.py src/unified_eval/normalization.py src/unified_eval/schema.py
git -C /home/tjk/myProjects/masterProjects/DEE/data status --short
```

Verification results:

- `uv run pytest tests/test_release_artifacts.py`: `2 passed`
- `uv run pytest tests/protocol_v1/test_t24*.py`: `7 passed`
- `uv run ruff format --check .`: `64 files already formatted`
- `uv run ruff check .`: `All checks passed!`
- `uv run pytest`: `100 passed`

## Release Assertions

- No evaluator matching, scoring, validation, normalization, or schema behavior
  was changed for this release candidate.
- No evaluator behavior was changed after inspecting test outputs.
- Track A support in this release candidate is limited to official result
  schema, fixed-result ingestion, and unavailable blocks. It is not a complete
  official evaluator runner reproduction.
- Track B Unified Strict Role-Value Micro-F1 must not be substituted for
  unavailable official metrics.
- No tag was created.
