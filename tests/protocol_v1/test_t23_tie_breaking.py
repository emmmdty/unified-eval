from __future__ import annotations

from unified_eval.matching import FrozenRecord, match_records, matching_log_to_csv_rows
from unified_eval.schema import SchemaRegistry


def _schema_registry() -> SchemaRegistry:
    return SchemaRegistry(
        dataset="ToyDEE",
        split="dev",
        event_roles={
            "EquityFreeze": frozenset({"shareholder", "amount"}),
        },
        schema_hash="sha256:schema",
        split_hash="sha256:split",
    )


def _record(
    *,
    record_index: int,
    arguments: dict[str, str | tuple[str, ...]],
) -> FrozenRecord:
    return FrozenRecord(
        dataset="ToyDEE",
        split="dev",
        document_id="doc_001",
        event_type="EquityFreeze",
        record_index=record_index,
        roles_to_values={
            role: frozenset((value,) if isinstance(value, str) else value)
            for role, value in arguments.items()
        },
    )


def test_t23_tie_breaking_maximizes_exactly_matched_atoms_before_lex_order() -> None:
    schema = _schema_registry()
    predictions = (
        _record(
            record_index=0, arguments={"shareholder": ("张三", "李四"), "amount": "A"}
        ),
        _record(record_index=1, arguments={"shareholder": "王五", "amount": "B"}),
    )
    golds = (
        _record(
            record_index=0, arguments={"shareholder": ("张三", "李四"), "amount": "B"}
        ),
        _record(record_index=1, arguments={"shareholder": "王五", "amount": "A"}),
    )

    result = match_records(predictions, golds, schema)

    assert [(match.pred_index, match.gold_index) for match in result.matches] == [
        (0, 0),
        (1, 1),
    ]
    assert [match.matched_role_value_atoms for match in result.matches] == [2, 1]


def test_t23_tie_breaking_uses_lexicographic_pair_list_as_final_rule() -> None:
    schema = _schema_registry()
    predictions = (
        _record(record_index=0, arguments={"shareholder": "张三"}),
        _record(record_index=1, arguments={"shareholder": "王五"}),
    )
    golds = (
        _record(record_index=0, arguments={"shareholder": "张三"}),
        _record(record_index=1, arguments={"shareholder": "张三"}),
    )

    result = match_records(predictions, golds, schema)

    assert [(match.pred_index, match.gold_index) for match in result.matches] == [
        (0, 0)
    ]
    assert [record.record_index for record in result.unmatched_golds] == [1]


def test_t23_repeated_runs_produce_identical_matching_log_and_config_hash() -> None:
    schema = _schema_registry()
    predictions = (
        _record(record_index=0, arguments={"shareholder": "张三"}),
        _record(record_index=1, arguments={"shareholder": "王五"}),
    )
    golds = (
        _record(record_index=0, arguments={"shareholder": "张三"}),
        _record(record_index=1, arguments={"shareholder": "张三"}),
    )

    first = match_records(predictions, golds, schema)
    second = match_records(predictions, golds, schema)

    assert matching_log_to_csv_rows(first.matching_log) == matching_log_to_csv_rows(
        second.matching_log
    )
    assert first.matching_config_hash.startswith("sha256:")
    assert first.matching_config_hash == second.matching_config_hash
