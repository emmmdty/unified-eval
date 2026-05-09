# Release Manifest: v1.0.0

## Release Identity

- Intended tag: `v1.0.0`
- Package version in `pyproject.toml`: `1.0.0`
- Installed package metadata version: `1.0.0`
- Current source commit before Phase 13 tagging:
  `b5c0775d240447ae74bce12a42d801a1e9b2578b`
- Current source commit message before Phase 13 tagging:
  `Phase 12: prepare v0.9.0-rc1 release candidate`
- Final tag commit cannot be embedded in this file before the release commit
  exists. After tagging, resolve it with:
  `git rev-parse v1.0.0^{}`
- No tag was created by Phase 13.

## Environment

- Python version: `3.13.12`
- Python executable:
  `/home/tjk/myProjects/masterProjects/DEE/unified-eval/.venv/bin/python3`
- SciPy version: `1.17.1`
- pytest version: `9.0.3`
- ruff version: `0.15.12`
- uv lock status: `uv lock --check` passed after updating `uv.lock` for
  `unified-eval==1.0.0`

Dependency versions captured with `uv run`:

- `unified-eval==1.0.0`
- `scipy==1.17.1`
- `pytest==9.0.3`
- `ruff==0.15.12`

## Golden Artifact Hashes

Golden artifact directory:
`release_artifacts/v1.0.0/golden/`

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
| `config.json` | `3ef2953dce0b3d9f7c1236549278f02eb238e58b3b7bb991339c2bfb936bea71` |
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
for pkg in ("unified-eval", "scipy", "pytest", "ruff"):
    print(f"{pkg}=={importlib.metadata.version(pkg)}")
print("python_version=" + platform.python_version())
print("python_executable=" + sys.executable)
PY
```

Golden artifact generation:

```bash
uv run python scripts/generate_release_golden.py --output-dir release_artifacts/v1.0.0/golden
```

Release gates:

```bash
uv lock --check
uv run python scripts/generate_release_golden.py --output-dir release_artifacts/v1.0.0/golden
uv run pytest tests/test_release_artifacts.py
uv run pytest tests/protocol_v1/test_t24*.py
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run pytest tests/protocol_v1
```

Boundary audits:

```bash
git diff -- docs/DEE\ Evaluation\ Protocol\ Final.md
git diff -- src/unified_eval/matching.py src/unified_eval/scoring.py src/unified_eval/validation.py src/unified_eval/normalization.py src/unified_eval/schema.py
git diff --name-status
git -C /home/tjk/myProjects/masterProjects/DEE/data status --short
rg -n "semantic equivalence|embedding similarity|fuzzy matching|alias repair|schema guessing|role guessing|event-type guessing|gold repair|prediction repair|LLM judge" $(git diff --name-only)
```

Verification results:

- `uv lock --check`: passed
- `uv run python scripts/generate_release_golden.py --output-dir release_artifacts/v1.0.0/golden`:
  generated v1 golden artifacts with `P=0.500000`, `R=0.333333`,
  `F1=0.400000`
- `uv run pytest tests/test_release_artifacts.py`: `4 passed`
- `uv run pytest tests/protocol_v1/test_t24*.py`: `7 passed`
- `uv run ruff format --check .`: `64 files already formatted`
- `uv run ruff check .`: `All checks passed!`
- `uv run pytest`: `102 passed`
- `uv run pytest tests/protocol_v1`: `91 passed`

Boundary audit results:

- `docs/DEE Evaluation Protocol Final.md`: no diff
- Core evaluator behavior files `matching.py`, `scoring.py`, `validation.py`,
  `normalization.py`, and `schema.py`: no diff
- Sibling data project status: clean
- Forbidden-term scan over changed files matched only README boundary
  prohibitions, not implementation code.

Clean clone validation commands:

```bash
git clone <repo-url> unified-eval-v1.0.0-check
cd unified-eval-v1.0.0-check
git checkout v1.0.0
uv sync
uv lock --check
uv run python scripts/generate_release_golden.py --output-dir release_artifacts/v1.0.0/golden
uv run pytest tests/test_release_artifacts.py
uv run pytest tests/protocol_v1/test_t24*.py
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

## CI Requirement

CI for the release tag must run the same release gates listed above, including
`uv lock --check`, v1 golden artifact regeneration, release artifact tests,
T24 Track A boundary tests, ruff format check, ruff lint, and the full pytest
suite.

## Release Assertions

- No evaluator matching, scoring, validation, normalization, or schema behavior
  was changed after v0.9.0-rc1 except version/release/golden/manifest/documentation
  updates.
- No evaluator behavior was changed after inspecting test outputs.
- Track A support is limited to official result schema, fixed-result ingestion,
  and unavailable blocks unless an external official runner output is explicitly
  provided.
- Track B Unified Strict Role-Value Micro-F1 must not be substituted for
  unavailable official metrics.
- Track A official metrics and Track B unified strict metrics remain separate.
- `docs/DEE Evaluation Protocol Final.md` was not modified by Phase 13.
- The sibling data project at `/home/tjk/myProjects/masterProjects/DEE/data`
  was not modified by Phase 13.
