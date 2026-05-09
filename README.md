# Unified Eval

`unified-eval` is a protocol-first repository for Chinese financial document-level event extraction evaluation over DuEE-Fin, ChFinAnn, and DocFEE.

The frozen authority is `docs/DEE Evaluation Protocol Final.md`. Implementations must follow that protocol exactly.

## v1.0.0 Status

This repository implements the frozen protocol-v1 Track B Unified Strict
Role-Value Micro-F1 evaluator. The implementation includes the canonical
prediction and gold JSONL contract layer, strict validation/accounting for
malformed prediction input, strict normalization within the frozen protocol's
allowed character rules, event-type-constrained Hungarian matching, unified
strict role-value micro scoring, and the machine-readable report artifact
layer.

Track A support is limited to official result schema, fixed-result ingestion
helpers, and explicit unavailable blocks. This v1.0.0 release does not
implement full ChFinAnn Doc2EDAG, DocFEE, or DuEE-Fin official evaluator
runner reproduction.

Implemented:

- uv-managed Python project metadata;
- an importable `unified_eval` package;
- canonical prediction JSONL parsing for `document_id` / `predictions`;
- canonical gold JSONL parsing for `document_id` / `gold_events`;
- schema registry metadata for dataset, split, legal event types, legal roles,
  schema hash, and split hash;
- strict rejection of legacy `doc_id` / `events` as main evaluator input;
- contract tests for invalid role value types without string coercion;
- prediction validation output structures for `valid_records_for_matching`,
  `invalid_cases`, illegal-event FP atoms, illegal-role FP atoms,
  invalid-value FP atoms, and duplicate value logs;
- validation coverage for frozen protocol T06-T10, T28, and T30 without invoking
  matching or scoring;
- strict normalization under `configs/strict_normalizer_v1.json`, covering
  Unicode NFKC, full-width ASCII conversion, whitespace trimming/collapse,
  listed Chinese punctuation mapping, thousands separators inside digit
  sequences, and zero-width/invisible control removal;
- normalization log row generation for `normalization_log.csv`;
- stable `normalization_config_hash` generation for the strict normalizer
  config;
- protocol-v1 normalization tests for T19-T22;
- frozen matching record representation as `role -> frozenset[str]`;
- grouping by `(dataset, split, document_id, event_type)`;
- `scipy.optimize.linear_sum_assignment` as the protocol-v1 Hungarian
  dependency, with clear failure when SciPy is unavailable;
- zero-score real pred-gold assignments converted to unmatched prediction plus
  unmatched gold;
- deterministic tie-breaking for total pair score, exact matched atoms,
  FP+FN, and lexicographic `(pred_idx, gold_idx)` pair lists;
- protocol-shaped `matching_log.csv` row generation and stable
  `matching_config_hash`;
- protocol-v1 matching tests for T16-T18 and T23;
- strict role-value TP/FP/FN scoring over schema roles for matched pairs;
- unmatched prediction FP and unmatched gold FN accounting;
- invalid-output FP atom integration for illegal event types, illegal roles,
  and invalid values;
- micro precision, recall, and F1 aggregation with no true-negative count;
- protocol-v1 scoring tests for T01-T05, T11-T15, and T25.
- required report artifact writing for `overall_metrics.json`,
  `matching_log.csv`, `unmatched_cases.csv`, `error_cases.csv`,
  `invalid_cases.csv`, `normalization_log.csv`, `duplicate_log.csv`, and
  `config.json`;
- stable CSV headers for every required log;
- `overall_metrics.json` with separated official, unified strict,
  auxiliary-normalized, and diagnostics sections;
- `config.json` with schema/split hashes, normalizer/matcher configs and
  hashes, Python/SciPy/dependency versions, commit hash, and mutation guard
  status;
- protocol-v1 report artifact tests for T26 and T27.
- `src/unified_eval/official_adapters/` with isolated Track A result-schema
  ingestion interfaces for DuEE-Fin, ChFinAnn Doc2EDAG, and DocFEE;
- a stable `official-metric-result-v1` schema for available and unavailable
  official adapter outputs in `overall_metrics.json`;
- explicit `available=false` official adapter results when an official runner
  or official score is not configured;
- fixed T24 official-result schema / fixture-ingestion samples for ChFinAnn,
  DocFEE, and DuEE-Fin offline official-style result loading;
- separate DuEE-Fin `online_official` and `offline_official_style` result
  types.
- a public `python -m unified_eval.protocol_v1` CLI with explicit dataset,
  split, schema, gold, prediction, and output-dir arguments;
- end-to-end CLI tests and smoke fixture support for copied local data
  snapshots.

Out of scope:

- full ChFinAnn Doc2EDAG, DocFEE, or DuEE-Fin official evaluator runner
  reproduction;
- auxiliary normalized scoring beyond the disabled report placeholder;
- dataset splitting or data preprocessing.

## Boundaries

- Do not modify `~/myProjects/masterProjects/DEE/data`.
- Do not copy large files into this repository.
- Do not implement LLM judge scoring, semantic matching, embedding similarity, alias repair, schema guessing, role guessing, event type guessing, gold repair, or prediction repair.
- Keep Track A official metrics and Track B unified strict metrics separate.
  They are not interchangeable: Track A adapters currently preserve official
  result schema / result ingestion / unavailable-block reporting only, while
  unified strict scoring is the cross-dataset scientific metric. Never use
  unified strict scores as a substitute for unavailable official metrics or as
  evidence that an official runner was reproduced.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
make check
```

## Protocol-v1 CLI

After creating the local data snapshot, run the public evaluator with explicit
paths:

```bash
uv run python -m unified_eval.protocol_v1 \
  --dataset ChFinAnn \
  --split dev \
  --schema data/processed/views/evaluator_gold/ChFinAnn/schema.json \
  --gold data/processed/views/evaluator_gold/ChFinAnn/dev.jsonl \
  --pred examples/predictions/chfinann_dev_toy.jsonl \
  --output-dir outputs/chfinann_dev_toy
```

The CLI does not infer the dataset or schema from paths, and it does not repair
prediction records. Outputs are the required protocol artifacts:
`overall_metrics.json`, `matching_log.csv`, `unmatched_cases.csv`,
`error_cases.csv`, `invalid_cases.csv`, `normalization_log.csv`,
`duplicate_log.csv`, and `config.json`.

## Data Snapshot

Create an isolated local snapshot from the sibling data project:

```bash
uv run python scripts/copy_data_snapshot.py \
  --source-root ~/myProjects/masterProjects/DEE/data \
  --target-root data
uv run python scripts/verify_data_snapshot.py --snapshot-root data
```

The generated `data/` tree is ignored by Git. The copy allowlist is limited to
schemas, split manifests, evaluator-gold files, samples, source hash/stat
manifests, and small official-adapter samples. It does not modify the source
directory and does not re-split or repair data.
