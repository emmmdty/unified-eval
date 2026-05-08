from __future__ import annotations

import json
from pathlib import Path

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
            "EventA": frozenset({"r1", "r2", "r3"}),
            "EventB": frozenset({"b1"}),
        },
        schema_hash="sha256:schema",
        split_hash="sha256:split",
    )


def _record(
    *,
    record_index: int,
    event_type: str,
    document_id: str,
    arguments: dict[str, str | tuple[str, ...]],
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


def test_t25_unified_regression_matches_golden_counts_and_micro_metrics(
    schema_registry: SchemaRegistry,
) -> None:
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
        predictions,
        golds,
        schema_registry,
        invalid_fp_atoms=invalid_atoms,
    )
    golden_path = (
        Path(__file__).parents[1]
        / "fixtures"
        / "protocol_v1"
        / "t25_unified_regression_golden.json"
    )
    golden = json.loads(golden_path.read_text(encoding="utf-8"))

    assert result.true_positives == golden["true_positives"]
    assert result.false_positives == golden["false_positives"]
    assert result.false_negatives == golden["false_negatives"]
    assert result.precision == pytest.approx(golden["precision"])
    assert result.recall == pytest.approx(golden["recall"])
    assert result.f1 == pytest.approx(golden["f1"])
