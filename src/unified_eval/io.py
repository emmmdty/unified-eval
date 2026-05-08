from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_eval.contracts import (
    CanonicalDocument,
    CanonicalRecord,
    CanonicalRoleValue,
    ContractValidationError,
    RecordsField,
    ValidationIssue,
)
from unified_eval.schema import SchemaRegistry


def read_prediction_jsonl(
    path: Path | str, schema: SchemaRegistry
) -> list[CanonicalDocument]:
    return _read_jsonl(path, schema, records_field="predictions")


def read_gold_jsonl(
    path: Path | str, schema: SchemaRegistry
) -> list[CanonicalDocument]:
    return _read_jsonl(path, schema, records_field="gold_events")


def _read_jsonl(
    path: Path | str, schema: SchemaRegistry, *, records_field: RecordsField
) -> list[CanonicalDocument]:
    documents: list[CanonicalDocument] = []
    issues: list[ValidationIssue] = []

    with Path(path).open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                issues.append(
                    ValidationIssue(
                        code="invalid_json",
                        message=str(exc),
                        line_number=line_number,
                        raw_value=raw_line.rstrip("\n"),
                    )
                )
                continue

            document, document_issues = _parse_document(
                payload,
                schema,
                records_field=records_field,
                line_number=line_number,
            )
            issues.extend(document_issues)
            if document is not None:
                documents.append(document)

    if issues:
        raise ContractValidationError(issues)
    return documents


def _parse_document(
    payload: Any,
    schema: SchemaRegistry,
    *,
    records_field: RecordsField,
    line_number: int,
) -> tuple[CanonicalDocument | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    if not isinstance(payload, dict):
        return None, [
            ValidationIssue(
                code="invalid_document_type",
                message="JSONL line must be an object",
                line_number=line_number,
                raw_value=payload,
            )
        ]

    document_id = payload.get("document_id")
    if "document_id" not in payload:
        return None, [
            ValidationIssue(
                code="missing_document_id",
                message=(
                    "canonical input requires document_id; "
                    "legacy doc_id is not accepted"
                ),
                line_number=line_number,
                raw_value=payload,
            )
        ]
    if not isinstance(document_id, str):
        return None, [
            ValidationIssue(
                code="invalid_document_id_type",
                message="document_id must be a string",
                line_number=line_number,
                raw_value=document_id,
            )
        ]

    if records_field not in payload:
        return None, [
            ValidationIssue(
                code=f"missing_{records_field}",
                message=f"canonical input requires {records_field}",
                line_number=line_number,
                document_id=document_id,
                raw_value=payload,
            )
        ]

    raw_records = payload[records_field]
    if not isinstance(raw_records, list):
        return None, [
            ValidationIssue(
                code=f"invalid_{records_field}_type",
                message=f"{records_field} must be a list",
                line_number=line_number,
                document_id=document_id,
                raw_value=raw_records,
            )
        ]

    records: list[CanonicalRecord] = []
    for record_index, raw_record in enumerate(raw_records):
        record, record_issues = _parse_record(
            raw_record,
            schema,
            line_number=line_number,
            document_id=document_id,
            record_index=record_index,
        )
        issues.extend(record_issues)
        if record is not None:
            records.append(record)

    if issues:
        return None, issues

    return (
        CanonicalDocument(
            dataset=schema.dataset,
            split=schema.split,
            document_id=document_id,
            records_field=records_field,
            records=tuple(records),
        ),
        [],
    )


def _parse_record(
    raw_record: Any,
    schema: SchemaRegistry,
    *,
    line_number: int,
    document_id: str,
    record_index: int,
) -> tuple[CanonicalRecord | None, list[ValidationIssue]]:
    if not isinstance(raw_record, dict):
        return None, [
            ValidationIssue(
                code="invalid_record_type",
                message="record must be an object",
                line_number=line_number,
                document_id=document_id,
                record_index=record_index,
                raw_value=raw_record,
            )
        ]

    event_type = raw_record.get("event_type")
    if "event_type" not in raw_record:
        return None, [
            _record_issue(
                "missing_event_type",
                "record requires event_type",
                line_number,
                document_id,
                record_index,
                raw_value=raw_record,
            )
        ]
    if not isinstance(event_type, str):
        return None, [
            _record_issue(
                "invalid_event_type_type",
                "event_type must be a string",
                line_number,
                document_id,
                record_index,
                raw_value=event_type,
            )
        ]
    if not schema.has_event_type(event_type):
        return None, [
            _record_issue(
                "illegal_event_type",
                "event_type is not legal for the schema",
                line_number,
                document_id,
                record_index,
                event_type=event_type,
                raw_value=event_type,
            )
        ]

    event_id = raw_record.get("event_id")
    if "event_id" in raw_record and not isinstance(event_id, str):
        return None, [
            _record_issue(
                "invalid_event_id_type",
                "event_id must be a string when present",
                line_number,
                document_id,
                record_index,
                event_type=event_type,
                raw_value=event_id,
            )
        ]

    raw_arguments = raw_record.get("arguments")
    if "arguments" not in raw_record:
        return None, [
            _record_issue(
                "missing_arguments",
                "record requires arguments",
                line_number,
                document_id,
                record_index,
                event_type=event_type,
                raw_value=raw_record,
            )
        ]
    if not isinstance(raw_arguments, dict):
        return None, [
            _record_issue(
                "invalid_arguments_type",
                "arguments must be an object",
                line_number,
                document_id,
                record_index,
                event_type=event_type,
                raw_value=raw_arguments,
            )
        ]

    arguments: dict[str, CanonicalRoleValue] = {}
    issues: list[ValidationIssue] = []
    for role, raw_value in raw_arguments.items():
        if not isinstance(role, str):
            issues.append(
                _record_issue(
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
            continue
        if not schema.has_role(event_type, role):
            issues.append(
                _record_issue(
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
            continue

        value, value_issue = _canonicalize_role_value(
            raw_value,
            line_number=line_number,
            document_id=document_id,
            record_index=record_index,
            event_type=event_type,
            role=role,
        )
        if value_issue is not None:
            issues.append(value_issue)
            continue
        arguments[role] = value

    if issues:
        return None, issues

    return (
        CanonicalRecord(
            event_type=event_type,
            event_id=event_id,
            arguments=arguments,
        ),
        [],
    )


def _canonicalize_role_value(
    raw_value: Any,
    *,
    line_number: int,
    document_id: str,
    record_index: int,
    event_type: str,
    role: str,
) -> tuple[CanonicalRoleValue, ValidationIssue | None]:
    if raw_value is None:
        return None, None
    if isinstance(raw_value, str):
        return raw_value, None
    if isinstance(raw_value, list) and all(isinstance(item, str) for item in raw_value):
        return tuple(raw_value), None

    return (
        None,
        _record_issue(
            "invalid_value_type",
            "role value must be a string, list[string], or null",
            line_number,
            document_id,
            record_index,
            event_type=event_type,
            role=role,
            raw_value=raw_value,
        ),
    )


def _record_issue(
    code: str,
    message: str,
    line_number: int,
    document_id: str,
    record_index: int,
    *,
    event_type: str | None = None,
    role: str | None = None,
    raw_value: Any = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        line_number=line_number,
        document_id=document_id,
        record_index=record_index,
        event_type=event_type,
        role=role,
        raw_value=raw_value,
    )
