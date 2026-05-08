from __future__ import annotations

import csv
from io import StringIO

import pytest

from unified_eval.matching import (
    MATCHING_LOG_CSV_FIELDS,
    FrozenRecord,
    HungarianDependencyError,
    match_records,
    matching_log_to_csv_rows,
    pair_score,
)
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


def _record(
    *,
    record_index: int,
    arguments: dict[str, str | tuple[str, ...]],
    event_type: str = "EquityFreeze",
    document_id: str = "doc_001",
    split: str = "dev",
) -> FrozenRecord:
    return FrozenRecord(
        dataset="ToyDEE",
        split=split,
        document_id=document_id,
        event_type=event_type,
        record_index=record_index,
        roles_to_values={
            role: frozenset((value,) if isinstance(value, str) else value)
            for role, value in arguments.items()
        },
    )


def test_t16_multiple_same_type_records_use_global_hungarian_alignment(
    schema_registry: SchemaRegistry,
) -> None:
    predictions = (
        _record(record_index=0, arguments={"shareholder": "张三"}),
        _record(
            record_index=1,
            arguments={"shareholder": "张三", "amount": "1000万元"},
        ),
    )
    golds = (
        _record(
            record_index=0,
            arguments={"shareholder": "张三", "amount": "1000万元"},
        ),
        _record(
            record_index=1,
            arguments={"shareholder": "张三", "amount": "2000万元"},
        ),
    )

    result = match_records(predictions, golds, schema_registry)

    assert [(match.pred_index, match.gold_index) for match in result.matches] == [
        (0, 1),
        (1, 0),
    ]
    assert sum(match.pair_score for match in result.matches) == 3
    assert result.unmatched_predictions == ()
    assert result.unmatched_golds == ()


def test_t17_unified_hungarian_differs_from_order_sensitive_greedy_case(
    schema_registry: SchemaRegistry,
) -> None:
    predictions = (
        _record(record_index=0, arguments={"shareholder": "张三"}),
        _record(
            record_index=1,
            arguments={"shareholder": "张三", "amount": "1000万元"},
        ),
    )
    golds = (
        _record(
            record_index=0,
            arguments={"shareholder": "张三", "amount": "1000万元"},
        ),
        _record(
            record_index=1,
            arguments={"shareholder": "张三", "amount": "2000万元"},
        ),
    )

    greedy_total = pair_score(predictions[0], golds[0], schema_registry) + pair_score(
        predictions[1], golds[1], schema_registry
    )
    result = match_records(predictions, golds, schema_registry)
    hungarian_total = sum(match.pair_score for match in result.matches)

    assert greedy_total == 2
    assert hungarian_total == 3
    assert [(match.pred_index, match.gold_index) for match in result.matches] == [
        (0, 1),
        (1, 0),
    ]


def test_t18_zero_score_real_assignment_is_unmatched_and_logged(
    schema_registry: SchemaRegistry,
) -> None:
    predictions = (_record(record_index=0, arguments={"shareholder": "张三"}),)
    golds = (_record(record_index=0, arguments={"shareholder": "李四"}),)

    result = match_records(predictions, golds, schema_registry)

    assert result.matches == ()
    assert [record.record_index for record in result.unmatched_predictions] == [0]
    assert [record.record_index for record in result.unmatched_golds] == [0]

    rows = matching_log_to_csv_rows(result.matching_log)
    assert rows == [
        {
            "document_id": "doc_001",
            "event_type": "EquityFreeze",
            "pred_idx": "0",
            "gold_idx": "0",
            "pair_score": "0",
            "matched": "false",
            "matched_roles": "[]",
        }
    ]


def test_duplicate_records_are_not_collapsed(
    schema_registry: SchemaRegistry,
) -> None:
    predictions = (
        _record(record_index=0, arguments={"shareholder": "张三"}),
        _record(record_index=1, arguments={"shareholder": "张三"}),
    )
    golds = (_record(record_index=0, arguments={"shareholder": "张三"}),)

    result = match_records(predictions, golds, schema_registry)

    assert [(match.pred_index, match.gold_index) for match in result.matches] == [
        (0, 0)
    ]
    assert [record.record_index for record in result.unmatched_predictions] == [1]
    assert result.unmatched_golds == ()


def test_grouping_includes_split_and_event_type(
    schema_registry: SchemaRegistry,
) -> None:
    predictions = (
        _record(record_index=0, arguments={"shareholder": "张三"}, split="dev"),
        _record(
            record_index=1,
            event_type="EquityRepurchase",
            arguments={"company": "ACME"},
            split="dev",
        ),
    )
    golds = (
        _record(record_index=0, arguments={"shareholder": "张三"}, split="test"),
        _record(
            record_index=1,
            event_type="EquityFreeze",
            arguments={"shareholder": "ACME"},
            split="dev",
        ),
    )

    result = match_records(predictions, golds, schema_registry)

    assert result.matches == ()
    assert [record.record_index for record in result.unmatched_predictions] == [0, 1]
    assert [record.record_index for record in result.unmatched_golds] == [1, 0]


def test_matching_log_csv_rows_contain_protocol_fields(
    schema_registry: SchemaRegistry,
) -> None:
    result = match_records(
        (_record(record_index=0, arguments={"shareholder": "张三"}),),
        (_record(record_index=0, arguments={"shareholder": "张三"}),),
        schema_registry,
    )
    rows = matching_log_to_csv_rows(result.matching_log)

    assert rows
    assert set(rows[0]) == set(MATCHING_LOG_CSV_FIELDS)

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(MATCHING_LOG_CSV_FIELDS))
    writer.writeheader()
    writer.writerows(rows)

    assert (
        "document_id,event_type,pred_idx,gold_idx,pair_score,matched,matched_roles"
        in (buffer.getvalue())
    )


def test_missing_scipy_fails_clearly_without_greedy_fallback(
    monkeypatch: pytest.MonkeyPatch,
    schema_registry: SchemaRegistry,
) -> None:
    import unified_eval.matching as matching

    def missing_scipy(name: str) -> object:
        if name == "scipy.optimize":
            raise ModuleNotFoundError("No module named 'scipy'")
        return matching.importlib.import_module(name)

    monkeypatch.setattr(matching.importlib, "import_module", missing_scipy)

    with pytest.raises(
        HungarianDependencyError,
        match="requires scipy.optimize.linear_sum_assignment",
    ):
        match_records(
            (_record(record_index=0, arguments={"shareholder": "张三"}),),
            (_record(record_index=0, arguments={"shareholder": "张三"}),),
            schema_registry,
        )
