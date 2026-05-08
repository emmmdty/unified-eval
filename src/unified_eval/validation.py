from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from unified_eval.contracts import CanonicalRoleValue
from unified_eval.schema import SchemaRegistry


@dataclass(frozen=True, slots=True)
class ValidPredictionRecord:
    document_id: str
    line_number: int
    record_index: int
    event_type: str
    arguments: dict[str, CanonicalRoleValue]
    event_id: str | None = None


@dataclass(frozen=True, slots=True)
class InvalidCase:
    code: str
    message: str
    line_number: int
    document_id: str | None = None
    record_index: int | None = None
    event_type: str | None = None
    role: str | None = None
    raw_value: Any = None
    raw_line: str | None = None


@dataclass(frozen=True, slots=True)
class FPAtom:
    document_id: str
    line_number: int
    record_index: int
    event_type: str | None
    role: str | None
    value: str
    raw_value: Any


@dataclass(frozen=True, slots=True)
class DuplicateValueLogEntry:
    document_id: str
    line_number: int
    record_index: int
    event_type: str
    role: str
    value: str
    count: int


@dataclass(frozen=True, slots=True)
class PredictionValidationResult:
    valid_records_for_matching: tuple[ValidPredictionRecord, ...]
    invalid_cases: tuple[InvalidCase, ...]
    illegal_event_fp_atoms: tuple[FPAtom, ...]
    illegal_role_fp_atoms: tuple[FPAtom, ...]
    invalid_value_fp_atoms: tuple[FPAtom, ...]
    duplicate_value_log: tuple[DuplicateValueLogEntry, ...]
    empty_prediction_document_ids: tuple[str, ...]


INVALID_CASE_CSV_FIELDS = (
    "code",
    "message",
    "line_number",
    "document_id",
    "record_index",
    "event_type",
    "role",
    "raw_value_json",
    "raw_line",
)

DUPLICATE_VALUE_LOG_CSV_FIELDS = (
    "duplicate_type",
    "source",
    "document_id",
    "line_number",
    "record_index",
    "event_type",
    "role",
    "value",
    "count",
    "record_json",
)


def validate_prediction_jsonl(
    path: Path | str,
    schema: SchemaRegistry,
    *,
    split_document_ids: Sequence[str] | None = None,
) -> PredictionValidationResult:
    split_order = tuple(split_document_ids or ())
    split_id_set = frozenset(split_order)

    state = _ValidationState()
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            expected_document_id = _expected_document_id_for_line(
                split_order, line_number
            )
            _validate_prediction_line(
                raw_line.rstrip("\n"),
                line_number=line_number,
                expected_document_id=expected_document_id,
                split_id_set=split_id_set,
                schema=schema,
                state=state,
            )

    return state.to_result()


def invalid_cases_to_csv_rows(
    invalid_cases: Sequence[InvalidCase],
) -> list[dict[str, str]]:
    return [
        {
            "code": case.code,
            "message": case.message,
            "line_number": str(case.line_number),
            "document_id": _csv_cell(case.document_id),
            "record_index": _csv_cell(case.record_index),
            "event_type": _csv_cell(case.event_type),
            "role": _csv_cell(case.role),
            "raw_value_json": _raw_json(case.raw_value),
            "raw_line": _csv_cell(case.raw_line),
        }
        for case in invalid_cases
    ]


class _ValidationState:
    def __init__(self) -> None:
        self.valid_records_for_matching: list[ValidPredictionRecord] = []
        self.invalid_cases: list[InvalidCase] = []
        self.illegal_event_fp_atoms: list[FPAtom] = []
        self.illegal_role_fp_atoms: list[FPAtom] = []
        self.invalid_value_fp_atoms: list[FPAtom] = []
        self.duplicate_value_log: list[DuplicateValueLogEntry] = []
        self.empty_prediction_document_ids: list[str] = []

    def to_result(self) -> PredictionValidationResult:
        return PredictionValidationResult(
            valid_records_for_matching=tuple(self.valid_records_for_matching),
            invalid_cases=tuple(self.invalid_cases),
            illegal_event_fp_atoms=tuple(self.illegal_event_fp_atoms),
            illegal_role_fp_atoms=tuple(self.illegal_role_fp_atoms),
            invalid_value_fp_atoms=tuple(self.invalid_value_fp_atoms),
            duplicate_value_log=tuple(self.duplicate_value_log),
            empty_prediction_document_ids=tuple(self.empty_prediction_document_ids),
        )


def _validate_prediction_line(
    raw_line: str,
    *,
    line_number: int,
    expected_document_id: str | None,
    split_id_set: frozenset[str],
    schema: SchemaRegistry,
    state: _ValidationState,
) -> None:
    try:
        payload = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        state.invalid_cases.append(
            InvalidCase(
                code="invalid_json",
                message=str(exc),
                line_number=line_number,
                document_id=expected_document_id,
                raw_line=raw_line,
            )
        )
        if expected_document_id is not None:
            state.empty_prediction_document_ids.append(expected_document_id)
        return

    if not isinstance(payload, dict):
        state.invalid_cases.append(
            InvalidCase(
                code="invalid_document_type",
                message="JSONL line must be an object",
                line_number=line_number,
                document_id=expected_document_id,
                raw_value=payload,
            )
        )
        if expected_document_id is not None:
            state.empty_prediction_document_ids.append(expected_document_id)
        return

    document_id = payload.get("document_id")
    if "document_id" not in payload:
        state.invalid_cases.append(
            InvalidCase(
                code="missing_document_id",
                message="prediction document requires document_id",
                line_number=line_number,
                raw_value=payload,
            )
        )
        return
    if not isinstance(document_id, str):
        state.invalid_cases.append(
            InvalidCase(
                code="invalid_document_id_type",
                message="document_id must be a string",
                line_number=line_number,
                raw_value=document_id,
            )
        )
        return

    if split_id_set and document_id not in split_id_set:
        state.invalid_cases.append(
            InvalidCase(
                code="unknown_document_id",
                message="document_id is not present in the expected split",
                line_number=line_number,
                document_id=document_id,
                raw_value=document_id,
            )
        )
        return

    split = payload.get("split")
    if "split" in payload and split != schema.split:
        state.invalid_cases.append(
            InvalidCase(
                code="split_mismatch",
                message="prediction split does not match the schema split",
                line_number=line_number,
                document_id=document_id,
                raw_value=split,
            )
        )
        return

    if "predictions" not in payload:
        state.invalid_cases.append(
            InvalidCase(
                code="missing_predictions",
                message="prediction document requires predictions",
                line_number=line_number,
                document_id=document_id,
                raw_value=payload,
            )
        )
        state.empty_prediction_document_ids.append(document_id)
        return

    predictions = payload["predictions"]
    if not isinstance(predictions, list):
        state.invalid_cases.append(
            InvalidCase(
                code="invalid_predictions_type",
                message="predictions must be a list",
                line_number=line_number,
                document_id=document_id,
                raw_value=predictions,
            )
        )
        state.empty_prediction_document_ids.append(document_id)
        return

    if not predictions:
        state.empty_prediction_document_ids.append(document_id)
        return

    for record_index, raw_record in enumerate(predictions):
        _validate_prediction_record(
            raw_record,
            line_number=line_number,
            document_id=document_id,
            record_index=record_index,
            schema=schema,
            state=state,
        )


def _validate_prediction_record(
    raw_record: Any,
    *,
    line_number: int,
    document_id: str,
    record_index: int,
    schema: SchemaRegistry,
    state: _ValidationState,
) -> None:
    if not isinstance(raw_record, dict):
        state.invalid_cases.append(
            InvalidCase(
                code="invalid_record_type",
                message="prediction record must be an object",
                line_number=line_number,
                document_id=document_id,
                record_index=record_index,
                raw_value=raw_record,
            )
        )
        return

    event_type = raw_record.get("event_type")
    if "event_type" not in raw_record:
        state.invalid_cases.append(
            _record_case(
                "missing_event_type",
                "prediction record requires event_type",
                line_number,
                document_id,
                record_index,
                raw_value=raw_record,
            )
        )
        return
    if not isinstance(event_type, str):
        state.invalid_cases.append(
            _record_case(
                "invalid_event_type_type",
                "event_type must be a string",
                line_number,
                document_id,
                record_index,
                raw_value=event_type,
            )
        )
        return

    raw_arguments = raw_record.get("arguments")
    if not schema.has_event_type(event_type):
        state.invalid_cases.append(
            _record_case(
                "illegal_event_type",
                "event_type is not legal for the schema",
                line_number,
                document_id,
                record_index,
                event_type=event_type,
                raw_value=event_type,
            )
        )
        if isinstance(raw_arguments, dict):
            _append_fp_atoms_for_arguments(
                state.illegal_event_fp_atoms,
                raw_arguments,
                line_number=line_number,
                document_id=document_id,
                record_index=record_index,
                event_type=event_type,
            )
        return

    event_id = raw_record.get("event_id")
    if "event_id" in raw_record and not isinstance(event_id, str):
        state.invalid_cases.append(
            _record_case(
                "invalid_event_id_type",
                "event_id must be a string when present",
                line_number,
                document_id,
                record_index,
                event_type=event_type,
                raw_value=event_id,
            )
        )
        return

    if "arguments" not in raw_record:
        state.invalid_cases.append(
            _record_case(
                "missing_arguments",
                "prediction record requires arguments",
                line_number,
                document_id,
                record_index,
                event_type=event_type,
                raw_value=raw_record,
            )
        )
        return
    if not isinstance(raw_arguments, dict):
        state.invalid_cases.append(
            _record_case(
                "invalid_arguments_type",
                "arguments must be an object",
                line_number,
                document_id,
                record_index,
                event_type=event_type,
                raw_value=raw_arguments,
            )
        )
        return

    arguments: dict[str, CanonicalRoleValue] = {}
    for role, raw_value in raw_arguments.items():
        if not isinstance(role, str):
            state.invalid_cases.append(
                _record_case(
                    "invalid_role_type",
                    "role key must be a string",
                    line_number,
                    document_id,
                    record_index,
                    event_type=event_type,
                    role=repr(role),
                    raw_value=role,
                )
            )
            _append_fp_atoms_for_value(
                state.illegal_role_fp_atoms,
                raw_value,
                line_number=line_number,
                document_id=document_id,
                record_index=record_index,
                event_type=event_type,
                role=repr(role),
            )
            continue

        if not schema.has_role(event_type, role):
            state.invalid_cases.append(
                _record_case(
                    "illegal_role",
                    "role is not legal for the event type",
                    line_number,
                    document_id,
                    record_index,
                    event_type=event_type,
                    role=role,
                    raw_value=raw_value,
                )
            )
            _append_fp_atoms_for_value(
                state.illegal_role_fp_atoms,
                raw_value,
                line_number=line_number,
                document_id=document_id,
                record_index=record_index,
                event_type=event_type,
                role=role,
            )
            continue

        value = _canonicalize_value(
            raw_value,
            line_number=line_number,
            document_id=document_id,
            record_index=record_index,
            event_type=event_type,
            role=role,
            state=state,
        )
        if value is not _INVALID_VALUE:
            arguments[role] = value

    state.valid_records_for_matching.append(
        ValidPredictionRecord(
            document_id=document_id,
            line_number=line_number,
            record_index=record_index,
            event_type=event_type,
            event_id=event_id,
            arguments=arguments,
        )
    )


_INVALID_VALUE = object()


def _canonicalize_value(
    raw_value: Any,
    *,
    line_number: int,
    document_id: str,
    record_index: int,
    event_type: str,
    role: str,
    state: _ValidationState,
) -> CanonicalRoleValue | object:
    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        value = raw_value.strip()
        if not value:
            state.invalid_cases.append(
                _record_case(
                    "empty_value",
                    "empty role value is ignored for matching",
                    line_number,
                    document_id,
                    record_index,
                    event_type=event_type,
                    role=role,
                    raw_value=raw_value,
                )
            )
            return _INVALID_VALUE
        return value
    if isinstance(raw_value, list) and all(isinstance(item, str) for item in raw_value):
        values: list[str] = []
        for item in raw_value:
            value = item.strip()
            if not value:
                state.invalid_cases.append(
                    _record_case(
                        "empty_value",
                        "empty role value is ignored for matching",
                        line_number,
                        document_id,
                        record_index,
                        event_type=event_type,
                        role=role,
                        raw_value=item,
                    )
                )
                continue
            values.append(value)

        counts = Counter(values)
        for value, count in counts.items():
            if count > 1:
                state.duplicate_value_log.append(
                    DuplicateValueLogEntry(
                        document_id=document_id,
                        line_number=line_number,
                        record_index=record_index,
                        event_type=event_type,
                        role=role,
                        value=value,
                        count=count,
                    )
                )

        unique_values = tuple(dict.fromkeys(values))
        if not unique_values:
            return _INVALID_VALUE
        return unique_values

    state.invalid_cases.append(
        _record_case(
            "invalid_value_type",
            "role value must be a string, list[string], or null",
            line_number,
            document_id,
            record_index,
            event_type=event_type,
            role=role,
            raw_value=raw_value,
        )
    )
    _append_fp_atoms_for_value(
        state.invalid_value_fp_atoms,
        raw_value,
        line_number=line_number,
        document_id=document_id,
        record_index=record_index,
        event_type=event_type,
        role=role,
    )
    return _INVALID_VALUE


def _append_fp_atoms_for_arguments(
    target: list[FPAtom],
    raw_arguments: dict[Any, Any],
    *,
    line_number: int,
    document_id: str,
    record_index: int,
    event_type: str | None,
) -> None:
    for role, raw_value in raw_arguments.items():
        role_name = role if isinstance(role, str) else repr(role)
        _append_fp_atoms_for_value(
            target,
            raw_value,
            line_number=line_number,
            document_id=document_id,
            record_index=record_index,
            event_type=event_type,
            role=role_name,
        )


def _append_fp_atoms_for_value(
    target: list[FPAtom],
    raw_value: Any,
    *,
    line_number: int,
    document_id: str,
    record_index: int,
    event_type: str | None,
    role: str | None,
) -> None:
    for value, atom_raw_value in _extract_non_empty_values(raw_value):
        target.append(
            FPAtom(
                document_id=document_id,
                line_number=line_number,
                record_index=record_index,
                event_type=event_type,
                role=role,
                value=value,
                raw_value=atom_raw_value,
            )
        )


def _extract_non_empty_values(raw_value: Any) -> tuple[tuple[str, Any], ...]:
    if raw_value is None:
        return ()
    if isinstance(raw_value, str):
        value = raw_value.strip()
        return ((value, raw_value),) if value else ()
    if isinstance(raw_value, list):
        values: list[tuple[str, Any]] = []
        for item in raw_value:
            values.extend(_extract_non_empty_values(item))
        return tuple(values)
    if isinstance(raw_value, dict) and not raw_value:
        return ()
    return ((_raw_json(raw_value), raw_value),)


def _expected_document_id_for_line(
    split_document_ids: Sequence[str], line_number: int
) -> str | None:
    index = line_number - 1
    if index < len(split_document_ids):
        return split_document_ids[index]
    return None


def _record_case(
    code: str,
    message: str,
    line_number: int,
    document_id: str,
    record_index: int,
    *,
    event_type: str | None = None,
    role: str | None = None,
    raw_value: Any = None,
) -> InvalidCase:
    return InvalidCase(
        code=code,
        message=message,
        line_number=line_number,
        document_id=document_id,
        record_index=record_index,
        event_type=event_type,
        role=role,
        raw_value=raw_value,
    )


def _raw_json(raw_value: Any) -> str:
    if raw_value is None:
        return ""
    try:
        return json.dumps(raw_value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return repr(raw_value)


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
