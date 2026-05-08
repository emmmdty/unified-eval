from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path

import pytest

from unified_eval.schema import SchemaRegistry
from unified_eval.validation import invalid_cases_to_csv_rows, validate_prediction_jsonl


@pytest.fixture
def schema_registry() -> SchemaRegistry:
    return SchemaRegistry(
        dataset="ToyDEE",
        split="dev",
        event_roles={
            "EquityFreeze": frozenset({"shareholder", "amount", "date"}),
            "EquityRepurchase": frozenset({"company", "amount"}),
        },
        schema_hash="sha256:schema",
        split_hash="sha256:split",
    )


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _codes(result: object) -> list[str]:
    return [case.code for case in result.invalid_cases]


def test_t06_t07_t10_t28_accounts_invalid_atoms_without_silent_drop(
    tmp_path: Path, schema_registry: SchemaRegistry
) -> None:
    path = _write_jsonl(
        tmp_path / "predictions.jsonl",
        [
            {
                "document_id": "doc_001",
                "predictions": [
                    {
                        "event_type": "EquityFreeze",
                        "event_id": "pred-legal-partial",
                        "arguments": {
                            "shareholder": ["张三", "张三", "李四"],
                            "amount": 1000,
                            "unknown_role": ["额外值", "", "另一个额外值"],
                            "date": None,
                        },
                    },
                    {
                        "event_type": "IllegalType",
                        "arguments": {
                            "ghost_role": "非法事件值",
                            "empty_role": "   ",
                            "multi_role": ["A", "", "B"],
                        },
                    },
                ],
            }
        ],
    )

    result = validate_prediction_jsonl(
        path, schema_registry, split_document_ids=("doc_001",)
    )

    assert [record.event_type for record in result.valid_records_for_matching] == [
        "EquityFreeze"
    ]
    valid_record = result.valid_records_for_matching[0]
    assert valid_record.document_id == "doc_001"
    assert valid_record.event_id == "pred-legal-partial"
    assert valid_record.arguments == {
        "shareholder": ("张三", "李四"),
        "date": None,
    }

    assert "illegal_event_type" in _codes(result)
    assert "illegal_role" in _codes(result)
    assert "invalid_value_type" in _codes(result)

    assert [atom.value for atom in result.illegal_event_fp_atoms] == [
        "非法事件值",
        "A",
        "B",
    ]
    assert [atom.value for atom in result.illegal_role_fp_atoms] == [
        "额外值",
        "另一个额外值",
    ]
    assert [(atom.role, atom.raw_value) for atom in result.invalid_value_fp_atoms] == [
        ("amount", 1000)
    ]
    assert [
        (entry.document_id, entry.event_type, entry.role, entry.value, entry.count)
        for entry in result.duplicate_value_log
    ] == [("doc_001", "EquityFreeze", "shareholder", "张三", 2)]


def test_t08_invalid_json_line_is_empty_prediction_for_split_document(
    tmp_path: Path, schema_registry: SchemaRegistry
) -> None:
    path = tmp_path / "bad-json.jsonl"
    path.write_text(
        json.dumps(
            {
                "document_id": "doc_001",
                "predictions": [
                    {"event_type": "EquityFreeze", "arguments": {"amount": "100"}}
                ],
            },
            ensure_ascii=False,
        )
        + "\n"
        + '{"document_id": "doc_002", "predictions": ['
        + "\n"
        + json.dumps(
            {
                "document_id": "doc_003",
                "predictions": [
                    {
                        "event_type": "EquityRepurchase",
                        "arguments": {"company": "ACME"},
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = validate_prediction_jsonl(
        path, schema_registry, split_document_ids=("doc_001", "doc_002", "doc_003")
    )

    assert [case.code for case in result.invalid_cases] == ["invalid_json"]
    assert result.invalid_cases[0].document_id == "doc_002"
    assert result.empty_prediction_document_ids == ("doc_002",)
    assert [record.document_id for record in result.valid_records_for_matching] == [
        "doc_001",
        "doc_003",
    ]


def test_t09_malformed_records_are_logged_and_other_records_continue(
    tmp_path: Path, schema_registry: SchemaRegistry
) -> None:
    path = _write_jsonl(
        tmp_path / "malformed-records.jsonl",
        [
            {
                "document_id": "doc_001",
                "predictions": [
                    "not-object",
                    {"arguments": {"amount": "100"}},
                    {"event_type": 42, "arguments": {"amount": "100"}},
                    {"event_type": "EquityFreeze"},
                    {"event_type": "EquityFreeze", "arguments": []},
                    {"event_type": "EquityFreeze", "arguments": {"amount": "100"}},
                ],
            }
        ],
    )

    result = validate_prediction_jsonl(
        path, schema_registry, split_document_ids=("doc_001",)
    )

    assert _codes(result) == [
        "invalid_record_type",
        "missing_event_type",
        "invalid_event_type_type",
        "missing_arguments",
        "invalid_arguments_type",
    ]
    assert len(result.valid_records_for_matching) == 1
    assert result.valid_records_for_matching[0].arguments == {"amount": "100"}


def test_document_level_shape_errors_are_logged(
    tmp_path: Path, schema_registry: SchemaRegistry
) -> None:
    path = _write_jsonl(
        tmp_path / "document-errors.jsonl",
        [
            {"predictions": []},
            {"document_id": 1, "predictions": []},
            {"document_id": "doc_missing_predictions"},
            {"document_id": "doc_bad_predictions", "predictions": {}},
        ],
    )

    result = validate_prediction_jsonl(
        path,
        schema_registry,
        split_document_ids=(
            "doc_missing_predictions",
            "doc_bad_predictions",
        ),
    )

    assert _codes(result) == [
        "missing_document_id",
        "invalid_document_id_type",
        "missing_predictions",
        "invalid_predictions_type",
    ]
    assert result.valid_records_for_matching == ()


def test_t30_split_validation_reports_unknown_document_and_split_mismatch(
    tmp_path: Path, schema_registry: SchemaRegistry
) -> None:
    path = _write_jsonl(
        tmp_path / "wrong-split.jsonl",
        [
            {"document_id": "doc_unknown", "predictions": []},
            {"document_id": "doc_001", "split": "test", "predictions": []},
        ],
    )

    result = validate_prediction_jsonl(
        path, schema_registry, split_document_ids=("doc_001",)
    )

    assert _codes(result) == ["unknown_document_id", "split_mismatch"]
    assert result.valid_records_for_matching == ()


def test_invalid_cases_are_csv_serializable(
    tmp_path: Path, schema_registry: SchemaRegistry
) -> None:
    path = _write_jsonl(
        tmp_path / "csv-invalid-cases.jsonl",
        [
            {
                "document_id": "doc_001",
                "predictions": [
                    {"event_type": "EquityFreeze", "arguments": {"amount": 1000}}
                ],
            }
        ],
    )
    result = validate_prediction_jsonl(
        path, schema_registry, split_document_ids=("doc_001",)
    )

    rows = invalid_cases_to_csv_rows(result.invalid_cases)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

    csv_text = buffer.getvalue()
    assert "invalid_value_type" in csv_text
    assert "1000" in csv_text
