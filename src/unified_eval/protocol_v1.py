from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from unified_eval.contracts import (
    CanonicalDocument,
    CanonicalRecord,
    CanonicalRoleValue,
    ContractValidationError,
    ValidationIssue,
)
from unified_eval.data_snapshot import sha256_file
from unified_eval.io import read_gold_jsonl
from unified_eval.matching import FrozenRecord
from unified_eval.normalization import (
    NormalizationLogEntry,
    StrictNormalizer,
)
from unified_eval.reporting import ReportArtifactInput, write_report_artifacts
from unified_eval.schema import SchemaRegistry
from unified_eval.scoring import score_records
from unified_eval.validation import (
    FPAtom,
    PredictionValidationResult,
    ValidPredictionRecord,
    validate_prediction_jsonl,
)

DEFAULT_NORMALIZER_CONFIG = Path("configs/strict_normalizer_v1.json")
EVALUATOR_VERSION = "protocol-v1"


class ProtocolCliError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LoadedSchema:
    registry: SchemaRegistry
    schema_version: str
    split_version: str


@dataclass(frozen=True, slots=True)
class FrozenWithLogs:
    records: tuple[FrozenRecord, ...]
    normalization_logs: tuple[NormalizationLogEntry, ...]


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        run_evaluation(args)
    except ProtocolCliError as exc:
        parser.exit(2, f"protocol-v1: error: {exc}\n")
    except ContractValidationError as exc:
        parser.exit(2, _format_contract_error(exc))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m unified_eval.protocol_v1",
        description="Run protocol-v1 unified strict DEE evaluation.",
    )
    parser.add_argument("--dataset", required=True, help="Explicit dataset name.")
    parser.add_argument("--split", required=True, help="Explicit split name.")
    parser.add_argument(
        "--schema",
        required=True,
        type=Path,
        help="Explicit protocol schema JSON path.",
    )
    parser.add_argument(
        "--gold",
        required=True,
        type=Path,
        help="Explicit gold JSONL path.",
    )
    parser.add_argument(
        "--pred",
        required=True,
        type=Path,
        help="Explicit canonical prediction JSONL path.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory for required protocol-v1 artifacts.",
    )
    parser.add_argument(
        "--normalizer-config",
        type=Path,
        default=DEFAULT_NORMALIZER_CONFIG,
        help="Strict normalizer config path.",
    )
    return parser


def run_evaluation(args: argparse.Namespace) -> dict[str, Path]:
    _require_file(args.schema, "--schema")
    _require_file(args.gold, "--gold")
    _require_file(args.pred, "--pred")
    _require_file(args.normalizer_config, "--normalizer-config")

    loaded_schema = load_schema(
        args.schema,
        dataset=args.dataset,
        split=args.split,
        split_hash="sha256:" + sha256_file(args.gold),
    )
    normalizer_config = _read_json_object(args.normalizer_config, "--normalizer-config")
    normalizer = StrictNormalizer.from_config(normalizer_config)

    gold_documents = read_protocol_gold_jsonl(
        args.gold,
        loaded_schema.registry,
        dataset=args.dataset,
        split=args.split,
    )
    gold_document_ids = tuple(document.document_id for document in gold_documents)
    gold = freeze_documents_with_logs(gold_documents, normalizer=normalizer)

    validation = validate_prediction_jsonl(
        args.pred,
        loaded_schema.registry,
        split_document_ids=gold_document_ids,
    )
    predictions = freeze_valid_predictions_with_logs(
        validation.valid_records_for_matching,
        loaded_schema.registry,
        normalizer=normalizer,
    )
    invalid_fp_atoms = _invalid_fp_atoms(validation)

    scoring_result = score_records(
        predictions.records,
        gold.records,
        loaded_schema.registry,
        invalid_fp_atoms=invalid_fp_atoms,
    )
    artifacts = write_report_artifacts(
        args.output_dir,
        ReportArtifactInput(
            schema=loaded_schema.registry,
            schema_version=loaded_schema.schema_version,
            split_version=loaded_schema.split_version,
            evaluator_version=EVALUATOR_VERSION,
            scoring_result=scoring_result,
            predictions=predictions.records,
            golds=gold.records,
            normalizer_config=normalizer_config,
            normalization_logs=(
                *gold.normalization_logs,
                *predictions.normalization_logs,
            ),
            invalid_cases=validation.invalid_cases,
            invalid_fp_atoms=invalid_fp_atoms,
            duplicate_value_logs=validation.duplicate_value_log,
            empty_prediction_document_ids=validation.empty_prediction_document_ids,
        ),
    )

    metrics = scoring_result
    print(
        "wrote protocol-v1 artifacts to "
        f"{Path(args.output_dir)} "
        f"(P={metrics.precision:.6f}, R={metrics.recall:.6f}, F1={metrics.f1:.6f})"
    )
    return artifacts


def load_schema(
    path: Path,
    *,
    dataset: str,
    split: str,
    split_hash: str,
) -> LoadedSchema:
    payload = _read_json_object(path, "--schema")
    schema_dataset = payload.get("dataset")
    if schema_dataset != dataset:
        raise ProtocolCliError(
            "dataset mismatch: "
            f"explicit --dataset {dataset} but schema dataset is {schema_dataset!r}"
        )

    event_roles: dict[str, frozenset[str]] = {}
    event_types = payload.get("event_types")
    if not isinstance(event_types, list):
        raise ProtocolCliError("--schema must contain event_types: list")
    for index, raw_event in enumerate(event_types):
        if not isinstance(raw_event, dict):
            raise ProtocolCliError(f"--schema event_types[{index}] must be an object")
        event_type = raw_event.get("event_type")
        roles = raw_event.get("roles")
        if not isinstance(event_type, str) or not event_type:
            raise ProtocolCliError(
                f"--schema event_types[{index}].event_type must be a string"
            )
        if not isinstance(roles, list) or not all(
            isinstance(role, str) and role for role in roles
        ):
            raise ProtocolCliError(
                f"--schema event_types[{index}].roles must be list[str]"
            )
        event_roles[event_type] = frozenset(roles)

    return LoadedSchema(
        registry=SchemaRegistry(
            dataset=dataset,
            split=split,
            event_roles=event_roles,
            schema_hash="sha256:" + sha256_file(path),
            split_hash=split_hash,
        ),
        schema_version=str(payload.get("canonical_version") or "unknown"),
        split_version=f"explicit:{split}",
    )


def read_protocol_gold_jsonl(
    path: Path,
    schema: SchemaRegistry,
    *,
    dataset: str,
    split: str,
) -> tuple[CanonicalDocument, ...]:
    rows = _read_jsonl_rows(path, source="--gold")
    if not rows:
        return ()

    first = rows[0][1]
    if isinstance(first, dict) and "document_id" in first and "gold_events" in first:
        return tuple(read_gold_jsonl(path, schema))
    if isinstance(first, dict) and "doc_id" in first and "events" in first:
        return _read_evaluator_gold_rows(rows, schema, dataset=dataset, split=split)
    raise ProtocolCliError(
        "--gold must be canonical gold JSONL with document_id/gold_events "
        "or a copied evaluator_gold snapshot with doc_id/events"
    )


def freeze_documents_with_logs(
    documents: Sequence[CanonicalDocument],
    *,
    normalizer: StrictNormalizer,
) -> FrozenWithLogs:
    records: list[FrozenRecord] = []
    logs: list[NormalizationLogEntry] = []
    for document in documents:
        for record_index, record in enumerate(document.records):
            roles, record_logs = _normalize_arguments(record.arguments, normalizer)
            logs.extend(record_logs)
            records.append(
                FrozenRecord(
                    dataset=document.dataset,
                    split=document.split,
                    document_id=document.document_id,
                    event_type=record.event_type,
                    record_index=record_index,
                    event_id=record.event_id,
                    roles_to_values=roles,
                )
            )
    return FrozenWithLogs(tuple(records), tuple(logs))


def freeze_valid_predictions_with_logs(
    records: Sequence[ValidPredictionRecord],
    schema: SchemaRegistry,
    *,
    normalizer: StrictNormalizer,
) -> FrozenWithLogs:
    frozen: list[FrozenRecord] = []
    logs: list[NormalizationLogEntry] = []
    for record in records:
        roles, record_logs = _normalize_arguments(record.arguments, normalizer)
        logs.extend(record_logs)
        frozen.append(
            FrozenRecord(
                dataset=schema.dataset,
                split=schema.split,
                document_id=record.document_id,
                event_type=record.event_type,
                record_index=record.record_index,
                event_id=record.event_id,
                roles_to_values=roles,
            )
        )
    return FrozenWithLogs(tuple(frozen), tuple(logs))


def _read_evaluator_gold_rows(
    rows: Sequence[tuple[int, Any]],
    schema: SchemaRegistry,
    *,
    dataset: str,
    split: str,
) -> tuple[CanonicalDocument, ...]:
    documents: list[CanonicalDocument] = []
    issues: list[ValidationIssue] = []
    for line_number, payload in rows:
        document, document_issues = _parse_evaluator_gold_document(
            payload,
            schema,
            dataset=dataset,
            split=split,
            line_number=line_number,
        )
        issues.extend(document_issues)
        if document is not None:
            documents.append(document)
    if issues:
        raise ContractValidationError(issues)
    return tuple(documents)


def _parse_evaluator_gold_document(
    payload: Any,
    schema: SchemaRegistry,
    *,
    dataset: str,
    split: str,
    line_number: int,
) -> tuple[CanonicalDocument | None, list[ValidationIssue]]:
    if not isinstance(payload, dict):
        return None, [
            ValidationIssue(
                code="invalid_document_type",
                message="gold JSONL line must be an object",
                line_number=line_number,
                raw_value=payload,
            )
        ]

    document_id = payload.get("doc_id")
    if not isinstance(document_id, str) or not document_id:
        return None, [
            ValidationIssue(
                code="missing_doc_id",
                message="evaluator_gold row requires doc_id",
                line_number=line_number,
                raw_value=payload,
            )
        ]
    if payload.get("dataset") != dataset:
        return None, [
            ValidationIssue(
                code="dataset_mismatch",
                message=(f"gold dataset must match explicit --dataset {dataset}"),
                line_number=line_number,
                document_id=document_id,
                raw_value=payload.get("dataset"),
            )
        ]
    if payload.get("split") != split:
        return None, [
            ValidationIssue(
                code="split_mismatch",
                message=f"gold split must match explicit --split {split}",
                line_number=line_number,
                document_id=document_id,
                raw_value=payload.get("split"),
            )
        ]

    raw_events = payload.get("events")
    if not isinstance(raw_events, list):
        return None, [
            ValidationIssue(
                code="invalid_events_type",
                message="evaluator_gold row requires events: list",
                line_number=line_number,
                document_id=document_id,
                raw_value=raw_events,
            )
        ]

    records: list[CanonicalRecord] = []
    issues: list[ValidationIssue] = []
    for record_index, raw_event in enumerate(raw_events):
        record, record_issues = _parse_evaluator_gold_record(
            raw_event,
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
            dataset=dataset,
            split=split,
            document_id=document_id,
            records_field="gold_events",
            records=tuple(records),
        ),
        [],
    )


def _parse_evaluator_gold_record(
    payload: Any,
    schema: SchemaRegistry,
    *,
    line_number: int,
    document_id: str,
    record_index: int,
) -> tuple[CanonicalRecord | None, list[ValidationIssue]]:
    if not isinstance(payload, dict):
        return None, [
            _gold_issue(
                "invalid_record_type",
                "gold event must be an object",
                line_number,
                document_id,
                record_index,
                raw_value=payload,
            )
        ]

    event_type = payload.get("event_type")
    if not isinstance(event_type, str) or not event_type:
        return None, [
            _gold_issue(
                "invalid_event_type",
                "gold event requires event_type: string",
                line_number,
                document_id,
                record_index,
                raw_value=event_type,
            )
        ]
    if not schema.has_event_type(event_type):
        return None, [
            _gold_issue(
                "illegal_event_type",
                "gold event_type is not legal for the schema",
                line_number,
                document_id,
                record_index,
                event_type=event_type,
                raw_value=event_type,
            )
        ]

    event_id = payload.get("event_id")
    if event_id is not None and not isinstance(event_id, str):
        return None, [
            _gold_issue(
                "invalid_event_id_type",
                "gold event_id must be a string when present",
                line_number,
                document_id,
                record_index,
                event_type=event_type,
                raw_value=event_id,
            )
        ]

    raw_arguments = payload.get("arguments")
    if not isinstance(raw_arguments, dict):
        return None, [
            _gold_issue(
                "invalid_arguments_type",
                "gold event requires arguments: object",
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
        if not isinstance(role, str) or not schema.has_role(event_type, role):
            issues.append(
                _gold_issue(
                    "illegal_role",
                    "gold role is not legal for the event type",
                    line_number,
                    document_id,
                    record_index,
                    event_type=event_type,
                    role=repr(role),
                    raw_value=raw_value,
                )
            )
            continue
        value, issue = _gold_role_value(
            raw_value,
            line_number=line_number,
            document_id=document_id,
            record_index=record_index,
            event_type=event_type,
            role=role,
        )
        if issue is not None:
            issues.append(issue)
            continue
        if value is not None:
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


def _gold_role_value(
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
    if isinstance(raw_value, list):
        values: list[str] = []
        for item in raw_value:
            if isinstance(item, str):
                values.append(item)
                continue
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                values.append(item["text"])
                continue
            return (
                None,
                _gold_issue(
                    "invalid_value_type",
                    "gold role values must be string or list of text objects",
                    line_number,
                    document_id,
                    record_index,
                    event_type=event_type,
                    role=role,
                    raw_value=item,
                ),
            )
        if not values:
            return None, None
        return tuple(values), None
    return (
        None,
        _gold_issue(
            "invalid_value_type",
            "gold role value must be string, list, or null",
            line_number,
            document_id,
            record_index,
            event_type=event_type,
            role=role,
            raw_value=raw_value,
        ),
    )


def _normalize_arguments(
    arguments: Mapping[str, CanonicalRoleValue],
    normalizer: StrictNormalizer,
) -> tuple[dict[str, tuple[str, ...]], tuple[NormalizationLogEntry, ...]]:
    normalized_arguments: dict[str, tuple[str, ...]] = {}
    logs: list[NormalizationLogEntry] = []
    for role, raw_value in arguments.items():
        result = normalizer.normalize_role_value(raw_value)
        logs.extend(result.logs)
        values = _role_value_to_tuple(result.normalized_value)
        if values:
            normalized_arguments[role] = values
    return normalized_arguments, tuple(logs)


def _role_value_to_tuple(value: CanonicalRoleValue) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    return tuple(item for item in value if item)


def _invalid_fp_atoms(validation: PredictionValidationResult) -> tuple[FPAtom, ...]:
    return (
        *validation.illegal_event_fp_atoms,
        *validation.illegal_role_fp_atoms,
        *validation.invalid_value_fp_atoms,
    )


def _read_json_object(path: Path, flag_name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProtocolCliError(f"{flag_name} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProtocolCliError(f"{flag_name} must be a JSON object")
    return payload


def _read_jsonl_rows(path: Path, *, source: str) -> tuple[tuple[int, Any], ...]:
    rows: list[tuple[int, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                rows.append((line_number, json.loads(line)))
            except json.JSONDecodeError as exc:
                raise ProtocolCliError(
                    f"{source} has invalid JSON at line {line_number}: {exc}"
                ) from exc
    return tuple(rows)


def _require_file(path: Path, flag_name: str) -> None:
    if not path.is_file():
        raise ProtocolCliError(f"{flag_name} file does not exist: {path}")


def _format_contract_error(exc: ContractValidationError) -> str:
    lines = ["protocol-v1: error: input contract validation failed"]
    for issue in exc.issues[:10]:
        location = _issue_location(issue)
        lines.append(f"- {issue.code}{location}: {issue.message}")
    if len(exc.issues) > 10:
        lines.append(f"- ... {len(exc.issues) - 10} more issues")
    return "\n".join(lines) + "\n"


def _issue_location(issue: ValidationIssue) -> str:
    parts: list[str] = []
    if issue.line_number is not None:
        parts.append(f"line {issue.line_number}")
    if issue.document_id is not None:
        parts.append(f"document {issue.document_id}")
    if issue.record_index is not None:
        parts.append(f"record {issue.record_index}")
    if issue.event_type is not None:
        parts.append(f"event_type {issue.event_type}")
    if issue.role is not None:
        parts.append(f"role {issue.role}")
    return f" ({', '.join(parts)})" if parts else ""


def _gold_issue(
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


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
