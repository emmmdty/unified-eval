# Unified Eval

`unified-eval` is a protocol-first repository for Chinese financial document-level event extraction evaluation over DuEE-Fin, ChFinAnn, and DocFEE.

The frozen authority is `docs/DEE Evaluation Protocol Final.md`. Implementations must follow that protocol exactly.

## Phase 6 Status

This repository implements the frozen canonical contract layer for protocol-v1
prediction and gold JSONL, plus the frozen validation/accounting layer for
malformed prediction input. It also implements strict normalization for the
unified strict metric exactly within the frozen protocol's allowed character
rules. Phase 5 adds frozen event-type-constrained Hungarian matching for
already normalized role-value records. Phase 6 adds final unified strict
role-value micro scoring over matched and unmatched records.

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

Not implemented yet:

- Track A official adapter implementations;
- copied dataset files;
- dataset splitting or data preprocessing.

## Boundaries

- Do not modify `~/myProjects/masterProjects/DEE/data`.
- Do not copy large files into this repository.
- Do not implement LLM judge scoring, semantic matching, embedding similarity, alias repair, schema guessing, role guessing, event type guessing, gold repair, or prediction repair.
- Keep Track A official metrics and Track B unified strict metrics separate.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
make check
```

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
