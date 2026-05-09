# Protocol Compliance Matrix

This is the protocol-v1 coverage report for the frozen test list in
`docs/DEE Evaluation Protocol Final.md`.

Verification command:

```bash
uv run pytest tests/protocol_v1
```

Latest local verification:

- `uv run pytest tests/protocol_v1`: `91 passed`
- individual execution of all required `test_t01_*.py` to `test_t30_*.py`
  files: `30 passed`

Golden expected outputs:

- `tests/fixtures/protocol_v1/t01_t30_expected_outputs.json`
- `tests/fixtures/protocol_v1/t24_chfinann_doc2edag_official_sample.json`
- `tests/fixtures/protocol_v1/t24_docfee_official_sample.json`
- `tests/fixtures/protocol_v1/t24_duee_fin_offline_official_style_sample.json`
- `tests/fixtures/protocol_v1/t25_unified_regression_golden.json`

| Test ID | Protocol Case | Status | Test File | Golden / Expected Evidence |
| --- | --- | --- | --- | --- |
| T01 | Gold vs Gold | PASS | `tests/protocol_v1/test_t01_gold_vs_gold.py` | Expected official and unified P/R/F1 in `t01_t30_expected_outputs.json` |
| T02 | Empty Prediction | PASS | `tests/protocol_v1/test_t02_empty_prediction.py` | Expected TP=0, FP=0, FN=2, F1=0 in `t01_t30_expected_outputs.json` |
| T03 | Empty Gold | PASS | `tests/protocol_v1/test_t03_empty_gold.py` | Expected TP=0, FP=2, FN=0, F1=0 in `t01_t30_expected_outputs.json` |
| T04 | Empty Both | PASS | `tests/protocol_v1/test_t04_empty_both.py` | Expected TP=0, FP=0, FN=0, F1=0 in `t01_t30_expected_outputs.json` |
| T05 | Wrong Event Type | PASS | `tests/protocol_v1/test_t05_wrong_event_type.py` | Expected cross-type FP/FN counts in `t01_t30_expected_outputs.json` |
| T06 | Illegal Event Type | PASS | `tests/protocol_v1/test_t06_illegal_event_type.py` | Expected invalid-event log and FP atom in `t01_t30_expected_outputs.json` |
| T07 | Illegal Role | PASS | `tests/protocol_v1/test_t07_illegal_role.py` | Expected invalid-role log, legal match, and FP atom in `t01_t30_expected_outputs.json` |
| T08 | Invalid JSON Line | PASS | `tests/protocol_v1/test_t08_invalid_json_line.py` | Expected invalid-json log and empty-prediction document in `t01_t30_expected_outputs.json` |
| T09 | Invalid Record | PASS | `tests/protocol_v1/test_t09_invalid_record.py` | Expected malformed-record log and continuing valid record score in `t01_t30_expected_outputs.json` |
| T10 | Invalid Value Type | PASS | `tests/protocol_v1/test_t10_invalid_value_type.py` | Expected invalid-value log, FP atom, and unmatched gold FN in `t01_t30_expected_outputs.json` |
| T11 | Duplicate Prediction | PASS | `tests/protocol_v1/test_t11_duplicate_prediction.py` | Expected duplicate-unmatched FP count in `t01_t30_expected_outputs.json` |
| T12 | Partial Record | PASS | `tests/protocol_v1/test_t12_partial_record.py` | Expected matched TP plus missing-role FN in `t01_t30_expected_outputs.json` |
| T13 | Wrong Role Value | PASS | `tests/protocol_v1/test_t13_wrong_role_value.py` | Expected role-value FP/FN mismatch counts in `t01_t30_expected_outputs.json` |
| T14 | Multi-Value Order | PASS | `tests/protocol_v1/test_t14_multi_value_order.py` | Expected unordered set TP=2 in `t01_t30_expected_outputs.json` |
| T15 | Multi-Value Partial Overlap | PASS | `tests/protocol_v1/test_t15_multi_value_partial_overlap.py` | Expected strict mismatch FP=1, FN=2 in `t01_t30_expected_outputs.json` |
| T16 | Multiple Same-Type Records | PASS | `tests/protocol_v1/test_t16_multiple_same_type_records.py` | Expected Hungarian matching log and TP/FP/FN in `t01_t30_expected_outputs.json` |
| T17 | Greedy vs Hungarian Difference | PASS | `tests/protocol_v1/test_t17_greedy_vs_hungarian_difference.py` | Expected greedy total 2 vs Hungarian total 3 in `t01_t30_expected_outputs.json` |
| T18 | Zero-Score Pair | PASS | `tests/protocol_v1/test_t18_zero_score_pair.py` | Expected unmatched zero-score matching log in `t01_t30_expected_outputs.json` |
| T19 | Strict Normalization | PASS | `tests/protocol_v1/test_t19_strict_normalization.py` | Expected strict normalized match and rule log in `t01_t30_expected_outputs.json` |
| T20 | Auxiliary Normalization Isolation | PASS | `tests/protocol_v1/test_t20_auxiliary_normalization_isolation.py` | Expected unified strict F1=0 and separate aux F1=1 in `t01_t30_expected_outputs.json` |
| T21 | No Auto Split | PASS | `tests/protocol_v1/test_t21_no_auto_split.py` | Expected no split, FP=1, FN=2 in `t01_t30_expected_outputs.json` |
| T22 | No External Alias | PASS | `tests/protocol_v1/test_t22_no_external_alias.py` | Expected alias mismatch FP=1, FN=1 in `t01_t30_expected_outputs.json` |
| T23 | Tie-Breaking Determinism | PASS | `tests/protocol_v1/test_t23_tie_breaking_determinism.py` | Expected repeated matching log in `t01_t30_expected_outputs.json` |
| T24 | Official-Result Schema / Fixture Ingestion Regression | PASS | `tests/protocol_v1/test_t24_official_result_schema_fixture_ingestion.py` | Expected ChFinAnn, DocFEE, and DuEE-Fin official-result schema blocks from fixture JSON files; this is not official runner reproduction |
| T25 | Unified Regression | PASS | `tests/protocol_v1/test_t25_unified_regression.py` | Expected unified TP/FP/FN/F1 in `t01_t30_expected_outputs.json` and `t25_unified_regression_golden.json` |
| T26 | Config Hash Stability | PASS | `tests/protocol_v1/test_t26_config_hash_stability.py` | Expected schema, split, normalizer, and matcher hashes in `t01_t30_expected_outputs.json` |
| T27 | Test-Time Mutation Guard | PASS | `tests/protocol_v1/test_t27_test_time_mutation_guard.py` | Expected changed hash and leaderboard invalidation in `t01_t30_expected_outputs.json` |
| T28 | Silent Drop Guard | PASS | `tests/protocol_v1/test_t28_silent_drop_guard.py` | Expected invalid-role rate > 0 and FP count in `t01_t30_expected_outputs.json` |
| T29 | Duplicate Value Log | PASS | `tests/protocol_v1/test_t29_duplicate_value_log.py` | Expected duplicate-value log and set-based TP count in `t01_t30_expected_outputs.json` |
| T30 | Dataset Split Check | PASS | `tests/protocol_v1/test_t30_dataset_split_check.py` | Expected unknown-document and split-mismatch logs in `t01_t30_expected_outputs.json` |

No row in this matrix treats gold-vs-gold, empty-vs-gold, or smoke execution as
complete protocol proof. Each T01-T30 row is backed by a named regression test
and explicit golden counts or log expectations.

Track A coverage in v1.0.0 is limited to official result schema, fixed-result
ingestion, and explicit unavailable blocks. It does not claim complete ChFinAnn
Doc2EDAG, DocFEE, or DuEE-Fin official evaluator runner reproduction, and Track
B Unified Strict Role-Value Micro-F1 must not be substituted for unavailable
official metrics.
