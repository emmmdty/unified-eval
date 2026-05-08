from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from unified_eval.contracts import CanonicalDocument, CanonicalRecord
from unified_eval.matching import (
    FrozenRecord,
    freeze_canonical_documents,
    match_records,
    matching_log_to_csv_rows,
    pair_score,
)
from unified_eval.normalization import StrictNormalizer, normalization_config_hash
from unified_eval.official_adapters import chfinann_doc2edag, docfee, duee_fin
from unified_eval.reporting import (
    ReportArtifactInput,
    build_config_manifest,
    build_overall_metrics,
    write_report_artifacts,
)
from unified_eval.schema import SchemaRegistry
from unified_eval.scoring import ScoringResult, score_records
from unified_eval.validation import (
    FPAtom,
    ValidPredictionRecord,
    validate_prediction_jsonl,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "protocol_v1"
EXPECTED_PATH = FIXTURES / "t01_t30_expected_outputs.json"
STRICT_CONFIG_PATH = Path("configs/strict_normalizer_v1.json")


def assert_protocol_case(case_id: str, tmp_path: Path) -> None:
    expected = _expected(case_id)
    _CASES[case_id](expected, tmp_path)


def _expected(case_id: str) -> dict[str, Any]:
    payload = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    return payload[case_id]


def _schema() -> SchemaRegistry:
    return SchemaRegistry(
        dataset="ToyDEE",
        split="dev",
        event_roles={
            "EventA": frozenset({"r1", "r2", "r3"}),
            "EventB": frozenset({"b1"}),
        },
        schema_hash="sha256:schema",
        split_hash="sha256:split",
    )


def _record(
    *,
    record_index: int,
    arguments: dict[str, str | tuple[str, ...]],
    event_type: str = "EventA",
    document_id: str = "doc_001",
) -> FrozenRecord:
    return FrozenRecord(
        dataset="ToyDEE",
        split="dev",
        document_id=document_id,
        event_type=event_type,
        record_index=record_index,
        roles_to_values={
            role: frozenset((value,) if isinstance(value, str) else value)
            for role, value in arguments.items()
        },
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any] | str]) -> Path:
    lines = [
        row if isinstance(row, str) else json.dumps(row, ensure_ascii=False)
        for row in rows
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _freeze_valid_records(
    records: tuple[ValidPredictionRecord, ...],
    schema: SchemaRegistry,
) -> tuple[FrozenRecord, ...]:
    frozen: list[FrozenRecord] = []
    for record in records:
        roles_to_values: dict[str, tuple[str, ...]] = {}
        for role, value in record.arguments.items():
            if value is None:
                continue
            roles_to_values[role] = (value,) if isinstance(value, str) else value
        frozen.append(
            FrozenRecord(
                dataset=schema.dataset,
                split=schema.split,
                document_id=record.document_id,
                event_type=record.event_type,
                record_index=record.record_index,
                roles_to_values=roles_to_values,
                event_id=record.event_id,
            )
        )
    return tuple(frozen)


def _assert_counts(result: ScoringResult, expected: dict[str, Any]) -> None:
    counts = expected["counts"]
    assert result.true_positives == counts["tp"]
    assert result.false_positives == counts["fp"]
    assert result.false_negatives == counts["fn"]
    assert result.precision == pytest.approx(counts["precision"])
    assert result.recall == pytest.approx(counts["recall"])
    assert result.f1 == pytest.approx(counts["f1"])


def _assert_code_log(actual_codes: list[str], expected: dict[str, Any]) -> None:
    assert actual_codes == expected["invalid_codes"]


def _invalid_atoms(*groups: tuple[FPAtom, ...]) -> tuple[FPAtom, ...]:
    return tuple(atom for group in groups for atom in group)


def _normalizer_config() -> dict[str, Any]:
    return json.loads(STRICT_CONFIG_PATH.read_text(encoding="utf-8"))


def _case_t01(expected: dict[str, Any], _tmp_path: Path) -> None:
    record = _record(record_index=0, arguments={"r1": "A", "r2": "B"})
    result = score_records((record,), (record,), _schema())

    _assert_counts(result, expected)

    official = chfinann_doc2edag.result_from_metrics(
        precision=1.0,
        recall=1.0,
        f1=1.0,
        evaluator_version="official-v1",
        evaluator_commit_hash="official123",
        command="official_eval pred gold",
    )
    overall = build_overall_metrics(
        ReportArtifactInput(
            schema=_schema(),
            schema_version="schema-v1",
            split_version="official",
            evaluator_version="dee-eval-v1.0.0",
            scoring_result=result,
            predictions=(record,),
            golds=(record,),
            normalizer_config=_normalizer_config(),
            official=official,
            commit_hash="abc123",
        )
    )
    assert overall["official"]["precision"] == expected["official"]["precision"]
    assert overall["official"]["recall"] == expected["official"]["recall"]
    assert overall["official"]["f1"] == expected["official"]["f1"]
    assert overall["unified_strict"]["f1"] == expected["counts"]["f1"]


def _case_t02(expected: dict[str, Any], _tmp_path: Path) -> None:
    gold = _record(record_index=0, arguments={"r1": "A", "r2": "B"})
    _assert_counts(score_records((), (gold,), _schema()), expected)


def _case_t03(expected: dict[str, Any], _tmp_path: Path) -> None:
    prediction = _record(record_index=0, arguments={"r1": "A", "r2": "B"})
    _assert_counts(score_records((prediction,), (), _schema()), expected)


def _case_t04(expected: dict[str, Any], _tmp_path: Path) -> None:
    _assert_counts(score_records((), (), _schema()), expected)


def _case_t05(expected: dict[str, Any], _tmp_path: Path) -> None:
    prediction = _record(
        record_index=0,
        event_type="EventB",
        arguments={"b1": "pred"},
    )
    gold = _record(record_index=0, event_type="EventA", arguments={"r1": "gold"})
    _assert_counts(score_records((prediction,), (gold,), _schema()), expected)


def _case_t06(expected: dict[str, Any], tmp_path: Path) -> None:
    schema = _schema()
    path = _write_jsonl(
        tmp_path / "t06.jsonl",
        [
            {
                "document_id": "doc_001",
                "predictions": [
                    {"event_type": "IllegalEvent", "arguments": {"r1": "A"}}
                ],
            }
        ],
    )
    validation = validate_prediction_jsonl(
        path, schema, split_document_ids=("doc_001",)
    )
    gold = _record(record_index=0, arguments={"r1": "A"})
    result = score_records(
        (),
        (gold,),
        schema,
        invalid_fp_atoms=validation.illegal_event_fp_atoms,
    )

    _assert_counts(result, expected)
    _assert_code_log([case.code for case in validation.invalid_cases], expected)
    assert [atom.value for atom in validation.illegal_event_fp_atoms] == expected[
        "fp_atoms"
    ]
    assert result.matching_result.matches == ()


def _case_t07(expected: dict[str, Any], tmp_path: Path) -> None:
    schema = _schema()
    path = _write_jsonl(
        tmp_path / "t07.jsonl",
        [
            {
                "document_id": "doc_001",
                "predictions": [
                    {
                        "event_type": "EventA",
                        "arguments": {
                            "r1": "A",
                            "illegal_role": "illegal-role-value",
                        },
                    }
                ],
            }
        ],
    )
    validation = validate_prediction_jsonl(
        path, schema, split_document_ids=("doc_001",)
    )
    prediction_records = _freeze_valid_records(
        validation.valid_records_for_matching, schema
    )
    gold = _record(record_index=0, arguments={"r1": "A"})
    result = score_records(
        prediction_records,
        (gold,),
        schema,
        invalid_fp_atoms=validation.illegal_role_fp_atoms,
    )

    _assert_counts(result, expected)
    _assert_code_log([case.code for case in validation.invalid_cases], expected)
    assert [atom.value for atom in validation.illegal_role_fp_atoms] == expected[
        "fp_atoms"
    ]
    assert [
        (match.pred_index, match.gold_index) for match in result.matching_result.matches
    ] == [(0, 0)]


def _case_t08(expected: dict[str, Any], tmp_path: Path) -> None:
    schema = _schema()
    path = _write_jsonl(
        tmp_path / "t08.jsonl",
        ['{"document_id": "doc_001", "predictions": ['],
    )
    validation = validate_prediction_jsonl(
        path, schema, split_document_ids=("doc_001",)
    )
    gold = _record(record_index=0, arguments={"r1": "A"})
    result = score_records((), (gold,), schema)

    _assert_counts(result, expected)
    _assert_code_log([case.code for case in validation.invalid_cases], expected)
    assert (
        list(validation.empty_prediction_document_ids)
        == expected["empty_prediction_document_ids"]
    )
    assert validation.invalid_cases[0].raw_line


def _case_t09(expected: dict[str, Any], tmp_path: Path) -> None:
    schema = _schema()
    path = _write_jsonl(
        tmp_path / "t09.jsonl",
        [
            {
                "document_id": "doc_001",
                "predictions": [
                    "not-a-record",
                    {"event_type": "EventA", "arguments": {"r1": "A"}},
                ],
            }
        ],
    )
    validation = validate_prediction_jsonl(
        path, schema, split_document_ids=("doc_001",)
    )
    prediction_records = _freeze_valid_records(
        validation.valid_records_for_matching, schema
    )
    gold = _record(record_index=1, arguments={"r1": "A"})
    result = score_records(prediction_records, (gold,), schema)

    _assert_counts(result, expected)
    _assert_code_log([case.code for case in validation.invalid_cases], expected)
    assert len(prediction_records) == 1


def _case_t10(expected: dict[str, Any], tmp_path: Path) -> None:
    schema = _schema()
    path = _write_jsonl(
        tmp_path / "t10.jsonl",
        [
            {
                "document_id": "doc_001",
                "predictions": [{"event_type": "EventA", "arguments": {"r1": 1000}}],
            }
        ],
    )
    validation = validate_prediction_jsonl(
        path, schema, split_document_ids=("doc_001",)
    )
    prediction_records = _freeze_valid_records(
        validation.valid_records_for_matching, schema
    )
    gold = _record(record_index=0, arguments={"r1": "1000"})
    result = score_records(
        prediction_records,
        (gold,),
        schema,
        invalid_fp_atoms=validation.invalid_value_fp_atoms,
    )

    _assert_counts(result, expected)
    _assert_code_log([case.code for case in validation.invalid_cases], expected)
    assert [atom.value for atom in validation.invalid_value_fp_atoms] == expected[
        "fp_atoms"
    ]
    assert prediction_records[0].roles_to_values == {}


def _case_t11(expected: dict[str, Any], _tmp_path: Path) -> None:
    predictions = (
        _record(record_index=0, arguments={"r1": "A"}),
        _record(record_index=1, arguments={"r1": "A"}),
    )
    gold = _record(record_index=0, arguments={"r1": "A"})
    _assert_counts(score_records(predictions, (gold,), _schema()), expected)


def _case_t12(expected: dict[str, Any], _tmp_path: Path) -> None:
    prediction = _record(record_index=0, arguments={"r1": "A"})
    gold = _record(record_index=0, arguments={"r1": "A", "r2": "B"})
    _assert_counts(score_records((prediction,), (gold,), _schema()), expected)


def _case_t13(expected: dict[str, Any], _tmp_path: Path) -> None:
    prediction = _record(record_index=0, arguments={"r1": "pred"})
    gold = _record(record_index=0, arguments={"r1": "gold"})
    _assert_counts(score_records((prediction,), (gold,), _schema()), expected)


def _case_t14(expected: dict[str, Any], _tmp_path: Path) -> None:
    prediction = _record(record_index=0, arguments={"r1": ("B", "A")})
    gold = _record(record_index=0, arguments={"r1": ("A", "B")})
    _assert_counts(score_records((prediction,), (gold,), _schema()), expected)


def _case_t15(expected: dict[str, Any], _tmp_path: Path) -> None:
    prediction = _record(record_index=0, arguments={"r1": ("A",)})
    gold = _record(record_index=0, arguments={"r1": ("A", "B")})
    _assert_counts(score_records((prediction,), (gold,), _schema()), expected)


def _t16_records() -> tuple[tuple[FrozenRecord, ...], tuple[FrozenRecord, ...]]:
    predictions = (
        _record(record_index=0, arguments={"r1": "A"}),
        _record(record_index=1, arguments={"r1": "A", "r2": "100"}),
    )
    golds = (
        _record(record_index=0, arguments={"r1": "A", "r2": "100"}),
        _record(record_index=1, arguments={"r1": "A", "r2": "200"}),
    )
    return predictions, golds


def _case_t16(expected: dict[str, Any], _tmp_path: Path) -> None:
    predictions, golds = _t16_records()
    result = score_records(predictions, golds, _schema())

    _assert_counts(result, expected)
    assert (
        matching_log_to_csv_rows(result.matching_result.matching_log)
        == expected["matching_log"]
    )


def _case_t17(expected: dict[str, Any], _tmp_path: Path) -> None:
    predictions, golds = _t16_records()
    schema = _schema()
    greedy_total = pair_score(predictions[0], golds[0], schema) + pair_score(
        predictions[1], golds[1], schema
    )
    result = score_records(predictions, golds, schema)
    hungarian_total = sum(match.pair_score for match in result.matching_result.matches)

    _assert_counts(result, expected)
    assert greedy_total == expected["greedy_total"]
    assert hungarian_total == expected["hungarian_total"]


def _case_t18(expected: dict[str, Any], _tmp_path: Path) -> None:
    prediction = _record(record_index=0, arguments={"r1": "A"})
    gold = _record(record_index=0, arguments={"r1": "B"})
    result = score_records((prediction,), (gold,), _schema())

    _assert_counts(result, expected)
    assert result.matching_result.matches == ()
    assert (
        matching_log_to_csv_rows(result.matching_result.matching_log)
        == expected["matching_log"]
    )


def _case_t19(expected: dict[str, Any], _tmp_path: Path) -> None:
    normalizer = StrictNormalizer.from_config_path(STRICT_CONFIG_PATH)
    prediction_value = "\u200b　“ＡＣＭＥ（CN）”：1,234　　万元"
    gold_value = '"ACME(CN)":1234 万元'
    prediction_doc = CanonicalDocument(
        dataset="ToyDEE",
        split="dev",
        document_id="doc_001",
        records_field="predictions",
        records=(
            CanonicalRecord(event_type="EventA", arguments={"r1": prediction_value}),
        ),
    )
    gold_doc = CanonicalDocument(
        dataset="ToyDEE",
        split="dev",
        document_id="doc_001",
        records_field="gold_events",
        records=(CanonicalRecord(event_type="EventA", arguments={"r1": gold_value}),),
    )
    result = score_records(
        freeze_canonical_documents((prediction_doc,), normalizer=normalizer),
        freeze_canonical_documents((gold_doc,), normalizer=normalizer),
        _schema(),
    )
    normalization = normalizer.normalize(prediction_value)

    _assert_counts(result, expected)
    assert set(normalization.applied_rules) == set(expected["applied_rules"])


def _case_t20(expected: dict[str, Any], _tmp_path: Path) -> None:
    prediction = _record(
        record_index=0,
        arguments={"r1": "2024-01-02", "r2": "1亿元", "r3": "ACME"},
    )
    gold = _record(
        record_index=0,
        arguments={"r1": "2024年1月2日", "r2": "10000万元", "r3": "ACME Corp"},
    )
    result = score_records((prediction,), (gold,), _schema())
    overall = build_overall_metrics(
        ReportArtifactInput(
            schema=_schema(),
            schema_version="schema-v1",
            split_version="official",
            evaluator_version="dee-eval-v1.0.0",
            scoring_result=result,
            predictions=(prediction,),
            golds=(gold,),
            normalizer_config=_normalizer_config(),
            aux_normalized=expected["aux_normalized"],
            commit_hash="abc123",
        )
    )

    _assert_counts(result, expected)
    assert overall["unified_strict"]["f1"] == expected["counts"]["f1"]
    assert overall["aux_normalized"] == expected["aux_normalized"]


def _case_t21(expected: dict[str, Any], _tmp_path: Path) -> None:
    prediction = _record(record_index=0, arguments={"r1": "张三、李四"})
    gold = _record(record_index=0, arguments={"r1": ("张三", "李四")})
    _assert_counts(score_records((prediction,), (gold,), _schema()), expected)


def _case_t22(expected: dict[str, Any], _tmp_path: Path) -> None:
    prediction = _record(record_index=0, arguments={"r1": "ACME"})
    gold = _record(record_index=0, arguments={"r1": "ACME Corporation"})
    _assert_counts(score_records((prediction,), (gold,), _schema()), expected)


def _case_t23(expected: dict[str, Any], _tmp_path: Path) -> None:
    predictions = (
        _record(record_index=0, arguments={"r1": "A"}),
        _record(record_index=1, arguments={"r1": "B"}),
    )
    golds = (
        _record(record_index=0, arguments={"r1": "A"}),
        _record(record_index=1, arguments={"r1": "A"}),
    )
    first = match_records(predictions, golds, _schema())
    second = match_records(predictions, golds, _schema())

    assert matching_log_to_csv_rows(first.matching_log) == expected["matching_log"]
    assert matching_log_to_csv_rows(first.matching_log) == matching_log_to_csv_rows(
        second.matching_log
    )
    assert first.matching_config_hash == second.matching_config_hash


def _case_t24(expected: dict[str, Any], _tmp_path: Path) -> None:
    chfinann = chfinann_doc2edag.load_result(
        FIXTURES / "t24_chfinann_doc2edag_official_sample.json",
        evaluator_version="doc2edag-official-v1",
        evaluator_commit_hash="chfinann123",
        command="python official_eval.py pred.json gold.json",
    ).to_overall_metrics_block()
    docfee_result = docfee.load_result(
        FIXTURES / "t24_docfee_official_sample.json",
        evaluator_version="docfee-official-v1",
        evaluator_commit_hash="docfee123",
        command="python score_docfee.py pred.json gold.json",
    ).to_overall_metrics_block()
    duee = duee_fin.load_offline_official_style_result(
        FIXTURES / "t24_duee_fin_offline_official_style_sample.json",
        evaluator_version="duee-fin-offline-style-v1",
        evaluator_commit_hash="dueeoffline123",
        command="python duee_fin_offline_eval.py pred.json gold.json",
    ).to_overall_metrics_block()

    for dataset, block in {
        "ChFinAnn": chfinann,
        "DocFEE": docfee_result,
        "DuEE-Fin": duee,
    }.items():
        expected_block = expected["official_results"][dataset]
        assert {key: block[key] for key in expected_block} == expected_block
    assert any("not fully reproducible offline" in note for note in duee["notes"])


def _case_t25(expected: dict[str, Any], _tmp_path: Path) -> None:
    predictions = (
        _record(
            record_index=0,
            event_type="EventA",
            document_id="doc_001",
            arguments={"r1": "A", "r2": "wrong"},
        ),
        _record(
            record_index=1,
            event_type="EventB",
            document_id="doc_001",
            arguments={"b1": "extra_b"},
        ),
        _record(
            record_index=0,
            event_type="EventA",
            document_id="doc_003",
            arguments={"r1": "extra_a"},
        ),
    )
    golds = (
        _record(
            record_index=0,
            event_type="EventA",
            document_id="doc_001",
            arguments={"r1": "A", "r2": "right", "r3": ("G1", "G2")},
        ),
        _record(
            record_index=0,
            event_type="EventA",
            document_id="doc_002",
            arguments={"r1": "missing_a"},
        ),
    )
    invalid_atoms = (
        FPAtom(
            document_id="doc_004",
            line_number=4,
            record_index=0,
            event_type="IllegalEvent",
            role="x",
            value="illegal event fp",
            raw_value="illegal event fp",
        ),
        FPAtom(
            document_id="doc_004",
            line_number=4,
            record_index=1,
            event_type="EventA",
            role="illegal_role",
            value="illegal role fp",
            raw_value="illegal role fp",
        ),
    )

    result = score_records(
        predictions, golds, _schema(), invalid_fp_atoms=invalid_atoms
    )
    _assert_counts(result, expected)


def _case_t26(expected: dict[str, Any], _tmp_path: Path) -> None:
    record = _record(record_index=0, arguments={"r1": "A"})
    result = score_records((record,), (record,), _schema())
    config = build_config_manifest(
        ReportArtifactInput(
            schema=_schema(),
            schema_version="schema-v1",
            split_version="official",
            evaluator_version="dee-eval-v1.0.0",
            scoring_result=result,
            predictions=(record,),
            golds=(record,),
            normalizer_config=_normalizer_config(),
            commit_hash="abc123",
        )
    )
    expected_config = expected["config"]

    assert config["schema_hash"] == expected_config["schema_hash"]
    assert config["split_hash"] == expected_config["split_hash"]
    assert (
        config["normalization_config_hash"]
        == expected_config["normalization_config_hash"]
    )
    assert config["matching_config_hash"] == expected_config["matching_config_hash"]
    assert (
        config["mutation_guard"]["leaderboard_valid"]
        is expected_config["leaderboard_valid"]
    )
    assert (
        config["mutation_guard"]["mismatched_hashes"]
        == expected_config["mismatched_hashes"]
    )


def _case_t27(expected: dict[str, Any], _tmp_path: Path) -> None:
    original_config = _normalizer_config()
    changed_config = json.loads(json.dumps(original_config))
    changed_config["punctuation_map"]["."] = "."
    record = _record(record_index=0, arguments={"r1": "A"})
    result = score_records((record,), (record,), _schema())
    config = build_config_manifest(
        ReportArtifactInput(
            schema=_schema(),
            schema_version="schema-v1",
            split_version="official",
            evaluator_version="dee-eval-v1.0.0",
            scoring_result=result,
            predictions=(record,),
            golds=(record,),
            normalizer_config=changed_config,
            expected_hashes={
                "normalization_config_hash": normalization_config_hash(original_config)
            },
            commit_hash="abc123",
        )
    )

    assert config["mutation_guard"] == {
        "expected_hashes": {
            "matching_config_hash": config["matching_config_hash"],
            "normalization_config_hash": normalization_config_hash(original_config),
        },
        "actual_hashes": {
            "schema_hash": "sha256:schema",
            "split_hash": "sha256:split",
            "normalization_config_hash": config["normalization_config_hash"],
            "matching_config_hash": config["matching_config_hash"],
        },
        **expected["mutation_guard"],
    }


def _case_t28(expected: dict[str, Any], tmp_path: Path) -> None:
    schema = _schema()
    path = _write_jsonl(
        tmp_path / "t28.jsonl",
        [
            {
                "document_id": "doc_001",
                "predictions": [
                    {
                        "event_type": "EventA",
                        "arguments": {
                            "r1": "A",
                            "illegal_role": "silent-drop-guard",
                        },
                    }
                ],
            }
        ],
    )
    validation = validate_prediction_jsonl(
        path, schema, split_document_ids=("doc_001",)
    )
    prediction_records = _freeze_valid_records(
        validation.valid_records_for_matching, schema
    )
    gold = _record(record_index=0, arguments={"r1": "A"})
    invalid_atoms = _invalid_atoms(validation.illegal_role_fp_atoms)
    result = score_records(
        prediction_records,
        (gold,),
        schema,
        invalid_fp_atoms=invalid_atoms,
    )
    overall = build_overall_metrics(
        ReportArtifactInput(
            schema=schema,
            schema_version="schema-v1",
            split_version="official",
            evaluator_version="dee-eval-v1.0.0",
            scoring_result=result,
            predictions=prediction_records,
            golds=(gold,),
            normalizer_config=_normalizer_config(),
            invalid_cases=validation.invalid_cases,
            invalid_fp_atoms=invalid_atoms,
            commit_hash="abc123",
        )
    )

    _assert_counts(result, expected)
    _assert_code_log([case.code for case in validation.invalid_cases], expected)
    assert overall["diagnostics"]["invalid_role_rate"] == expected["invalid_role_rate"]


def _case_t29(expected: dict[str, Any], tmp_path: Path) -> None:
    schema = _schema()
    path = _write_jsonl(
        tmp_path / "t29.jsonl",
        [
            {
                "document_id": "doc_001",
                "predictions": [
                    {"event_type": "EventA", "arguments": {"r1": ["A", "A", "B"]}}
                ],
            }
        ],
    )
    validation = validate_prediction_jsonl(
        path, schema, split_document_ids=("doc_001",)
    )
    prediction_records = _freeze_valid_records(
        validation.valid_records_for_matching, schema
    )
    gold = _record(record_index=0, arguments={"r1": ("A", "B")})
    result = score_records(prediction_records, (gold,), schema)
    paths = write_report_artifacts(
        tmp_path / "report",
        ReportArtifactInput(
            schema=schema,
            schema_version="schema-v1",
            split_version="official",
            evaluator_version="dee-eval-v1.0.0",
            scoring_result=result,
            predictions=prediction_records,
            golds=(gold,),
            normalizer_config=_normalizer_config(),
            duplicate_value_logs=validation.duplicate_value_log,
            commit_hash="abc123",
        ),
    )
    duplicate_rows = (paths["duplicate_log.csv"]).read_text(encoding="utf-8")

    _assert_counts(result, expected)
    assert [
        {
            "document_id": entry.document_id,
            "event_type": entry.event_type,
            "role": entry.role,
            "value": entry.value,
            "count": entry.count,
        }
        for entry in validation.duplicate_value_log
    ] == expected["duplicate_value_log"]
    assert "duplicate_role_value" in duplicate_rows


def _case_t30(expected: dict[str, Any], tmp_path: Path) -> None:
    schema = _schema()
    path = _write_jsonl(
        tmp_path / "t30.jsonl",
        [
            {"document_id": "doc_unknown", "predictions": []},
            {"document_id": "doc_001", "split": "test", "predictions": []},
        ],
    )
    validation = validate_prediction_jsonl(
        path, schema, split_document_ids=("doc_001",)
    )

    _assert_code_log([case.code for case in validation.invalid_cases], expected)
    assert len(validation.valid_records_for_matching) == expected["valid_record_count"]


_CASES = {
    "T01": _case_t01,
    "T02": _case_t02,
    "T03": _case_t03,
    "T04": _case_t04,
    "T05": _case_t05,
    "T06": _case_t06,
    "T07": _case_t07,
    "T08": _case_t08,
    "T09": _case_t09,
    "T10": _case_t10,
    "T11": _case_t11,
    "T12": _case_t12,
    "T13": _case_t13,
    "T14": _case_t14,
    "T15": _case_t15,
    "T16": _case_t16,
    "T17": _case_t17,
    "T18": _case_t18,
    "T19": _case_t19,
    "T20": _case_t20,
    "T21": _case_t21,
    "T22": _case_t22,
    "T23": _case_t23,
    "T24": _case_t24,
    "T25": _case_t25,
    "T26": _case_t26,
    "T27": _case_t27,
    "T28": _case_t28,
    "T29": _case_t29,
    "T30": _case_t30,
}
