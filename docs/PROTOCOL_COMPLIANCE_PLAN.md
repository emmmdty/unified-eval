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

| Test ID | Protocol Test | Future Target Module | Current Status |
| --- | --- | --- | --- |
| T01 | Gold vs Gold | Track B scorer plus Track A adapter fixtures | Planned |
| T02 | Empty Prediction | Scoring and unmatched gold handling | Planned |
| T03 | Empty Gold | Scoring and unmatched prediction handling | Planned |
| T04 | Empty Both | Scoring zero-count handling | Planned |
| T05 | Wrong Event Type | Grouping and cross-type error handling | Planned |
| T06 | Illegal Event Type | Validation and invalid event logging | Implemented in Phase 3 |
| T07 | Illegal Role | Validation and illegal role FP accounting | Implemented in Phase 3 |
| T08 | Invalid JSON Line | Canonical I/O and invalid JSON logging | Implemented in Phase 3 |
| T09 | Invalid Record | Canonical I/O and record-level validation | Implemented in Phase 3 |
| T10 | Invalid Value Type | Value validation and invalid case logging | Implemented in Phase 3 |
| T11 | Duplicate Prediction | Duplicate record handling and unmatched FP accounting | Matching preservation implemented in Phase 5; scoring planned |
| T12 | Partial Record | Matched-pair TP/FN accounting | Planned |
| T13 | Wrong Role Value | Matched-pair FP/FN accounting | Planned |
| T14 | Multi-Value Order | Value-set representation | Planned |
| T15 | Multi-Value Partial Overlap | Strict multi-value scoring | Planned |
| T16 | Multiple Same-Type Records | Hungarian matching | Implemented in Phase 5 |
| T17 | Greedy vs Hungarian Difference | Official adapter comparison and unified matcher | Implemented in Phase 5 for unified matcher; official adapter comparison planned |
| T18 | Zero-Score Pair | Matching and unmatched conversion | Implemented in Phase 5 |
| T19 | Strict Normalization | Strict normalizer | Implemented in Phase 4 |
| T20 | Auxiliary Normalization Isolation | Auxiliary normalizer isolation | Implemented in Phase 4 for unified strict isolation; auxiliary scoring planned |
| T21 | No Auto Split | Strict normalizer and prediction repair guard | Implemented in Phase 4 |
| T22 | No External Alias | Strict normalizer and alias repair guard | Implemented in Phase 4 |
| T23 | Tie-Breaking Determinism | Matcher tie-breaking and logs | Implemented in Phase 5 |
| T24 | Official Adapter Regression | Track A official adapters | Planned |
| T25 | Unified Regression | End-to-end Track B fixtures | Planned |
| T26 | Config Hash Stability | Config and hash utilities | Matcher config hash implemented in Phase 5; broader config manifest planned |
| T27 | Test-Time Mutation Guard | Result manifest and hash validation | Planned |
| T28 | Silent Drop Guard | Validation, logging, and FP accounting | Implemented in Phase 3 |
| T29 | Duplicate Value Log | Value canonicalization and duplicate logs | Validation log implemented in Phase 3; scoring integration planned |
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
Phase 5 completes step 4 for frozen matching only. Scoring, auxiliary normalized
scoring, official adapters, full duplicate record reporting, full report
generation, and result manifests remain unimplemented.

## Non-Goals

- No LLM judge scoring.
- No semantic matching.
- No embedding similarity scoring.
- No alias repair.
- No schema, role, or event type guessing.
- No gold repair.
- No prediction repair.
- No dataset re-splitting.
