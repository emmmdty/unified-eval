from __future__ import annotations

from collections.abc import Iterable

import pytest

from unified_eval.matching import FrozenRecord
from unified_eval.schema import SchemaRegistry
from unified_eval.scoring import score_records
from unified_eval.validation import FPAtom


@pytest.fixture
def schema_registry() -> SchemaRegistry:
    return SchemaRegistry(
        dataset="ToyDEE",
        split="dev",
        event_roles={
            "EventA": frozenset({"r1", "r2"}),
            "EventB": frozenset({"b1"}),
        },
        schema_hash="sha256:schema",
        split_hash="sha256:split",
    )


def _record(
    *,
    record_index: int,
    arguments: dict[str, str | Iterable[str]],
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


def _assert_counts(
    result: object,
    *,
    tp: int,
    fp: int,
    fn: int,
) -> None:
    assert result.true_positives == tp
    assert result.false_positives == fp
    assert result.false_negatives == fn


def test_t01_gold_vs_gold_scores_perfect_micro_f1(
    schema_registry: SchemaRegistry,
) -> None:
    record = _record(record_index=0, arguments={"r1": "A", "r2": "B"})

    result = score_records((record,), (record,), schema_registry)

    _assert_counts(result, tp=2, fp=0, fn=0)
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1 == 1.0


def test_t02_empty_prediction_counts_all_gold_values_as_fn(
    schema_registry: SchemaRegistry,
) -> None:
    gold = _record(record_index=0, arguments={"r1": "A", "r2": "B"})

    result = score_records((), (gold,), schema_registry)

    _assert_counts(result, tp=0, fp=0, fn=2)
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.f1 == 0.0


def test_t03_empty_gold_counts_all_prediction_values_as_fp(
    schema_registry: SchemaRegistry,
) -> None:
    prediction = _record(record_index=0, arguments={"r1": "A", "r2": "B"})

    result = score_records((prediction,), (), schema_registry)

    _assert_counts(result, tp=0, fp=2, fn=0)
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.f1 == 0.0


def test_t04_empty_both_has_no_true_negative_count(
    schema_registry: SchemaRegistry,
) -> None:
    result = score_records((), (), schema_registry)

    _assert_counts(result, tp=0, fp=0, fn=0)
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.f1 == 0.0


def test_t05_wrong_event_type_counts_prediction_fp_and_gold_fn(
    schema_registry: SchemaRegistry,
) -> None:
    prediction = _record(
        record_index=0,
        event_type="EventB",
        arguments={"b1": "pred"},
    )
    gold = _record(record_index=0, event_type="EventA", arguments={"r1": "gold"})

    result = score_records((prediction,), (gold,), schema_registry)

    _assert_counts(result, tp=0, fp=1, fn=1)


def test_t11_duplicate_prediction_leaves_extra_duplicate_as_fp(
    schema_registry: SchemaRegistry,
) -> None:
    predictions = (
        _record(record_index=0, arguments={"r1": "A"}),
        _record(record_index=1, arguments={"r1": "A"}),
    )
    gold = _record(record_index=0, arguments={"r1": "A"})

    result = score_records(predictions, (gold,), schema_registry)

    _assert_counts(result, tp=1, fp=1, fn=0)


def test_t12_partial_record_counts_exact_role_tp_and_missing_role_fn(
    schema_registry: SchemaRegistry,
) -> None:
    prediction = _record(record_index=0, arguments={"r1": "A"})
    gold = _record(record_index=0, arguments={"r1": "A", "r2": "B"})

    result = score_records((prediction,), (gold,), schema_registry)

    _assert_counts(result, tp=1, fp=0, fn=1)


def test_matched_pair_extra_prediction_role_counts_fp(
    schema_registry: SchemaRegistry,
) -> None:
    prediction = _record(record_index=0, arguments={"r1": "A", "r2": "extra"})
    gold = _record(record_index=0, arguments={"r1": "A"})

    result = score_records((prediction,), (gold,), schema_registry)

    _assert_counts(result, tp=1, fp=1, fn=0)


def test_t13_wrong_role_value_counts_predicted_fp_and_gold_fn(
    schema_registry: SchemaRegistry,
) -> None:
    prediction = _record(record_index=0, arguments={"r1": "pred"})
    gold = _record(record_index=0, arguments={"r1": "gold"})

    result = score_records((prediction,), (gold,), schema_registry)

    _assert_counts(result, tp=0, fp=1, fn=1)


def test_t14_multi_value_order_is_an_exact_set_match(
    schema_registry: SchemaRegistry,
) -> None:
    prediction = _record(record_index=0, arguments={"r1": ("B", "A")})
    gold = _record(record_index=0, arguments={"r1": ("A", "B")})

    result = score_records((prediction,), (gold,), schema_registry)

    _assert_counts(result, tp=2, fp=0, fn=0)


def test_t15_multi_value_partial_overlap_gets_no_partial_tp(
    schema_registry: SchemaRegistry,
) -> None:
    prediction = _record(record_index=0, arguments={"r1": ("A",)})
    gold = _record(record_index=0, arguments={"r1": ("A", "B")})

    result = score_records((prediction,), (gold,), schema_registry)

    _assert_counts(result, tp=0, fp=1, fn=2)


def test_invalid_fp_atoms_are_added_to_total_fp(
    schema_registry: SchemaRegistry,
) -> None:
    invalid_atoms = (
        FPAtom(
            document_id="doc_001",
            line_number=1,
            record_index=0,
            event_type="IllegalEvent",
            role="r1",
            value="illegal event value",
            raw_value="illegal event value",
        ),
        FPAtom(
            document_id="doc_001",
            line_number=1,
            record_index=1,
            event_type="EventA",
            role="illegal_role",
            value="illegal role value",
            raw_value="illegal role value",
        ),
        FPAtom(
            document_id="doc_001",
            line_number=1,
            record_index=2,
            event_type="EventA",
            role="r1",
            value="1000",
            raw_value=1000,
        ),
    )

    result = score_records((), (), schema_registry, invalid_fp_atoms=invalid_atoms)

    _assert_counts(result, tp=0, fp=3, fn=0)
