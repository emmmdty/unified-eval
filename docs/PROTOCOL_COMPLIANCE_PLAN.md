# Protocol Compliance Plan

This document tracks the implementation plan for the required test suite in `docs/DEE Evaluation Protocol Final.md`.

Phase 2 status: canonical contract code is implemented in
`src/unified_eval/contracts.py`, `src/unified_eval/schema.py`, and
`src/unified_eval/io.py`, with focused tests in
`tests/protocol_v1/test_contracts.py`. The T01-T30 scoring freeze suite below
remains planned unless explicitly noted in a later phase.

Phase 3 status: prediction validation code is implemented in
`src/unified_eval/validation.py`, with focused tests in
`tests/protocol_v1/test_validation_engine.py`. This phase covers malformed
prediction input and invalid-case accounting only; matching, scoring,
normalization, and Track A official adapters remain unimplemented.

Phase 4 status: strict normalization code is implemented in
`src/unified_eval/normalization.py`, with frozen config
`configs/strict_normalizer_v1.json` and focused tests in
`tests/protocol_v1/test_t19_t22_normalization.py`. This phase covers strict
normalization, normalization log rows, and strict normalizer config hashing
only; matching, scoring, full report generation, auxiliary normalized scoring,
and Track A official adapters remain unimplemented.

Phase 5 status: frozen matching code is implemented in
`src/unified_eval/matching.py`, with focused tests in
`tests/protocol_v1/test_t16_t18_matching.py` and
`tests/protocol_v1/test_t23_tie_breaking.py`. This phase covers grouping,
frozen role-value set records, SciPy Hungarian matching, deterministic
tie-breaking, zero-score unmatched conversion, duplicate record preservation,
matching log rows, and matcher config hashing only; scoring, full report
generation, auxiliary normalized scoring, and Track A official adapters remain
unimplemented.

Phase 6 status: final unified strict scoring code is implemented in
`src/unified_eval/scoring.py`, with focused tests in
`tests/protocol_v1/test_t01_t05_t11_t15_scoring.py`,
`tests/protocol_v1/test_t25_scoring_regression.py`, and the T25 golden fixture
under `tests/fixtures/protocol_v1/`. This phase covers matched-pair schema-role
TP/FP/FN accounting, unmatched prediction/gold accounting, invalid-output FP
atom integration, no true-negative counting, and micro P/R/F1 aggregation only;
full report generation, auxiliary normalized scoring, and Track A official
adapters remain unimplemented.

Phase 7 status: frozen report artifact generation is implemented in
`src/unified_eval/reporting.py`, with focused tests in
`tests/protocol_v1/test_t26_t27_report_artifacts.py`. This phase covers all
required protocol-v1 output files, stable CSV headers, `overall_metrics.json`,
`config.json`, dependency and commit metadata, config hash stability, and the
test-time mutation guard. Track A official adapters and auxiliary normalized
scoring remain unimplemented.

Phase 8 status: Track A official adapter interfaces are implemented in
`src/unified_eval/official_adapters/`, with focused tests in
`tests/protocol_v1/test_t24_official_adapters.py` and fixed samples under
`tests/fixtures/protocol_v1/`. This phase covers the stable
`official-metric-result-v1` schema, `available=false` unavailable results,
ChFinAnn Doc2EDAG and DocFEE fixed-sample loading, DuEE-Fin online-official vs
offline-official-style separation, and the boundary that Track A adapters do
not import Track B matching or scoring. Complete offline reproductions of every
dataset-official evaluator and auxiliary normalized scoring remain
unimplemented.

| Test ID | Protocol Test | Future Target Module | Current Status |
| --- | --- | --- | --- |
| T01 | Gold vs Gold | Track B scorer plus Track A adapter fixtures | Unified scorer implemented in Phase 6; Track A adapter planned |
| T02 | Empty Prediction | Scoring and unmatched gold handling | Implemented in Phase 6 |
| T03 | Empty Gold | Scoring and unmatched prediction handling | Implemented in Phase 6 |
| T04 | Empty Both | Scoring zero-count handling | Implemented in Phase 6 |
| T05 | Wrong Event Type | Grouping and cross-type error handling | Implemented in Phase 6 for unified scorer |
| T06 | Illegal Event Type | Validation and invalid event logging | Implemented in Phase 3 |
| T07 | Illegal Role | Validation and illegal role FP accounting | Implemented in Phase 3 |
| T08 | Invalid JSON Line | Canonical I/O and invalid JSON logging | Implemented in Phase 3 |
| T09 | Invalid Record | Canonical I/O and record-level validation | Implemented in Phase 3 |
| T10 | Invalid Value Type | Value validation and invalid case logging | Implemented in Phase 3 |
| T11 | Duplicate Prediction | Duplicate record handling and unmatched FP accounting | Implemented in Phase 6 |
| T12 | Partial Record | Matched-pair TP/FN accounting | Implemented in Phase 6 |
| T13 | Wrong Role Value | Matched-pair FP/FN accounting | Implemented in Phase 6 |
| T14 | Multi-Value Order | Value-set representation | Implemented in Phase 6 |
| T15 | Multi-Value Partial Overlap | Strict multi-value scoring | Implemented in Phase 6 |
| T16 | Multiple Same-Type Records | Hungarian matching | Implemented in Phase 5 |
| T17 | Greedy vs Hungarian Difference | Official adapter comparison and unified matcher | Implemented in Phase 5 for unified matcher; Phase 8 keeps official adapter interfaces separate from Track B matching/scoring |
| T18 | Zero-Score Pair | Matching and unmatched conversion | Implemented in Phase 5 |
| T19 | Strict Normalization | Strict normalizer | Implemented in Phase 4 |
| T20 | Auxiliary Normalization Isolation | Auxiliary normalizer isolation | Implemented in Phase 4 for unified strict isolation; auxiliary scoring planned |
| T21 | No Auto Split | Strict normalizer and prediction repair guard | Implemented in Phase 4 |
| T22 | No External Alias | Strict normalizer and alias repair guard | Implemented in Phase 4 |
| T23 | Tie-Breaking Determinism | Matcher tie-breaking and logs | Implemented in Phase 5 |
| T24 | Official Adapter Regression | Track A official adapters | Adapter-interface regression implemented in Phase 8 for ChFinAnn, DocFEE, and DuEE-Fin offline official-style fixed samples |
| T25 | Unified Regression | End-to-end Track B fixtures | Scoring golden fixture implemented in Phase 6; full report fixture planned |
| T26 | Config Hash Stability | Config and hash utilities | Implemented in Phase 7 |
| T27 | Test-Time Mutation Guard | Result manifest and hash validation | Implemented in Phase 7 |
| T28 | Silent Drop Guard | Validation, logging, and FP accounting | Implemented in Phase 3 |
| T29 | Duplicate Value Log | Value canonicalization and duplicate logs | Validation log implemented in Phase 3; duplicate report artifact emitted in Phase 7 |
| T30 | Dataset Split Check | Dataset adapter and split validation | Implemented in Phase 3 |

## Implementation Order

1. Establish tiny fixture schemas and canonical JSONL fixtures.
2. Implement canonical I/O and validation tests before evaluator logic.
3. Implement strict normalization in isolation.
4. Implement grouping and deterministic matching.
5. Implement TP/FP/FN accounting and unified strict aggregation.
6. Add required logs and reproducibility metadata.
7. Add Track A official adapter interfaces and regression fixtures.
8. Run T01-T30 as the freeze gate before any test-set reporting.

Phase 2 completes steps 1-2 only for the canonical contract surface. Phase 3
adds invalid-case CSV serialization and duplicate role-value logs for prediction
validation. Phase 4 completes step 3 for strict unified normalization only.
Phase 5 completes step 4 for frozen matching only. Phase 6 completes step 5 for
final unified strict scoring only. Phase 7 completes step 6 for required
machine-readable logs and reproducibility metadata. Phase 8 completes step 7
for official adapter interfaces and fixed adapter-result samples only. Complete
official script reproductions and auxiliary normalized scoring remain
unimplemented.

## Non-Goals

- No LLM judge scoring.
- No semantic matching.
- No embedding similarity scoring.
- No alias repair.
- No schema, role, or event type guessing.
- No gold repair.
- No prediction repair.
- No dataset re-splitting.
- No substitution of Track B unified strict scores for unavailable Track A
  official scores.
- No mixing of DuEE-Fin offline official-style results with online official
  leaderboard results.
