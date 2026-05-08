from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from typing import Any

from unified_eval.contracts import (
    CanonicalDocument,
    CanonicalRecord,
    CanonicalRoleValue,
)
from unified_eval.normalization import StrictNormalizer
from unified_eval.schema import SchemaRegistry

MATCHING_LOG_CSV_FIELDS = (
    "document_id",
    "event_type",
    "pred_idx",
    "gold_idx",
    "pair_score",
    "matched",
    "matched_roles",
)

MATCHING_CONFIG_V1: dict[str, Any] = {
    "version": "hungarian_matcher_v1",
    "track": "unified_strict",
    "algorithm": "scipy.optimize.linear_sum_assignment",
    "group_by": ["dataset", "split", "document_id", "event_type"],
    "record_representation": "role_to_frozenset_string",
    "pair_score": "count_schema_roles_with_equal_non_empty_value_sets",
    "zero_score_real_assignment": "unmatched_pred_plus_unmatched_gold",
    "duplicate_records": "preserved",
    "tie_breaking": [
        "maximize_total_pair_score",
        "maximize_exactly_matched_role_value_atoms",
        "minimize_fp_plus_fn",
        "minimize_lexicographic_pred_gold_pair_list",
    ],
}


class HungarianDependencyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FrozenRecord:
    dataset: str
    split: str
    document_id: str
    event_type: str
    record_index: int
    roles_to_values: Mapping[str, Iterable[str]]
    event_id: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.dataset, "dataset")
        _require_nonempty_string(self.split, "split")
        _require_nonempty_string(self.document_id, "document_id")
        _require_nonempty_string(self.event_type, "event_type")
        if not isinstance(self.record_index, int) or self.record_index < 0:
            raise ValueError("record_index must be a non-negative integer")

        frozen_roles: dict[str, frozenset[str]] = {}
        for role, values in self.roles_to_values.items():
            _require_nonempty_string(role, "role")
            raw_values = (values,) if isinstance(values, str) else values
            frozen_values = frozenset(_validated_role_values(raw_values))
            if frozen_values:
                frozen_roles[role] = frozen_values
        object.__setattr__(self, "roles_to_values", frozen_roles)

    @property
    def group_key(self) -> tuple[str, str, str, str]:
        return (self.dataset, self.split, self.document_id, self.event_type)


@dataclass(frozen=True, slots=True)
class MatchedPair:
    dataset: str
    split: str
    document_id: str
    event_type: str
    pred_index: int
    gold_index: int
    pair_score: int
    matched_role_value_atoms: int
    fp_plus_fn: int
    matched_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MatchingLogEntry:
    dataset: str
    split: str
    document_id: str
    event_type: str
    pred_index: int | None
    gold_index: int | None
    pair_score: int
    matched: bool
    matched_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MatchingResult:
    matches: tuple[MatchedPair, ...]
    unmatched_predictions: tuple[FrozenRecord, ...]
    unmatched_golds: tuple[FrozenRecord, ...]
    matching_log: tuple[MatchingLogEntry, ...]
    matching_config_hash: str
    scipy_version: str


@dataclass(frozen=True, slots=True)
class _Edge:
    pair_score: int
    atoms: int
    fp_plus_fn: int
    pair: tuple[int, int] | None
    log_key: tuple[int, int, int, int, tuple[str, ...]] | None


@dataclass(frozen=True, slots=True)
class _Objective:
    pair_score: int
    atoms: int
    fp_plus_fn: int
    pairs: tuple[tuple[int, int], ...]
    log_key: tuple[tuple[int, int, int, int, tuple[str, ...]], ...]
    columns: tuple[int, ...]


def matching_config_hash(config: Mapping[str, Any] = MATCHING_CONFIG_V1) -> str:
    payload = json.dumps(
        config,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def freeze_canonical_documents(
    documents: Sequence[CanonicalDocument],
    *,
    normalizer: StrictNormalizer | None = None,
) -> tuple[FrozenRecord, ...]:
    records: list[FrozenRecord] = []
    for document in documents:
        for record_index, record in enumerate(document.records):
            records.append(
                freeze_canonical_record(
                    document,
                    record,
                    record_index=record_index,
                    normalizer=normalizer,
                )
            )
    return tuple(records)


def freeze_canonical_record(
    document: CanonicalDocument,
    record: CanonicalRecord,
    *,
    record_index: int,
    normalizer: StrictNormalizer | None = None,
) -> FrozenRecord:
    return FrozenRecord(
        dataset=document.dataset,
        split=document.split,
        document_id=document.document_id,
        event_type=record.event_type,
        record_index=record_index,
        event_id=record.event_id,
        roles_to_values=_freeze_arguments(record.arguments, normalizer=normalizer),
    )


def pair_score(
    prediction: FrozenRecord,
    gold: FrozenRecord,
    schema: SchemaRegistry,
) -> int:
    return len(_matched_roles(prediction, gold, schema))


def match_records(
    predictions: Sequence[FrozenRecord],
    golds: Sequence[FrozenRecord],
    schema: SchemaRegistry,
) -> MatchingResult:
    linear_sum_assignment, scipy_version = _load_linear_sum_assignment()

    predictions_by_group = _group_records(predictions)
    golds_by_group = _group_records(golds)

    matches: list[MatchedPair] = []
    unmatched_predictions: list[FrozenRecord] = []
    unmatched_golds: list[FrozenRecord] = []
    matching_log: list[MatchingLogEntry] = []

    for group_key in sorted(predictions_by_group.keys() | golds_by_group.keys()):
        group_predictions = tuple(
            sorted(predictions_by_group[group_key], key=_record_sort_key)
        )
        group_golds = tuple(sorted(golds_by_group[group_key], key=_record_sort_key))
        group_result = _match_group(
            group_predictions,
            group_golds,
            schema,
            linear_sum_assignment=linear_sum_assignment,
        )
        matches.extend(group_result.matches)
        unmatched_predictions.extend(group_result.unmatched_predictions)
        unmatched_golds.extend(group_result.unmatched_golds)
        matching_log.extend(group_result.matching_log)

    return MatchingResult(
        matches=tuple(sorted(matches, key=_matched_pair_sort_key)),
        unmatched_predictions=tuple(
            sorted(unmatched_predictions, key=_record_sort_key)
        ),
        unmatched_golds=tuple(sorted(unmatched_golds, key=_record_sort_key)),
        matching_log=tuple(sorted(matching_log, key=_log_entry_sort_key)),
        matching_config_hash=matching_config_hash(),
        scipy_version=scipy_version,
    )


def matching_log_to_csv_rows(
    entries: Sequence[MatchingLogEntry],
) -> list[dict[str, str]]:
    return [
        {
            "document_id": entry.document_id,
            "event_type": entry.event_type,
            "pred_idx": _csv_index(entry.pred_index),
            "gold_idx": _csv_index(entry.gold_index),
            "pair_score": str(entry.pair_score),
            "matched": "true" if entry.matched else "false",
            "matched_roles": json.dumps(
                list(entry.matched_roles),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        }
        for entry in entries
    ]


def _match_group(
    predictions: tuple[FrozenRecord, ...],
    golds: tuple[FrozenRecord, ...],
    schema: SchemaRegistry,
    *,
    linear_sum_assignment: Any,
) -> MatchingResult:
    if not predictions and not golds:
        return _empty_result()
    if not predictions:
        return _gold_only_group(golds)
    if not golds:
        return _prediction_only_group(predictions)

    hungarian_columns = _run_protocol_hungarian(
        predictions, golds, schema, linear_sum_assignment
    )
    columns = _resolve_deterministic_assignment(predictions, golds, schema)
    if _assignment_pair_score(columns, predictions, golds, schema) != (
        _assignment_pair_score(hungarian_columns, predictions, golds, schema)
    ):
        raise RuntimeError("deterministic tie resolution changed Hungarian score")

    matches: list[MatchedPair] = []
    unmatched_predictions: list[FrozenRecord] = []
    unmatched_golds: list[FrozenRecord] = []
    matching_log: list[MatchingLogEntry] = []

    group = predictions[0].group_key
    pred_count = len(predictions)
    gold_count = len(golds)
    for row_index, column_index in enumerate(columns):
        if row_index < pred_count and column_index < gold_count:
            prediction = predictions[row_index]
            gold = golds[column_index]
            score = pair_score(prediction, gold, schema)
            roles = _matched_roles(prediction, gold, schema)
            atoms = _matched_role_value_atoms(prediction, gold, schema)
            if score > 0:
                matches.append(
                    MatchedPair(
                        dataset=prediction.dataset,
                        split=prediction.split,
                        document_id=prediction.document_id,
                        event_type=prediction.event_type,
                        pred_index=prediction.record_index,
                        gold_index=gold.record_index,
                        pair_score=score,
                        matched_role_value_atoms=atoms,
                        fp_plus_fn=_pair_fp_plus_fn(prediction, gold, schema),
                        matched_roles=roles,
                    )
                )
                matching_log.append(
                    _log_entry(
                        group,
                        prediction.record_index,
                        gold.record_index,
                        score,
                        True,
                        roles,
                    )
                )
            else:
                unmatched_predictions.append(prediction)
                unmatched_golds.append(gold)
                matching_log.append(
                    _log_entry(
                        group, prediction.record_index, gold.record_index, 0, False, ()
                    )
                )
        elif row_index < pred_count:
            prediction = predictions[row_index]
            unmatched_predictions.append(prediction)
            matching_log.append(
                _log_entry(group, prediction.record_index, None, 0, False, ())
            )
        elif column_index < gold_count:
            gold = golds[column_index]
            unmatched_golds.append(gold)
            matching_log.append(
                _log_entry(group, None, gold.record_index, 0, False, ())
            )

    return MatchingResult(
        matches=tuple(matches),
        unmatched_predictions=tuple(unmatched_predictions),
        unmatched_golds=tuple(unmatched_golds),
        matching_log=tuple(matching_log),
        matching_config_hash=matching_config_hash(),
        scipy_version=_scipy_version(),
    )


def _resolve_deterministic_assignment(
    predictions: tuple[FrozenRecord, ...],
    golds: tuple[FrozenRecord, ...],
    schema: SchemaRegistry,
) -> tuple[int, ...]:
    size = max(len(predictions), len(golds))
    edges = tuple(
        tuple(
            _edge_summary(row_index, column_index, predictions, golds, schema)
            for column_index in range(size)
        )
        for row_index in range(size)
    )

    @cache
    def best(row_index: int, used_columns: int) -> _Objective:
        if row_index == size:
            return _Objective(0, 0, 0, (), (), ())

        current_best: _Objective | None = None
        for column_index in range(size):
            column_mask = 1 << column_index
            if used_columns & column_mask:
                continue
            edge = edges[row_index][column_index]
            child = best(row_index + 1, used_columns | column_mask)
            pairs = child.pairs
            if edge.pair is not None:
                pairs = tuple(sorted((*pairs, edge.pair)))
            log_key = child.log_key
            if edge.log_key is not None:
                log_key = tuple(sorted((*log_key, edge.log_key)))
            candidate = _Objective(
                pair_score=edge.pair_score + child.pair_score,
                atoms=edge.atoms + child.atoms,
                fp_plus_fn=edge.fp_plus_fn + child.fp_plus_fn,
                pairs=pairs,
                log_key=log_key,
                columns=(column_index, *child.columns),
            )
            if current_best is None or _is_better(candidate, current_best):
                current_best = candidate

        if current_best is None:
            raise RuntimeError("failed to resolve deterministic Hungarian assignment")
        return current_best

    return best(0, 0).columns


def _edge_summary(
    row_index: int,
    column_index: int,
    predictions: tuple[FrozenRecord, ...],
    golds: tuple[FrozenRecord, ...],
    schema: SchemaRegistry,
) -> _Edge:
    pred_count = len(predictions)
    gold_count = len(golds)
    if row_index < pred_count and column_index < gold_count:
        prediction = predictions[row_index]
        gold = golds[column_index]
        score = pair_score(prediction, gold, schema)
        roles = _matched_roles(prediction, gold, schema)
        atoms = _matched_role_value_atoms(prediction, gold, schema)
        if score > 0:
            fp_plus_fn = _pair_fp_plus_fn(prediction, gold, schema)
            pair = (prediction.record_index, gold.record_index)
        else:
            fp_plus_fn = _record_atom_count(prediction, schema) + _record_atom_count(
                gold, schema
            )
            pair = None
        return _Edge(
            pair_score=score,
            atoms=atoms if score > 0 else 0,
            fp_plus_fn=fp_plus_fn,
            pair=pair,
            log_key=_edge_log_key(
                prediction.record_index,
                gold.record_index,
                score,
                score > 0,
                roles if score > 0 else (),
            ),
        )

    if row_index < pred_count:
        prediction = predictions[row_index]
        return _Edge(
            pair_score=0,
            atoms=0,
            fp_plus_fn=_record_atom_count(prediction, schema),
            pair=None,
            log_key=_edge_log_key(prediction.record_index, None, 0, False, ()),
        )

    if column_index < gold_count:
        gold = golds[column_index]
        return _Edge(
            pair_score=0,
            atoms=0,
            fp_plus_fn=_record_atom_count(gold, schema),
            pair=None,
            log_key=_edge_log_key(None, gold.record_index, 0, False, ()),
        )

    return _Edge(0, 0, 0, None, None)


def _run_protocol_hungarian(
    predictions: tuple[FrozenRecord, ...],
    golds: tuple[FrozenRecord, ...],
    schema: SchemaRegistry,
    linear_sum_assignment: Any,
) -> tuple[int, ...]:
    size = max(len(predictions), len(golds))
    score_matrix = [[0 for _ in range(size)] for _ in range(size)]
    for pred_index, prediction in enumerate(predictions):
        for gold_index, gold in enumerate(golds):
            score_matrix[pred_index][gold_index] = pair_score(prediction, gold, schema)
    row_indexes, column_indexes = linear_sum_assignment(
        [[-score for score in row] for row in score_matrix]
    )
    return tuple(
        column_index
        for _, column_index in sorted(zip(row_indexes, column_indexes, strict=True))
    )


def _assignment_pair_score(
    columns: tuple[int, ...],
    predictions: tuple[FrozenRecord, ...],
    golds: tuple[FrozenRecord, ...],
    schema: SchemaRegistry,
) -> int:
    return sum(
        pair_score(predictions[row_index], golds[column_index], schema)
        for row_index, column_index in enumerate(columns)
        if row_index < len(predictions) and column_index < len(golds)
    )


def _matched_roles(
    prediction: FrozenRecord,
    gold: FrozenRecord,
    schema: SchemaRegistry,
) -> tuple[str, ...]:
    if prediction.group_key != gold.group_key:
        return ()
    return tuple(
        role
        for role in sorted(schema.legal_roles(prediction.event_type))
        if prediction.roles_to_values.get(role, frozenset())
        == gold.roles_to_values.get(role, frozenset())
        and prediction.roles_to_values.get(role, frozenset())
    )


def _matched_role_value_atoms(
    prediction: FrozenRecord,
    gold: FrozenRecord,
    schema: SchemaRegistry,
) -> int:
    return sum(
        len(prediction.roles_to_values[role])
        for role in _matched_roles(prediction, gold, schema)
    )


def _pair_fp_plus_fn(
    prediction: FrozenRecord,
    gold: FrozenRecord,
    schema: SchemaRegistry,
) -> int:
    fp_plus_fn = 0
    for role in schema.legal_roles(prediction.event_type):
        predicted_values = prediction.roles_to_values.get(role, frozenset())
        gold_values = gold.roles_to_values.get(role, frozenset())
        if not predicted_values and not gold_values:
            continue
        if predicted_values == gold_values:
            continue
        fp_plus_fn += len(predicted_values) + len(gold_values)
    return fp_plus_fn


def _record_atom_count(record: FrozenRecord, schema: SchemaRegistry) -> int:
    return sum(
        len(record.roles_to_values.get(role, frozenset()))
        for role in schema.legal_roles(record.event_type)
    )


def _freeze_arguments(
    arguments: Mapping[str, CanonicalRoleValue],
    *,
    normalizer: StrictNormalizer | None,
) -> dict[str, frozenset[str]]:
    frozen: dict[str, frozenset[str]] = {}
    for role, raw_value in arguments.items():
        values = _role_value_to_strings(raw_value, normalizer=normalizer)
        if values:
            frozen[role] = frozenset(values)
    return frozen


def _role_value_to_strings(
    value: CanonicalRoleValue,
    *,
    normalizer: StrictNormalizer | None,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        normalized = _normalize_string(value, normalizer=normalizer)
        return (normalized,) if normalized else ()

    normalized_values: list[str] = []
    for item in value:
        normalized = _normalize_string(item, normalizer=normalizer)
        if normalized:
            normalized_values.append(normalized)
    return tuple(normalized_values)


def _normalize_string(value: str, *, normalizer: StrictNormalizer | None) -> str:
    if normalizer is None:
        return value
    return normalizer.normalize(value).normalized_value


def _is_better(candidate: _Objective, incumbent: _Objective) -> bool:
    if candidate.pair_score != incumbent.pair_score:
        return candidate.pair_score > incumbent.pair_score
    if candidate.atoms != incumbent.atoms:
        return candidate.atoms > incumbent.atoms
    if candidate.fp_plus_fn != incumbent.fp_plus_fn:
        return candidate.fp_plus_fn < incumbent.fp_plus_fn
    if candidate.pairs != incumbent.pairs:
        return candidate.pairs < incumbent.pairs
    return candidate.log_key < incumbent.log_key


def _group_records(
    records: Sequence[FrozenRecord],
) -> defaultdict[tuple[str, str, str, str], list[FrozenRecord]]:
    grouped: defaultdict[tuple[str, str, str, str], list[FrozenRecord]] = defaultdict(
        list
    )
    for record in records:
        grouped[record.group_key].append(record)
    return grouped


def _prediction_only_group(predictions: tuple[FrozenRecord, ...]) -> MatchingResult:
    matching_log = tuple(
        _log_entry(record.group_key, record.record_index, None, 0, False, ())
        for record in predictions
    )
    return MatchingResult(
        matches=(),
        unmatched_predictions=predictions,
        unmatched_golds=(),
        matching_log=matching_log,
        matching_config_hash=matching_config_hash(),
        scipy_version=_scipy_version(),
    )


def _gold_only_group(golds: tuple[FrozenRecord, ...]) -> MatchingResult:
    matching_log = tuple(
        _log_entry(record.group_key, None, record.record_index, 0, False, ())
        for record in golds
    )
    return MatchingResult(
        matches=(),
        unmatched_predictions=(),
        unmatched_golds=golds,
        matching_log=matching_log,
        matching_config_hash=matching_config_hash(),
        scipy_version=_scipy_version(),
    )


def _empty_result() -> MatchingResult:
    return MatchingResult(
        matches=(),
        unmatched_predictions=(),
        unmatched_golds=(),
        matching_log=(),
        matching_config_hash=matching_config_hash(),
        scipy_version=_scipy_version(),
    )


def _log_entry(
    group_key: tuple[str, str, str, str],
    pred_index: int | None,
    gold_index: int | None,
    pair_score_value: int,
    matched: bool,
    matched_roles: tuple[str, ...],
) -> MatchingLogEntry:
    dataset, split, document_id, event_type = group_key
    return MatchingLogEntry(
        dataset=dataset,
        split=split,
        document_id=document_id,
        event_type=event_type,
        pred_index=pred_index,
        gold_index=gold_index,
        pair_score=pair_score_value,
        matched=matched,
        matched_roles=matched_roles,
    )


def _edge_log_key(
    pred_index: int | None,
    gold_index: int | None,
    pair_score_value: int,
    matched: bool,
    matched_roles: tuple[str, ...],
) -> tuple[int, int, int, int, tuple[str, ...]]:
    return (
        pred_index if pred_index is not None else -1,
        gold_index if gold_index is not None else -1,
        -pair_score_value,
        0 if matched else 1,
        matched_roles,
    )


def _record_sort_key(record: FrozenRecord) -> tuple[str, str, str, str, int]:
    return (*record.group_key, record.record_index)


def _matched_pair_sort_key(pair: MatchedPair) -> tuple[str, str, str, str, int, int]:
    return (
        pair.dataset,
        pair.split,
        pair.document_id,
        pair.event_type,
        pair.pred_index,
        pair.gold_index,
    )


def _log_entry_sort_key(
    entry: MatchingLogEntry,
) -> tuple[str, str, str, str, int, int, int, int]:
    return (
        entry.dataset,
        entry.split,
        entry.document_id,
        entry.event_type,
        1 if entry.pred_index is None else 0,
        entry.pred_index if entry.pred_index is not None else -1,
        1 if entry.gold_index is None else 0,
        entry.gold_index if entry.gold_index is not None else -1,
    )


def _csv_index(index: int | None) -> str:
    return "" if index is None else str(index)


def _load_linear_sum_assignment() -> tuple[Any, str]:
    try:
        optimize = importlib.import_module("scipy.optimize")
        linear_sum_assignment = optimize.linear_sum_assignment
    except (AttributeError, ModuleNotFoundError) as exc:
        raise HungarianDependencyError(
            "protocol-v1 matching requires scipy.optimize.linear_sum_assignment; "
            "install the project dependencies with uv sync"
        ) from exc
    return linear_sum_assignment, _scipy_version()


def _scipy_version() -> str:
    try:
        return importlib.metadata.version("scipy")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _require_nonempty_string(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")


def _validated_role_values(values: Iterable[str]) -> Iterable[str]:
    for value in values:
        if not isinstance(value, str):
            raise ValueError("role values must be strings")
        if value:
            yield value
