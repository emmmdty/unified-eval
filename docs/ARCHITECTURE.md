# Architecture

This repository is dedicated to unified evaluation. It does not own dataset preprocessing, dataset splitting, model inference, or prediction repair.

## Authority And Data Boundaries

- `docs/DEE Evaluation Protocol Final.md` is the frozen evaluator specification.
- `~/myProjects/masterProjects/DEE/data` is the source project for existing data artifacts and must not be modified from this repository.
- Later phases may copy only necessary, small, approved artifacts into this repository.
- Track A dataset-official metrics and Track B unified strict metrics must remain separate.

## Current Layout

- `src/unified_eval/`: importable Python package scaffold.
- `src/unified_eval/contracts.py`: immutable canonical document, record, and
  validation issue contracts.
- `src/unified_eval/schema.py`: frozen schema registry metadata.
- `src/unified_eval/io.py`: canonical prediction/gold JSONL readers.
- `src/unified_eval/validation.py`: tolerant prediction validation and
  invalid-output accounting for protocol Section 6.
- `src/unified_eval/normalization.py`: strict unified-metric normalization and
  normalization config hashing for protocol Section 9.1.
- `src/unified_eval/matching.py`: frozen event-type-constrained Hungarian
  matching and `matching_log.csv` row generation for protocol Section 7.
- `src/unified_eval/scoring.py`: final unified strict role-value TP/FP/FN and
  micro P/R/F1 scoring for protocol Sections 3.5, 3.6, and 8.
- `src/unified_eval/reporting.py`: required protocol-v1 report artifact writer
  for overall metrics, logs, config metadata, dependency versions, commit hash,
  and config mutation guard outputs.
- `configs/strict_normalizer_v1.json`: frozen strict normalizer v1 config.
- `tests/`: smoke tests, snapshot tests, and protocol-v1 contract tests.
- `scripts/`: future thin command-line wrappers.
- `docs/`: frozen protocol, architecture notes, and compliance planning.

No Track A official adapter behavior or auxiliary normalized scoring is
implemented yet.

## Isolated Data Snapshot

`scripts/copy_data_snapshot.py` copies a protocol-scoped allowlist from
`~/myProjects/masterProjects/DEE/data` into local `data/`. The allowlist includes
schemas, split manifests, evaluator-gold files, source hash/stat manifests,
samples, and small official-adapter samples.

`scripts/verify_data_snapshot.py` verifies the generated snapshot manifest with
SHA-256 hashes. The snapshot is a local artifact ignored by Git; it must not use
symlinks, mutate the source project, re-split datasets, repair gold data, or edit
schemas.

## Planned Modules

### Canonical I/O

Implemented code parses canonical JSONL prediction and gold files, one document
per line. It preserves invalid raw values in validation issues and avoids
coercive repair.

### Dataset Adapters

The schema registry exposes dataset, split, schema hash, split hash, legal event
types, and legal roles. Future dataset adapters must not create new splits or
guess schema fields.

### Validation

Validation implements the Phase 3 slice of protocol Section 6 for prediction
JSONL. Invalid JSON, malformed documents, malformed records, illegal event
types, illegal roles, invalid values, empty values, duplicate role values,
unknown document IDs, and split mismatches are counted and logged. It emits
valid records for future matching plus invalid-case and FP-atom side channels;
it does not run matching, scoring, or normalization.

### Strict Normalization

Strict normalization implements only protocol Section 9.1. It emits
CSV-serializable normalization log rows and a stable
`normalization_config_hash` for `configs/strict_normalizer_v1.json`.
Auxiliary-only normalization belongs in a separate path and must never change
Track B unified strict metrics.

### Matching

Matching implements deterministic event-type-constrained Hungarian alignment by
`(dataset, split, document_id, event_type)`. It preserves duplicate records,
uses `scipy.optimize.linear_sum_assignment`, treats zero-score real assignments
as unmatched, emits protocol-shaped matching log rows, and records a stable
matcher config hash. Cross-event-type rescue is forbidden.

### Scoring

Scoring computes role-value-level TP, FP, FN, precision, recall, and micro-F1
exactly as defined by the protocol. It counts matched pairs over schema roles,
unmatched predictions as FP, unmatched gold records as FN, and invalid-output FP
atoms from prediction validation. True negatives are never counted.

### Track A Official Adapters

Official adapters should preserve dataset-official behavior for comparability. They must not replace Track B and must record evaluator version, command, and commit hash where applicable.

### Reports And Logs

Report generation should write the required machine-readable outputs: `overall_metrics.json`, `matching_log.csv`, `unmatched_cases.csv`, `error_cases.csv`, `invalid_cases.csv`, `normalization_log.csv`, `duplicate_log.csv`, and `config.json`.
Phase 7 implements this artifact layer with stable CSV headers, separate Track A
official and Track B unified strict metric blocks, disabled auxiliary-normalized
placeholders, and reproducibility metadata including Python/SciPy/dependency
versions and commit hash.

### Tests

The required T01-T30 suite in the frozen protocol is the acceptance target for
evaluator freeze. Phase 2 adds protocol-v1 contract tests for canonical
prediction/gold parsing, legacy-shape rejection, schema registry metadata, and
invalid value-type diagnostics.

Phase 3 adds protocol-v1 validation tests for T06-T10, T28, and T30.

Phase 4 adds protocol-v1 strict normalization tests for T19-T22. Phase 5 adds
protocol-v1 matching tests for T16-T18 and T23. Phase 6 adds protocol-v1
scoring tests for T01-T05, T11-T15, and T25. Phase 7 adds report artifact
tests for T26 and T27.
