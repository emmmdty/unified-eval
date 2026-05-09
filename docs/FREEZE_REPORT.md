# Phase 11 Freeze Report

## Scope

Final freeze regression was run on the copied local data snapshot for
DuEE-Fin, ChFinAnn, and DocFEE. No evaluator behavior, normalizer, schema, or
split file was changed for this freeze. The only checked-in non-reporting
addition is `scripts/run_all_checks.sh`, a wrapper for the already documented
format, lint, and test gates.

## Commit

- Evaluated evaluator source commit: `47a6fe114716b3961d47c31f5ec0965204464a71`
- Evaluated evaluator source commit message: `Phase 10: implement protocol-v1 CLI`
- Final report commit message: `Phase 11: produce final freeze report`
- Note: the final report commit hash cannot be embedded in this file without
  changing the commit hash itself. Report the final commit hash after creating
  the commit.

## Environment

- Python version: `3.13.12`
- Python executable:
  `/home/tjk/myProjects/masterProjects/DEE/unified-eval/.venv/bin/python3`
- SciPy version: `1.17.1`
- Dependency versions:
  - `unified-eval==0.0.0` for the Phase 11 run before release hardening
  - `scipy==1.17.1`
  - `pytest==9.0.3`
  - `ruff==0.15.12`
- Phase 12 release hardening updates package metadata to `0.9.0-rc1`
  (`0.9.0rc1` in installed package metadata) and records that version in the
  v0.9.0-rc1 release manifest and golden `config.json`.
- Phase 13 v1.0.0 release hardening promotes the v0.9.0-rc1 release candidate
  to the frozen protocol-v1 evaluator release. It updates package/release
  metadata, documentation, v1 golden artifacts, and the v1 release manifest
  without changing evaluator matching, scoring, validation, normalization, or
  schema behavior.

## Track A Official Adapter Scope

Track A support in this repository is limited to the stable
`official-metric-result-v1` schema, fixed official-result fixture ingestion,
and explicit `available=false` unavailable blocks. It is not a complete
offline reproduction of the ChFinAnn Doc2EDAG, DocFEE, or DuEE-Fin official
evaluator runners.

Track A official metrics and Track B Unified Strict Role-Value Micro-F1 remain
separate. Unified strict scores are the cross-dataset scientific metric, but
they must not be reported as substitutes for unavailable official metrics.

## Frozen Hashes

Shared configuration hashes:

- Normalizer config file hash:
  `b75a8e36df19d86b11459d5b4f15d1aaa54dbeca252c190a215790aecf8c962b`
- Normalizer config protocol hash:
  `sha256:698f7ef6fc58c459f132c93e8ae337798558e1228a4e8f8d5f90f44d9c44e487`
- Matcher config protocol hash:
  `sha256:83bf8563da60a0a98511b431b96eb5bcb3140be55e387d98254976193eb27abb`

Dataset hashes used by the copied-snapshot regression:

| Dataset | CLI dataset | Split | Schema hash | Split hash |
| --- | --- | --- | --- | --- |
| `DuEE-Fin-dev500` | `DuEE-Fin` | `dev` | `sha256:17474f0973b358ae9d3eebe02dedc1c722795f474c266347c1d6c0b8784227f4` | `sha256:68d32b699c09831af71b7890e5324aaac88ec89012eee9fc7380a7535b6f22ea` |
| `ChFinAnn` | `ChFinAnn` | `dev` | `sha256:fbd730fd1daa96fe6cc12a4bcda12d580895459d70730c234acc8fbf9d87b856` | `sha256:65fcf1dea311b4e476926dda980ae42e362c025e0d29f74d8017304a719163dd` |
| `DocFEE-dev1000` | `DocFEE` | `dev` | `sha256:20e28e688bf8a9e8ed4461af8817fcc5ec230a457e0dcbf5546d4d78c2a43078` | `sha256:4c5730257ca0b52dd8d3cad3b0981964cf356e9ca14b286e2acb471b37905340` |

Source split-manifest file hashes, recorded separately from the evaluator dev
JSONL split hash above:

- `data/processed/DuEE-Fin-dev500/split_manifest.json`:
  `1310bc5dfd8d9c689cb0795281fa8c2b906c1ee96c1752b63e12ae9de0e71d27`
- `data/processed/ChFinAnn/split_manifest.json`:
  `d9aed916e8abcd274c47c93cd7a5df5eb017b40e49fe76009e1402e55df7d557`
- `data/processed/DocFEE-dev1000/split_manifest.json`:
  `c2699948a9cc78dce70bd1679f9aa3991c6bbf1dccc9e4e1ba39af90f97ff766`

## Data Snapshot Manifest

- Manifest path: `data/snapshot_manifest.json`
- Manifest file hash:
  `0abb8e1bf0579216d3bfc54452f558182b371a01707fde06ce128500812a5056`
- Manifest schema version: `unified-eval-data-snapshot-v1`
- Created at UTC: `2026-05-08T12:48:05+00:00`
- Source root: `/home/tjk/myProjects/masterProjects/DEE/data`
- Snapshot root: `/home/tjk/myProjects/masterProjects/DEE/unified-eval/data`
- Hash method: `sha256`
- Datasets:
  - `DuEE-Fin-dev500`
  - `ChFinAnn`
  - `DocFEE-dev1000`
- Manifest file count: `61`
- Verification result: `ok=true`, `checked_files=61`
- Snapshot notes:
  - No train/dev/test split membership is changed.
  - Gold files and schemas are copied byte-for-byte without repair.
  - Raw large train/dev/test files are not part of this allowlist.

## Exact Commands

Snapshot verification:

```bash
uv run python scripts/verify_data_snapshot.py --snapshot-root data
```

Dependency/version capture:

```bash
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

Copied-snapshot gold-as-pred input generation:

```bash
rm -rf outputs/phase11_freeze/smoke_inputs \
  outputs/phase11_freeze/runs/duee_fin_dev_gold_as_pred \
  outputs/phase11_freeze/runs/chfinann_dev_gold_as_pred \
  outputs/phase11_freeze/runs/docfee_dev_gold_as_pred
mkdir -p outputs/phase11_freeze/smoke_inputs outputs/phase11_freeze/runs
uv run python - <<'PY'
import json
from pathlib import Path

root = Path('data/processed/views/evaluator_gold')
out = Path('outputs/phase11_freeze/smoke_inputs')
out.mkdir(parents=True, exist_ok=True)
for dataset in ('DuEE-Fin-dev500', 'ChFinAnn', 'DocFEE-dev1000'):
    src = root / dataset / 'dev.jsonl'
    dst = out / f'{dataset}_dev_gold_as_pred.jsonl'
    with src.open(encoding='utf-8') as handle, dst.open('w', encoding='utf-8') as writer:
        for line in handle:
            row = json.loads(line)
            predictions = []
            for event in row.get('events', []):
                arguments = {}
                for role, values in event.get('arguments', {}).items():
                    converted = []
                    for value in values:
                        if isinstance(value, dict):
                            converted.append(value.get('text'))
                        else:
                            converted.append(value)
                    converted = [value for value in converted if isinstance(value, str)]
                    if converted:
                        arguments[role] = converted if len(converted) > 1 else converted[0]
                predictions.append({'event_type': event['event_type'], 'arguments': arguments})
            writer.write(json.dumps({'document_id': row['doc_id'], 'predictions': predictions}, ensure_ascii=False) + '\n')
    print(dst)
PY
```

Copied-snapshot smoke/regression commands:

```bash
uv run python -m unified_eval.protocol_v1 \
  --dataset DuEE-Fin \
  --split dev \
  --schema data/processed/views/evaluator_gold/DuEE-Fin-dev500/schema.json \
  --gold data/processed/views/evaluator_gold/DuEE-Fin-dev500/dev.jsonl \
  --pred outputs/phase11_freeze/smoke_inputs/DuEE-Fin-dev500_dev_gold_as_pred.jsonl \
  --output-dir outputs/phase11_freeze/runs/duee_fin_dev_gold_as_pred

uv run python -m unified_eval.protocol_v1 \
  --dataset ChFinAnn \
  --split dev \
  --schema data/processed/views/evaluator_gold/ChFinAnn/schema.json \
  --gold data/processed/views/evaluator_gold/ChFinAnn/dev.jsonl \
  --pred outputs/phase11_freeze/smoke_inputs/ChFinAnn_dev_gold_as_pred.jsonl \
  --output-dir outputs/phase11_freeze/runs/chfinann_dev_gold_as_pred

uv run python -m unified_eval.protocol_v1 \
  --dataset DocFEE \
  --split dev \
  --schema data/processed/views/evaluator_gold/DocFEE-dev1000/schema.json \
  --gold data/processed/views/evaluator_gold/DocFEE-dev1000/dev.jsonl \
  --pred outputs/phase11_freeze/smoke_inputs/DocFEE-dev1000_dev_gold_as_pred.jsonl \
  --output-dir outputs/phase11_freeze/runs/docfee_dev_gold_as_pred
```

Toy smoke command:

```bash
uv run python -m unified_eval.protocol_v1 \
  --dataset ChFinAnn \
  --split dev \
  --schema data/processed/views/evaluator_gold/ChFinAnn/schema.json \
  --gold data/processed/views/evaluator_gold/ChFinAnn/dev.jsonl \
  --pred examples/predictions/chfinann_dev_toy.jsonl \
  --output-dir outputs/phase11_freeze/runs/chfinann_dev_toy
```

Acceptance gates:

```bash
uv run pytest tests/protocol_v1/test_t*.py
scripts/run_all_checks.sh
```

## Regression Results

Every run wrote the full protocol-v1 artifact set:
`overall_metrics.json`, `matching_log.csv`, `unmatched_cases.csv`,
`error_cases.csv`, `invalid_cases.csv`, `normalization_log.csv`,
`duplicate_log.csv`, and `config.json`.

| Run | Dataset | Split | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `outputs/phase11_freeze/runs/duee_fin_dev_gold_as_pred` | DuEE-Fin | dev | 3435 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| `outputs/phase11_freeze/runs/chfinann_dev_gold_as_pred` | ChFinAnn | dev | 30588 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| `outputs/phase11_freeze/runs/docfee_dev_gold_as_pred` | DocFEE | dev | 5950 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| `outputs/phase11_freeze/runs/chfinann_dev_toy` | ChFinAnn | dev | 13 | 1 | 30575 | 0.9285714285714286 | 0.00042500326925591734 | 0.0008496176720475786 |

The three copied-snapshot self-evaluation smokes have no invalid rows and no
error rows beyond CSV headers.

## Acceptance Evidence

- `uv run pytest tests/protocol_v1/test_t*.py`: `68 passed in 0.60s`.
- `scripts/run_all_checks.sh`: ruff format check passed, ruff lint passed, and
  `98 passed in 1.55s`.
- Toy smoke passed:
  `outputs/phase11_freeze/runs/chfinann_dev_toy`.
- Copied snapshot smokes passed:
  - `outputs/phase11_freeze/runs/duee_fin_dev_gold_as_pred`
  - `outputs/phase11_freeze/runs/chfinann_dev_gold_as_pred`
  - `outputs/phase11_freeze/runs/docfee_dev_gold_as_pred`
- Data snapshot verification passed:
  `ok=true`, `checked_files=61`.

## Issue Log

- Initial local smoke input generation copied `event_id` from gold events into
  prediction records. DuEE-Fin and DocFEE gold event IDs are not always strings,
  so prediction validation correctly logged `invalid_event_id_type`. This was a
  smoke-input construction issue. It was recorded here and rerun with valid
  prediction records that omit `event_id`; no evaluator, normalizer, schema, or
  split behavior was changed after inspecting the result.

## Freeze Decision

Freeze report complete. The copied data snapshot is verified, T01-T30 pass, the
full local check wrapper passes, one toy smoke passes, and copied-snapshot
smokes pass for DuEE-Fin, ChFinAnn, and DocFEE. No evaluator behavior,
normalizer, schema, or split mutation was made for Phase 11.
