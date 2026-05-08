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
- `tests/`: smoke tests, snapshot tests, and protocol-v1 contract tests.
- `scripts/`: future thin command-line wrappers.
- `docs/`: frozen protocol, architecture notes, and compliance planning.

No matching, scoring, normalization, or Track A official adapter behavior is
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

Validation should implement protocol Section 6. Invalid JSON, malformed records, illegal event types, illegal roles, invalid values, empty values, and duplicate values must be counted and logged.

### Strict Normalization

Strict normalization should implement only protocol Section 9.1. Auxiliary-only normalization belongs in a separate path and must never change Track B unified strict metrics.

### Matching

Matching should implement deterministic event-type-constrained Hungarian alignment by `(dataset, split, document_id, event_type)`. Cross-event-type rescue is forbidden.

### Scoring

Scoring should compute role-value-level TP, FP, FN, precision, recall, and micro-F1 exactly as defined by the protocol. True negatives are never counted.

### Track A Official Adapters

Official adapters should preserve dataset-official behavior for comparability. They must not replace Track B and must record evaluator version, command, and commit hash where applicable.

### Reports And Logs

Report generation should write the required machine-readable outputs: `overall_metrics.json`, `matching_log.csv`, `unmatched_cases.csv`, `error_cases.csv`, `invalid_cases.csv`, `normalization_log.csv`, `duplicate_log.csv`, and `config.json`.

### Tests

The required T01-T30 suite in the frozen protocol is the acceptance target for
evaluator freeze. Phase 2 adds protocol-v1 contract tests for canonical
prediction/gold parsing, legacy-shape rejection, schema registry metadata, and
invalid value-type diagnostics.
