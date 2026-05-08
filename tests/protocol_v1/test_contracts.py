from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from unified_eval.contracts import ContractValidationError
from unified_eval.io import read_gold_jsonl, read_prediction_jsonl
from unified_eval.schema import SchemaRegistry


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


def test_canonical_prediction_jsonl_parses(
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
                        "event_id": "pred-1",
                        "arguments": {
                            "shareholder": ["张三", "李四"],
                            "amount": "1000万元",
                            "date": None,
                        },
                    }
                ],
            }
        ],
    )

    documents = read_prediction_jsonl(path, schema_registry)

    assert len(documents) == 1
    document = documents[0]
    assert document.document_id == "doc_001"
    assert document.dataset == "ToyDEE"
    assert document.split == "dev"
    assert document.records_field == "predictions"
    assert len(document.records) == 1

    record = document.records[0]
    assert record.event_type == "EquityFreeze"
    assert record.event_id == "pred-1"
    assert record.arguments == {
        "shareholder": ("张三", "李四"),
        "amount": "1000万元",
        "date": None,
    }


def test_canonical_gold_jsonl_parses(
    tmp_path: Path, schema_registry: SchemaRegistry
) -> None:
    path = _write_jsonl(
        tmp_path / "gold.jsonl",
        [
            {
                "document_id": "doc_001",
                "gold_events": [
                    {
                        "event_type": "EquityFreeze",
                        "event_id": "gold-1",
                        "arguments": {
                            "shareholder": ["张三", "李四"],
                            "amount": "1000万元",
                        },
                    }
                ],
            }
        ],
    )

    documents = read_gold_jsonl(path, schema_registry)

    assert len(documents) == 1
    document = documents[0]
    assert document.document_id == "doc_001"
    assert document.records_field == "gold_events"
    assert document.records[0].event_type == "EquityFreeze"
    assert document.records[0].event_id == "gold-1"
    assert document.records[0].arguments == {
        "shareholder": ("张三", "李四"),
        "amount": "1000万元",
    }


def test_schema_registry_exposes_protocol_metadata(
    schema_registry: SchemaRegistry,
) -> None:
    assert schema_registry.dataset == "ToyDEE"
    assert schema_registry.split == "dev"
    assert schema_registry.legal_event_types == frozenset(
        {"EquityFreeze", "EquityRepurchase"}
    )
    assert schema_registry.legal_roles("EquityFreeze") == frozenset(
        {"shareholder", "amount", "date"}
    )
    assert schema_registry.schema_hash == "sha256:schema"
    assert schema_registry.split_hash == "sha256:split"


@pytest.mark.parametrize(
    ("reader", "legacy_row"),
    [
        (read_prediction_jsonl, {"doc_id": "doc_001", "events": []}),
        (read_gold_jsonl, {"doc_id": "doc_001", "events": []}),
    ],
)
def test_legacy_doc_id_events_is_rejected_by_main_jsonl_readers(
    tmp_path: Path,
    schema_registry: SchemaRegistry,
    reader: Callable[[Path, SchemaRegistry], object],
    legacy_row: dict[str, object],
) -> None:
    path = _write_jsonl(tmp_path / "legacy.jsonl", [legacy_row])

    with pytest.raises(ContractValidationError) as exc_info:
        reader(path, schema_registry)

    assert exc_info.value.issues[0].code == "missing_document_id"


@pytest.mark.parametrize(
    ("reader", "records_field"),
    [
        (read_prediction_jsonl, "predictions"),
        (read_gold_jsonl, "gold_events"),
    ],
)
@pytest.mark.parametrize(
    "bad_value",
    [
        {"raw": "1000万元"},
        1000,
        ["张三", 20240101],
    ],
)
def test_invalid_role_values_are_reported_without_string_coercion(
    tmp_path: Path,
    schema_registry: SchemaRegistry,
    reader: Callable[[Path, SchemaRegistry], object],
    records_field: str,
    bad_value: object,
) -> None:
    path = _write_jsonl(
        tmp_path / "bad-values.jsonl",
        [
            {
                "document_id": "doc_001",
                records_field: [
                    {
                        "event_type": "EquityFreeze",
                        "arguments": {"amount": bad_value},
                    }
                ],
            }
        ],
    )

    with pytest.raises(ContractValidationError) as exc_info:
        reader(path, schema_registry)

    issue = exc_info.value.issues[0]
    assert issue.code == "invalid_value_type"
    assert issue.raw_value == bad_value


@pytest.mark.parametrize(
    ("row", "expected_code"),
    [
        (
            {
                "document_id": "doc_001",
                "predictions": [
                    {"event_type": "UnknownType", "arguments": {"amount": "1000"}}
                ],
            },
            "illegal_event_type",
        ),
        (
            {
                "document_id": "doc_001",
                "predictions": [
                    {
                        "event_type": "EquityFreeze",
                        "arguments": {"unknown_role": "1000"},
                    }
                ],
            },
            "illegal_role",
        ),
    ],
)
def test_schema_registry_is_used_for_event_type_and_role_validation(
    tmp_path: Path,
    schema_registry: SchemaRegistry,
    row: dict[str, object],
    expected_code: str,
) -> None:
    path = _write_jsonl(tmp_path / "schema-invalid.jsonl", [row])

    with pytest.raises(ContractValidationError) as exc_info:
        read_prediction_jsonl(path, schema_registry)

    assert exc_info.value.issues[0].code == expected_code
