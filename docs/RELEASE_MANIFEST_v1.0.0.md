# Release Manifest: v1.0.0

## Release Identity

- Intended tag: `v1.0.0`
- Package version in `pyproject.toml`: `1.0.0`
- Installed package metadata version: `1.0.0`
- Release preparation branch: `release/v1.0.0`
- Release preparation phase: `Phase 13: prepare v1.0.0 release`
- Final tag target:
  - This file is committed before the annotated release tag is created.
  - The authoritative tag target must be resolved after tagging with:

```bash
git rev-parse v1.0.0^{}
git describe --tags --exact-match
```

* Expected release process:

  1. Merge the `release/v1.0.0` branch after CI passes.
  2. Clean-clone `main` and rerun the release gates.
  3. Create the annotated `v1.0.0` tag on the validated `main` commit.
  4. Clean-clone the `v1.0.0` tag and rerun the release gates.
  5. Publish the GitHub Release with this manifest and the v1.0.0 golden artifacts.

This manifest intentionally does not embed a self-referential final tag hash. The
Git tag object and GitHub Release metadata are the authoritative release anchors.

## Environment

For byte-identical reproduction of the checked-in v1.0.0 golden artifacts,
the release validation environment pins Python to `3.13.12`. Running the
evaluator on another compatible Python patch version may still be valid, but
`config.json` records the runtime Python version, so byte-level golden artifact
hashes are expected to differ.

The following environment was used for Phase 13 local release preparation.

* Python version: `3.13.12`
* SciPy version: `1.17.1`
* pytest version: `9.0.3`
* ruff version: `0.15.12`
* uv lock status: `uv lock --check` passed after updating `uv.lock` for
  `unified-eval==1.0.0`

Dependency versions captured with `uv run`:

* `unified-eval==1.0.0`
* `scipy==1.17.1`
* `pytest==9.0.3`
* `ruff==0.15.12`

External reproducibility does not depend on the author's local virtualenv path.
A fresh checkout must recreate the environment from `pyproject.toml` and `uv.lock`.

## Golden Artifact Hashes

Golden artifact directory:

```text
release_artifacts/v1.0.0/golden/
```

Protocol-level hashes:

* Schema hash:
  `sha256:5ee9c2e6c273bcc5eac765b2572bd230084ec1e0d0c551fe9ca2085c2eff0c9b`
* Split hash:
  `sha256:9582165e37f78826677a7f341d52e044c36b89062a5902cb5ab30bb8414d8df4`
* Strict normalizer config hash:
  `sha256:698f7ef6fc58c459f132c93e8ae337798558e1228a4e8f8d5f90f44d9c44e487`
* Matcher config hash:
  `sha256:83bf8563da60a0a98511b431b96eb5bcb3140be55e387d98254976193eb27abb`

File hashes use SHA-256 over file bytes.

| File                    | SHA-256                                                            |
| ----------------------- | ------------------------------------------------------------------ |
| `config.json`           | `3ef2953dce0b3d9f7c1236549278f02eb238e58b3b7bb991339c2bfb936bea71` |
| `duplicate_log.csv`     | `9ee3ec654a9a8e51af23a903a3707e71a7b5299904b1f15336f41d2317edbfba` |
| `error_cases.csv`       | `9610db02f29d781b2cf114b2d7def79498031f108f59d4f2f883561200e8e2f9` |
| `inputs/gold.jsonl`     | `9582165e37f78826677a7f341d52e044c36b89062a5902cb5ab30bb8414d8df4` |
| `inputs/pred.jsonl`     | `d35c91dd4936bcab6c5ab5407d24105fe994e3fd1d523ea47b7506829b07df4c` |
| `inputs/schema.json`    | `5ee9c2e6c273bcc5eac765b2572bd230084ec1e0d0c551fe9ca2085c2eff0c9b` |
| `invalid_cases.csv`     | `216afab377491b34ae5818bf4e9e5661ef08bbb6ff0ce1e884bc216197301a58` |
| `matching_log.csv`      | `d7d83b20e03be2b9d34521e86bafdcfbda018ae88a8c3de573b79616d414c10e` |
| `normalization_log.csv` | `38511242a10a51f9c9041b9919366c1af80ef2e94f0221898f26c2b028deb271` |
| `overall_metrics.json`  | `bce94101f8dc53fefd188f0da45edcef797e232b5fff3eb3246e07d5a6057143` |
| `unmatched_cases.csv`   | `5072024f6b38a47ffdd388cd91a53c241f3510974affacd05e892f3683723294` |

## Exact Commands Used

Version and dependency setup:

```bash
uv lock
uv sync
uv lock --check
uv run python - <<'PY'
import importlib.metadata
import platform

for pkg in ("unified-eval", "scipy", "pytest", "ruff"):
    print(f"{pkg}=={importlib.metadata.version(pkg)}")
print("python_version=" + platform.python_version())
PY
```

Golden artifact generation:

```bash
uv run python scripts/generate_release_golden.py \
  --output-dir release_artifacts/v1.0.0/golden
```

Release gates:

```bash
uv lock --check

uv run python scripts/generate_release_golden.py \
  --output-dir release_artifacts/v1.0.0/golden

git diff --exit-code -- release_artifacts/v1.0.0/golden

uv run pytest tests/test_release_artifacts.py
uv run pytest tests/protocol_v1 -k t24
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run pytest tests/protocol_v1
```

Boundary audits:

```bash
git diff -- docs/DEE\ Evaluation\ Protocol\ Final.md

git diff -- \
  src/unified_eval/matching.py \
  src/unified_eval/scoring.py \
  src/unified_eval/validation.py \
  src/unified_eval/normalization.py \
  src/unified_eval/schema.py

git diff --name-status
```

Author local data-boundary audit:

```bash
git -C /home/tjk/myProjects/masterProjects/DEE/data status --short
```

The path above is the author's local sibling data project used for the boundary
audit. It is not required for external release reproduction.

Forbidden-term scan over changed files:

```bash
rg -n \
  "semantic equivalence|embedding similarity|fuzzy matching|alias repair|schema guessing|role guessing|event-type guessing|gold repair|prediction repair|LLM judge" \
  $(git diff --name-only)
```

This scan is only a release-boundary audit. It does not replace the protocol-v1
test suite.

## Verification Results

Local Phase 13 verification results:

* `uv lock --check`: passed
* `uv run python scripts/generate_release_golden.py --output-dir release_artifacts/v1.0.0/golden`:
  generated v1 golden artifacts with `P=0.500000`, `R=0.333333`,
  `F1=0.400000`
* `git diff --exit-code -- release_artifacts/v1.0.0/golden`: passed after
  committing the deterministic v1 golden artifacts
* `uv run pytest tests/test_release_artifacts.py`: `4 passed`
* `uv run pytest tests/protocol_v1 -k t24`: `7 passed`
* `uv run ruff format --check .`: `64 files already formatted`
* `uv run ruff check .`: `All checks passed!`
* `uv run pytest`: `102 passed`
* `uv run pytest tests/protocol_v1`: `91 passed`

Boundary audit results:

* `docs/DEE Evaluation Protocol Final.md`: no diff
* Core evaluator behavior files `matching.py`, `scoring.py`, `validation.py`,
  `normalization.py`, and `schema.py`: no diff
* Sibling data project status: clean in the author local boundary audit
* Forbidden-term scan over changed files matched only README or documentation
  boundary prohibitions, not implementation code

## Clean-Clone Validation Commands

Clean clone from `main` after PR merge:

```bash
cd /tmp
rm -rf unified-eval-v1-main-rerun

git clone https://github.com/emmmdty/unified-eval.git unified-eval-v1-main-rerun
cd unified-eval-v1-main-rerun

uv sync --locked
uv lock --check

uv run --locked python scripts/generate_release_golden.py \
  --output-dir release_artifacts/v1.0.0/golden

git diff --exit-code -- release_artifacts/v1.0.0/golden

uv run --locked pytest tests/test_release_artifacts.py
uv run --locked pytest tests/protocol_v1 -k t24
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked pytest
uv run --locked pytest tests/protocol_v1
```

Clean clone from the final `v1.0.0` tag:

```bash
cd /tmp
rm -rf unified-eval-v1-tag-rerun

git clone --branch v1.0.0 https://github.com/emmmdty/unified-eval.git unified-eval-v1-tag-rerun
cd unified-eval-v1-tag-rerun

git rev-parse HEAD
git describe --tags --exact-match

uv sync --locked
uv lock --check

uv run --locked python scripts/generate_release_golden.py \
  --output-dir release_artifacts/v1.0.0/golden

git diff --exit-code -- release_artifacts/v1.0.0/golden

uv run --locked pytest tests/test_release_artifacts.py
uv run --locked pytest tests/protocol_v1 -k t24
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked pytest
uv run --locked pytest tests/protocol_v1
```

## CI Requirement

CI for the release branch, PR, `main`, and final release tag must run the same
release gates under Python `3.13.12`, because `config.json` records the runtime
Python version and the committed golden artifact hashes are byte-level hashes:

```bash
uv lock --check
uv sync --locked

uv run --locked python scripts/generate_release_golden.py \
  --output-dir release_artifacts/v1.0.0/golden

git diff --exit-code -- release_artifacts/v1.0.0/golden

uv run --locked pytest tests/test_release_artifacts.py
uv run --locked pytest tests/protocol_v1 -k t24
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked pytest
uv run --locked pytest tests/protocol_v1
```

## Release Assertions

* No evaluator matching, scoring, validation, normalization, or schema behavior
  was changed after `v0.9.0-rc1` except version, release, golden artifact,
  manifest, CI, and documentation updates.
* No evaluator behavior was changed after inspecting test outputs.
* Track A support is limited to official result schema, fixed-result ingestion,
  and unavailable blocks unless an external official runner output is explicitly
  provided.
* Track B Unified Strict Role-Value Micro-F1 must not be substituted for
  unavailable official metrics.
* Track A official metrics and Track B unified strict metrics remain separate.
* `docs/DEE Evaluation Protocol Final.md` was not modified by Phase 13.
* The sibling data project used by the author for local validation was not
  modified by Phase 13.
* External release reproduction must rely only on the Git repository, `uv.lock`,
  checked-in examples, checked-in golden artifacts, and the commands in this
  manifest.