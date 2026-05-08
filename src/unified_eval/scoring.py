from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from unified_eval.matching import FrozenRecord, MatchingResult, match_records
from unified_eval.schema import SchemaRegistry


@dataclass(frozen=True, slots=True)
class ScoreCounts:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    def add(self, other: ScoreCounts) -> ScoreCounts:
        return ScoreCounts(
            true_positives=self.true_positives + other.true_positives,
            false_positives=self.false_positives + other.false_positives,
            false_negatives=self.false_negatives + other.false_negatives,
        )


@dataclass(frozen=True, slots=True)
class ScoringResult:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    matching_result: MatchingResult


def score_records(
    predictions: Sequence[FrozenRecord],
    golds: Sequence[FrozenRecord],
    schema: SchemaRegistry,
    *,
    invalid_fp_atoms: Sequence[Any] = (),
) -> ScoringResult:
    matching_result = match_records(predictions, golds, schema)
    return score_matching_result(
        matching_result,
        predictions,
        golds,
        schema,
        invalid_fp_atoms=invalid_fp_atoms,
    )


def score_matching_result(
    matching_result: MatchingResult,
    predictions: Sequence[FrozenRecord],
    golds: Sequence[FrozenRecord],
    schema: SchemaRegistry,
    *,
    invalid_fp_atoms: Sequence[Any] = (),
) -> ScoringResult:
    prediction_map = _records_by_match_key(predictions)
    gold_map = _records_by_match_key(golds)

    counts = ScoreCounts(false_positives=len(invalid_fp_atoms))

    for match in matching_result.matches:
        prediction = prediction_map[
            (
                match.dataset,
                match.split,
                match.document_id,
                match.event_type,
                match.pred_index,
            )
        ]
        gold = gold_map[
            (
                match.dataset,
                match.split,
                match.document_id,
                match.event_type,
                match.gold_index,
            )
        ]
        counts = counts.add(_score_matched_pair(prediction, gold, schema))

    for prediction in matching_result.unmatched_predictions:
        counts = counts.add(
            ScoreCounts(false_positives=_legal_role_value_count(prediction, schema))
        )

    for gold in matching_result.unmatched_golds:
        counts = counts.add(
            ScoreCounts(false_negatives=_legal_role_value_count(gold, schema))
        )

    precision = _safe_divide(
        counts.true_positives,
        counts.true_positives + counts.false_positives,
    )
    recall = _safe_divide(
        counts.true_positives,
        counts.true_positives + counts.false_negatives,
    )
    f1 = _safe_divide(2 * precision * recall, precision + recall)

    return ScoringResult(
        true_positives=counts.true_positives,
        false_positives=counts.false_positives,
        false_negatives=counts.false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
        matching_result=matching_result,
    )


def _score_matched_pair(
    prediction: FrozenRecord,
    gold: FrozenRecord,
    schema: SchemaRegistry,
) -> ScoreCounts:
    counts = ScoreCounts()
    for role in schema.legal_roles(gold.event_type):
        predicted_values = prediction.roles_to_values.get(role, frozenset())
        gold_values = gold.roles_to_values.get(role, frozenset())

        if not predicted_values and not gold_values:
            continue
        if predicted_values == gold_values:
            counts = counts.add(ScoreCounts(true_positives=len(gold_values)))
            continue
        if not predicted_values:
            counts = counts.add(ScoreCounts(false_negatives=len(gold_values)))
            continue
        if not gold_values:
            counts = counts.add(ScoreCounts(false_positives=len(predicted_values)))
            continue
        counts = counts.add(
            ScoreCounts(
                false_positives=len(predicted_values),
                false_negatives=len(gold_values),
            )
        )
    return counts


def _legal_role_value_count(record: FrozenRecord, schema: SchemaRegistry) -> int:
    return sum(
        len(record.roles_to_values.get(role, frozenset()))
        for role in schema.legal_roles(record.event_type)
    )


def _records_by_match_key(
    records: Sequence[FrozenRecord],
) -> dict[tuple[str, str, str, str, int], FrozenRecord]:
    records_by_key: dict[tuple[str, str, str, str, int], FrozenRecord] = {}
    for record in records:
        key = (*record.group_key, record.record_index)
        if key in records_by_key:
            raise ValueError(f"duplicate record match key: {key}")
        records_by_key[key] = record
    return records_by_key


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
