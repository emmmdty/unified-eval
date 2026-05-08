# Protocol Compliance Plan

This document tracks the implementation plan for the required test suite in `docs/DEE Evaluation Protocol Final.md`.

Phase 0 status: scaffold only. Every protocol test below is planned, not implemented, except the repository smoke import test in `tests/test_smoke.py`.

| Test ID | Protocol Test | Future Target Module | Phase 0 Status |
| --- | --- | --- | --- |
| T01 | Gold vs Gold | Track B scorer plus Track A adapter fixtures | Planned |
| T02 | Empty Prediction | Scoring and unmatched gold handling | Planned |
| T03 | Empty Gold | Scoring and unmatched prediction handling | Planned |
| T04 | Empty Both | Scoring zero-count handling | Planned |
| T05 | Wrong Event Type | Grouping and cross-type error handling | Planned |
| T06 | Illegal Event Type | Validation and invalid event logging | Planned |
| T07 | Illegal Role | Validation and illegal role FP accounting | Planned |
| T08 | Invalid JSON Line | Canonical I/O and invalid JSON logging | Planned |
| T09 | Invalid Record | Canonical I/O and record-level validation | Planned |
| T10 | Invalid Value Type | Value validation and invalid case logging | Planned |
| T11 | Duplicate Prediction | Duplicate record handling and unmatched FP accounting | Planned |
| T12 | Partial Record | Matched-pair TP/FN accounting | Planned |
| T13 | Wrong Role Value | Matched-pair FP/FN accounting | Planned |
| T14 | Multi-Value Order | Value-set representation | Planned |
| T15 | Multi-Value Partial Overlap | Strict multi-value scoring | Planned |
| T16 | Multiple Same-Type Records | Hungarian matching | Planned |
| T17 | Greedy vs Hungarian Difference | Official adapter comparison and unified matcher | Planned |
| T18 | Zero-Score Pair | Matching and unmatched conversion | Planned |
| T19 | Strict Normalization | Strict normalizer | Planned |
| T20 | Auxiliary Normalization Isolation | Auxiliary normalizer isolation | Planned |
| T21 | No Auto Split | Strict normalizer and prediction repair guard | Planned |
| T22 | No External Alias | Strict normalizer and alias repair guard | Planned |
| T23 | Tie-Breaking Determinism | Matcher tie-breaking and logs | Planned |
| T24 | Official Adapter Regression | Track A official adapters | Planned |
| T25 | Unified Regression | End-to-end Track B fixtures | Planned |
| T26 | Config Hash Stability | Config and hash utilities | Planned |
| T27 | Test-Time Mutation Guard | Result manifest and hash validation | Planned |
| T28 | Silent Drop Guard | Validation, logging, and FP accounting | Planned |
| T29 | Duplicate Value Log | Value canonicalization and duplicate logs | Planned |
| T30 | Dataset Split Check | Dataset adapter and split validation | Planned |

## Implementation Order

1. Establish tiny fixture schemas and canonical JSONL fixtures.
2. Implement canonical I/O and validation tests before evaluator logic.
3. Implement strict normalization in isolation.
4. Implement grouping and deterministic matching.
5. Implement TP/FP/FN accounting and unified strict aggregation.
6. Add required logs and reproducibility metadata.
7. Add Track A official adapter interfaces and regression fixtures.
8. Run T01-T30 as the freeze gate before any test-set reporting.

## Non-Goals

- No LLM judge scoring.
- No semantic matching.
- No embedding similarity scoring.
- No alias repair.
- No schema, role, or event type guessing.
- No gold repair.
- No prediction repair.
- No dataset re-splitting.
