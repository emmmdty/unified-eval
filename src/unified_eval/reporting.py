from __future__ import annotations

import csv
import importlib.metadata
import json
import platform
import subprocess
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from unified_eval import __version__
from unified_eval.matching import (
    MATCHING_CONFIG_V1,
    MATCHING_LOG_CSV_FIELDS,
    FrozenRecord,
    MatchedPair,
    MatchingResult,
    matching_config_hash,
    matching_log_to_csv_rows,
)
from unified_eval.normalization import (
    NORMALIZATION_LOG_CSV_FIELDS,
    NormalizationLogEntry,
    normalization_config_hash,
    normalization_logs_to_csv_rows,
)
from unified_eval.official_adapters import (
    OFFICIAL_RESULT_FIELDS,
    OfficialMetricResult,
    unavailable_result,
)
from unified_eval.schema import SchemaRegistry
from unified_eval.scoring import ScoringResult
from unified_eval.validation import (
    DUPLICATE_VALUE_LOG_CSV_FIELDS,
    INVALID_CASE_CSV_FIELDS,
    DuplicateValueLogEntry,
    FPAtom,
    InvalidCase,
    invalid_cases_to_csv_rows,
)

ARTIFACT_FILENAMES = (
    "overall_metrics.json",
    "matching_log.csv",
    "unmatched_cases.csv",
    "error_cases.csv",
    "invalid_cases.csv",
    "normalization_log.csv",
    "duplicate_log.csv",
    "config.json",
)

UNMATCHED_CASES_CSV_FIELDS = (
    "case_type",
    "document_id",
    "event_type",
    "pred_idx",
    "gold_idx",
    "record_json",
    "reason",
)

ERROR_CASES_CSV_FIELDS = (
    "case_type",
    "document_id",
    "event_type",
    "pred_idx",
    "gold_idx",
    "role",
    "value_json",
    "reason",
)

DUPLICATE_LOG_CSV_FIELDS = DUPLICATE_VALUE_LOG_CSV_FIELDS

_DIAGNOSTIC_FIELDS = (
    "record_em",
    "event_type_f1",
    "json_validity",
    "format_validity",
    "schema_validity",
    "invalid_event_type_rate",
    "invalid_role_rate",
    "duplicate_record_rate",
    "empty_prediction_rate",
)


@dataclass(frozen=True, slots=True)
class ReportArtifactInput:
    schema: SchemaRegistry
    schema_version: str
    split_version: str
    evaluator_version: str
    scoring_result: ScoringResult
    predictions: Sequence[FrozenRecord]
    golds: Sequence[FrozenRecord]
    normalizer_config: Mapping[str, Any]
    matcher_config: Mapping[str, Any] = field(
        default_factory=lambda: MATCHING_CONFIG_V1.copy()
    )
    official: Mapping[str, Any] | OfficialMetricResult | None = None
    aux_normalized: Mapping[str, Any] | None = None
    diagnostics: Mapping[str, float] | None = None
    normalization_logs: Sequence[NormalizationLogEntry] = ()
    invalid_cases: Sequence[InvalidCase] = ()
    invalid_fp_atoms: Sequence[FPAtom] = ()
    duplicate_value_logs: Sequence[DuplicateValueLogEntry] = ()
    empty_prediction_document_ids: Sequence[str] = ()
    expected_hashes: Mapping[str, str] = field(default_factory=dict)
    commit_hash: str | None = None


def write_report_artifacts(
    output_dir: Path | str,
    report_input: ReportArtifactInput,
) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    artifact_payloads = {
        "overall_metrics.json": build_overall_metrics(report_input),
        "config.json": build_config_manifest(report_input),
    }
    csv_payloads = {
        "matching_log.csv": (
            MATCHING_LOG_CSV_FIELDS,
            matching_log_to_csv_rows(
                report_input.scoring_result.matching_result.matching_log
            ),
        ),
        "unmatched_cases.csv": (
            UNMATCHED_CASES_CSV_FIELDS,
            unmatched_cases_to_csv_rows(report_input.scoring_result.matching_result),
        ),
        "error_cases.csv": (
            ERROR_CASES_CSV_FIELDS,
            error_cases_to_csv_rows(report_input),
        ),
        "invalid_cases.csv": (
            INVALID_CASE_CSV_FIELDS,
            invalid_cases_to_csv_rows(report_input.invalid_cases),
        ),
        "normalization_log.csv": (
            NORMALIZATION_LOG_CSV_FIELDS,
            normalization_logs_to_csv_rows(report_input.normalization_logs),
        ),
        "duplicate_log.csv": (
            DUPLICATE_LOG_CSV_FIELDS,
            duplicate_logs_to_csv_rows(report_input),
        ),
    }

    written: dict[str, Path] = {}
    for filename, payload in artifact_payloads.items():
        path = output_path / filename
        _write_json(path, payload)
        written[filename] = path

    for filename, (fieldnames, rows) in csv_payloads.items():
        path = output_path / filename
        _write_csv(path, fieldnames, rows)
        written[filename] = path

    return {filename: written[filename] for filename in ARTIFACT_FILENAMES}


def build_overall_metrics(report_input: ReportArtifactInput) -> dict[str, Any]:
    scoring = report_input.scoring_result
    return {
        "dataset": report_input.schema.dataset,
        "split": report_input.schema.split,
        "evaluator_version": report_input.evaluator_version,
        "schema_version": report_input.schema_version,
        "schema_hash": report_input.schema.schema_hash,
        "split_version": report_input.split_version,
        "normalization_config_hash": normalization_config_hash(
            report_input.normalizer_config
        ),
        "matching_config_hash": matching_config_hash(report_input.matcher_config),
        "official": _official_block(report_input.official, report_input.schema.dataset),
        "unified_strict": {
            "tp": scoring.true_positives,
            "fp": scoring.false_positives,
            "fn": scoring.false_negatives,
            "precision": scoring.precision,
            "recall": scoring.recall,
            "f1": scoring.f1,
        },
        "aux_normalized": _aux_normalized_block(report_input.aux_normalized),
        "diagnostics": _diagnostics_block(report_input),
    }


def build_config_manifest(report_input: ReportArtifactInput) -> dict[str, Any]:
    actual_hashes = {
        "schema_hash": report_input.schema.schema_hash,
        "split_hash": report_input.schema.split_hash,
        "normalization_config_hash": normalization_config_hash(
            report_input.normalizer_config
        ),
        "matching_config_hash": matching_config_hash(report_input.matcher_config),
    }
    expected_hashes = {
        "matching_config_hash": (
            report_input.scoring_result.matching_result.matching_config_hash
        ),
        **dict(report_input.expected_hashes),
    }
    mismatched_hashes = tuple(
        name
        for name in sorted(expected_hashes)
        if expected_hashes[name] != actual_hashes.get(name)
    )
    python_version = platform.python_version()
    scipy_version = report_input.scoring_result.matching_result.scipy_version
    dependency_versions = {
        "python": python_version,
        "scipy": scipy_version,
        "unified-eval": _package_version("unified-eval", __version__),
    }

    return {
        "dataset": report_input.schema.dataset,
        "split": report_input.schema.split,
        "evaluator_version": report_input.evaluator_version,
        "schema_version": report_input.schema_version,
        "schema_hash": report_input.schema.schema_hash,
        "split_version": report_input.split_version,
        "split_hash": report_input.schema.split_hash,
        "normalizer_config": _json_roundtrip(report_input.normalizer_config),
        "normalization_config_hash": actual_hashes["normalization_config_hash"],
        "matcher_config": _json_roundtrip(report_input.matcher_config),
        "matching_config_hash": actual_hashes["matching_config_hash"],
        "python_version": python_version,
        "scipy_version": scipy_version,
        "dependency_versions": dependency_versions,
        "commit_hash": report_input.commit_hash or _git_commit_hash(),
        "mutation_guard": {
            "expected_hashes": expected_hashes,
            "actual_hashes": actual_hashes,
            "mismatched_hashes": list(mismatched_hashes),
            "leaderboard_valid": not mismatched_hashes,
        },
    }


def unmatched_cases_to_csv_rows(
    matching_result: MatchingResult,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in matching_result.unmatched_predictions:
        rows.append(
            {
                "case_type": "prediction",
                "document_id": record.document_id,
                "event_type": record.event_type,
                "pred_idx": str(record.record_index),
                "gold_idx": "",
                "record_json": _record_json(record),
                "reason": "unmatched_prediction",
            }
        )
    for record in matching_result.unmatched_golds:
        rows.append(
            {
                "case_type": "gold",
                "document_id": record.document_id,
                "event_type": record.event_type,
                "pred_idx": "",
                "gold_idx": str(record.record_index),
                "record_json": _record_json(record),
                "reason": "unmatched_gold",
            }
        )
    return sorted(rows, key=_row_sort_key)


def error_cases_to_csv_rows(
    report_input: ReportArtifactInput,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    predictions_by_key = _records_by_match_key(report_input.predictions)
    golds_by_key = _records_by_match_key(report_input.golds)

    for match in report_input.scoring_result.matching_result.matches:
        prediction = predictions_by_key[_match_prediction_key(match)]
        gold = golds_by_key[_match_gold_key(match)]
        rows.extend(_matched_pair_error_rows(prediction, gold, report_input.schema))

    for record in report_input.scoring_result.matching_result.unmatched_predictions:
        for role, value in _record_role_values(record, report_input.schema):
            rows.append(
                _error_row(
                    "FP",
                    record.document_id,
                    record.event_type,
                    pred_idx=record.record_index,
                    gold_idx=None,
                    role=role,
                    value=value,
                    reason="unmatched_prediction",
                )
            )

    for record in report_input.scoring_result.matching_result.unmatched_golds:
        for role, value in _record_role_values(record, report_input.schema):
            rows.append(
                _error_row(
                    "FN",
                    record.document_id,
                    record.event_type,
                    pred_idx=None,
                    gold_idx=record.record_index,
                    role=role,
                    value=value,
                    reason="unmatched_gold",
                )
            )

    for atom in report_input.invalid_fp_atoms:
        rows.append(
            _error_row(
                "FP",
                atom.document_id,
                atom.event_type or "",
                pred_idx=atom.record_index,
                gold_idx=None,
                role=atom.role or "",
                value=atom.value,
                reason="invalid_prediction_atom",
            )
        )

    return sorted(rows, key=_row_sort_key)


def duplicate_logs_to_csv_rows(
    report_input: ReportArtifactInput,
) -> list[dict[str, str]]:
    rows = [
        {
            "duplicate_type": "duplicate_role_value",
            "source": "prediction",
            "document_id": entry.document_id,
            "line_number": str(entry.line_number),
            "record_index": str(entry.record_index),
            "event_type": entry.event_type,
            "role": entry.role,
            "value": entry.value,
            "count": str(entry.count),
            "record_json": "",
        }
        for entry in report_input.duplicate_value_logs
    ]
    rows.extend(_duplicate_record_rows("prediction", report_input.predictions))
    rows.extend(_duplicate_record_rows("gold", report_input.golds))
    return sorted(rows, key=_row_sort_key)


def _matched_pair_error_rows(
    prediction: FrozenRecord,
    gold: FrozenRecord,
    schema: SchemaRegistry,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for role in sorted(schema.legal_roles(prediction.event_type)):
        predicted_values = prediction.roles_to_values.get(role, frozenset())
        gold_values = gold.roles_to_values.get(role, frozenset())
        if predicted_values == gold_values:
            continue
        if predicted_values and gold_values:
            reason = "mismatched_role_value"
        elif predicted_values:
            reason = "extra_role_value"
        else:
            reason = "missing_role_value"

        for value in sorted(predicted_values):
            rows.append(
                _error_row(
                    "FP",
                    prediction.document_id,
                    prediction.event_type,
                    pred_idx=prediction.record_index,
                    gold_idx=gold.record_index,
                    role=role,
                    value=value,
                    reason=reason,
                )
            )
        for value in sorted(gold_values):
            rows.append(
                _error_row(
                    "FN",
                    gold.document_id,
                    gold.event_type,
                    pred_idx=prediction.record_index,
                    gold_idx=gold.record_index,
                    role=role,
                    value=value,
                    reason=reason,
                )
            )
    return rows


def _error_row(
    case_type: str,
    document_id: str,
    event_type: str,
    *,
    pred_idx: int | None,
    gold_idx: int | None,
    role: str,
    value: str,
    reason: str,
) -> dict[str, str]:
    return {
        "case_type": case_type,
        "document_id": document_id,
        "event_type": event_type,
        "pred_idx": _csv_index(pred_idx),
        "gold_idx": _csv_index(gold_idx),
        "role": role,
        "value_json": _json_cell(value),
        "reason": reason,
    }


def _official_block(
    official: Mapping[str, Any] | OfficialMetricResult | None,
    dataset: str,
) -> dict[str, Any]:
    if isinstance(official, OfficialMetricResult):
        return official.to_overall_metrics_block()

    block = _default_unavailable_official_result(dataset).to_overall_metrics_block()
    if official is not None:
        block.update(_json_roundtrip(dict(official)))
    return {field: block[field] for field in OFFICIAL_RESULT_FIELDS}


def _default_unavailable_official_result(dataset: str) -> OfficialMetricResult:
    default_names = {
        "DuEE-Fin": (
            "DuEE-Fin Official / Offline Official-Style F1",
            "duee-fin-official",
        ),
        "ChFinAnn": ("ChFinAnn Official F1", "chfinann-doc2edag-official"),
        "DocFEE": ("DocFEE Official F1", "docfee-official"),
    }
    metric_name, evaluator = default_names.get(dataset, ("Official F1", "official"))
    return unavailable_result(
        dataset=dataset,
        metric_name=metric_name,
        evaluator=evaluator,
        reason="official adapter result was not provided",
    )


def _aux_normalized_block(aux_normalized: Mapping[str, Any] | None) -> dict[str, Any]:
    block = {
        "enabled": False,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
    }
    if aux_normalized is not None:
        block.update(dict(aux_normalized))
    return block


def _diagnostics_block(report_input: ReportArtifactInput) -> dict[str, float]:
    diagnostics = dict.fromkeys(_DIAGNOSTIC_FIELDS, 0.0)
    prediction_count = len(report_input.predictions)
    invalid_record_count = _invalid_record_count(report_input.invalid_cases)
    denominator = max(1, prediction_count + invalid_record_count)
    invalid_event_type_count = sum(
        1 for case in report_input.invalid_cases if case.code == "illegal_event_type"
    )
    invalid_role_count = sum(
        1 for case in report_input.invalid_cases if case.code == "illegal_role"
    )
    diagnostics["invalid_event_type_rate"] = invalid_event_type_count / denominator
    diagnostics["invalid_role_rate"] = invalid_role_count / denominator
    diagnostics["duplicate_record_rate"] = _duplicate_record_rate(
        report_input.predictions
    )
    diagnostics["empty_prediction_rate"] = _empty_prediction_rate(report_input)
    diagnostics["json_validity"] = (
        0.0 if _has_code(report_input, "invalid_json") else 1.0
    )
    diagnostics["format_validity"] = (
        0.0 if _has_any_format_error(report_input.invalid_cases) else 1.0
    )
    diagnostics["schema_validity"] = (
        0.0 if invalid_event_type_count or invalid_role_count else 1.0
    )
    if report_input.diagnostics is not None:
        diagnostics.update(
            {key: float(value) for key, value in report_input.diagnostics.items()}
        )
    return diagnostics


def _duplicate_record_rows(
    source: str,
    records: Sequence[FrozenRecord],
) -> list[dict[str, str]]:
    grouped: defaultdict[tuple[Any, ...], list[FrozenRecord]] = defaultdict(list)
    for record in records:
        grouped[_record_signature(source, record)].append(record)

    rows: list[dict[str, str]] = []
    for group_records in grouped.values():
        if len(group_records) <= 1:
            continue
        for record in group_records:
            rows.append(
                {
                    "duplicate_type": "duplicate_record",
                    "source": source,
                    "document_id": record.document_id,
                    "line_number": "",
                    "record_index": str(record.record_index),
                    "event_type": record.event_type,
                    "role": "",
                    "value": "",
                    "count": str(len(group_records)),
                    "record_json": _record_json(record),
                }
            )
    return rows


def _record_role_values(
    record: FrozenRecord,
    schema: SchemaRegistry,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (role, value)
        for role in sorted(schema.legal_roles(record.event_type))
        for value in sorted(record.roles_to_values.get(role, frozenset()))
    )


def _records_by_match_key(
    records: Sequence[FrozenRecord],
) -> dict[tuple[str, str, str, str, int], FrozenRecord]:
    return {(*record.group_key, record.record_index): record for record in records}


def _match_prediction_key(match: MatchedPair) -> tuple[str, str, str, str, int]:
    return (
        match.dataset,
        match.split,
        match.document_id,
        match.event_type,
        match.pred_index,
    )


def _match_gold_key(match: MatchedPair) -> tuple[str, str, str, str, int]:
    return (
        match.dataset,
        match.split,
        match.document_id,
        match.event_type,
        match.gold_index,
    )


def _invalid_record_count(invalid_cases: Sequence[InvalidCase]) -> int:
    return len(
        {
            (case.document_id, case.record_index)
            for case in invalid_cases
            if case.record_index is not None
        }
    )


def _duplicate_record_rate(records: Sequence[FrozenRecord]) -> float:
    if not records:
        return 0.0
    grouped: defaultdict[tuple[Any, ...], int] = defaultdict(int)
    for record in records:
        grouped[_record_signature("prediction", record)] += 1
    duplicate_extras = sum(max(0, count - 1) for count in grouped.values())
    return duplicate_extras / len(records)


def _empty_prediction_rate(report_input: ReportArtifactInput) -> float:
    document_ids = {
        *(record.document_id for record in report_input.predictions),
        *(record.document_id for record in report_input.golds),
        *report_input.empty_prediction_document_ids,
    }
    if not document_ids:
        return 0.0
    return len(frozenset(report_input.empty_prediction_document_ids)) / len(
        document_ids
    )


def _has_code(report_input: ReportArtifactInput, code: str) -> bool:
    return any(case.code == code for case in report_input.invalid_cases)


def _has_any_format_error(invalid_cases: Sequence[InvalidCase]) -> bool:
    return any(
        case.code
        not in {
            "illegal_event_type",
            "illegal_role",
            "split_mismatch",
            "unknown_document_id",
        }
        for case in invalid_cases
    )


def _record_signature(source: str, record: FrozenRecord) -> tuple[Any, ...]:
    roles = tuple(
        (role, tuple(sorted(values)))
        for role, values in sorted(record.roles_to_values.items())
    )
    return (
        source,
        record.dataset,
        record.split,
        record.document_id,
        record.event_type,
        roles,
    )


def _record_json(record: FrozenRecord) -> str:
    return _json_cell(
        {
            "dataset": record.dataset,
            "split": record.split,
            "document_id": record.document_id,
            "event_type": record.event_type,
            "record_index": record.record_index,
            "event_id": record.event_id,
            "roles_to_values": {
                role: sorted(values)
                for role, values in sorted(record.roles_to_values.items())
            },
        }
    )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def _write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def _json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_roundtrip(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _row_sort_key(row: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(row.get(field, "") for field in sorted(row))


def _csv_index(index: int | None) -> str:
    return "" if index is None else str(index)


def _package_version(package_name: str, fallback: str) -> str:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return fallback


def _git_commit_hash() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"
