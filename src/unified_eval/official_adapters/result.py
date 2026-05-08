from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

OFFICIAL_RESULT_SCHEMA_VERSION = "official-metric-result-v1"
OFFICIAL_RESULT_FIELDS = (
    "schema_version",
    "available",
    "dataset",
    "metric_name",
    "evaluator",
    "score_type",
    "precision",
    "recall",
    "f1",
    "evaluator_version",
    "evaluator_commit_hash",
    "command",
    "source",
    "unavailable_reason",
    "metadata",
    "notes",
)

ScoreType = Literal[
    "official",
    "online_official",
    "offline_official_style",
    "unavailable",
]

_METRIC_ALIASES = {
    "precision": ("precision", "p", "micro_p", "MicroP", "MicroPrecision"),
    "recall": ("recall", "r", "micro_r", "MicroR", "MicroRecall"),
    "f1": ("f1", "f", "micro_f1", "MicroF1", "MicroF"),
}


@dataclass(frozen=True, slots=True)
class OfficialMetricResult:
    dataset: str
    metric_name: str
    evaluator: str
    score_type: ScoreType
    available: bool
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    evaluator_version: str = ""
    evaluator_commit_hash: str = ""
    command: str = ""
    source: str = ""
    unavailable_reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    notes: Sequence[str] = ()

    def __post_init__(self) -> None:
        _require_nonempty_string(self.dataset, "dataset")
        _require_nonempty_string(self.metric_name, "metric_name")
        _require_nonempty_string(self.evaluator, "evaluator")
        if self.available and self.score_type == "unavailable":
            raise ValueError(
                "available official results cannot use unavailable score_type"
            )
        if not self.available and self.score_type != "unavailable":
            raise ValueError(
                "unavailable official results must use unavailable score_type"
            )
        if not self.available and not self.unavailable_reason:
            raise ValueError("unavailable official results require unavailable_reason")

        for field_name in ("precision", "recall", "f1"):
            value = getattr(self, field_name)
            if not isinstance(value, int | float) or isinstance(value, bool):
                raise ValueError(f"{field_name} must be a number")
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{field_name} must be in [0.0, 1.0]")

        if not self.available:
            object.__setattr__(self, "precision", 0.0)
            object.__setattr__(self, "recall", 0.0)
            object.__setattr__(self, "f1", 0.0)
        else:
            object.__setattr__(self, "precision", float(self.precision))
            object.__setattr__(self, "recall", float(self.recall))
            object.__setattr__(self, "f1", float(self.f1))

        object.__setattr__(self, "metadata", _json_mapping(self.metadata))
        object.__setattr__(self, "notes", tuple(str(note) for note in self.notes))

    def to_overall_metrics_block(self) -> dict[str, Any]:
        return {
            "schema_version": OFFICIAL_RESULT_SCHEMA_VERSION,
            "available": self.available,
            "dataset": self.dataset,
            "metric_name": self.metric_name,
            "evaluator": self.evaluator,
            "score_type": self.score_type,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "evaluator_version": self.evaluator_version,
            "evaluator_commit_hash": self.evaluator_commit_hash,
            "command": self.command,
            "source": self.source,
            "unavailable_reason": self.unavailable_reason,
            "metadata": _json_mapping(self.metadata),
            "notes": list(self.notes),
        }


def available_result(
    *,
    dataset: str,
    metric_name: str,
    evaluator: str,
    score_type: ScoreType,
    precision: float,
    recall: float,
    f1: float,
    evaluator_version: str = "",
    evaluator_commit_hash: str = "",
    command: str = "",
    source: str = "",
    metadata: Mapping[str, Any] | None = None,
    notes: Sequence[str] = (),
) -> OfficialMetricResult:
    if score_type == "unavailable":
        raise ValueError("use unavailable_result for unavailable official metrics")
    return OfficialMetricResult(
        dataset=dataset,
        metric_name=metric_name,
        evaluator=evaluator,
        score_type=score_type,
        available=True,
        precision=precision,
        recall=recall,
        f1=f1,
        evaluator_version=evaluator_version,
        evaluator_commit_hash=evaluator_commit_hash,
        command=command,
        source=source,
        metadata=metadata or {},
        notes=notes,
    )


def unavailable_result(
    *,
    dataset: str,
    metric_name: str,
    evaluator: str,
    reason: str,
    metadata: Mapping[str, Any] | None = None,
    notes: Sequence[str] = (),
) -> OfficialMetricResult:
    return OfficialMetricResult(
        dataset=dataset,
        metric_name=metric_name,
        evaluator=evaluator,
        score_type="unavailable",
        available=False,
        unavailable_reason=reason,
        metadata=metadata or {},
        notes=notes,
    )


def load_metric_result(
    path: Path | str,
    *,
    dataset: str,
    metric_name: str,
    evaluator: str,
    score_type: ScoreType,
    evaluator_version: str,
    evaluator_commit_hash: str,
    command: str,
    metadata: Mapping[str, Any] | None = None,
    notes: Sequence[str] = (),
) -> OfficialMetricResult:
    if score_type == "unavailable":
        raise ValueError("load_metric_result requires an available score_type")

    result_path = Path(path)
    payload = _load_json_object(result_path)
    precision = _metric_value(payload, "precision")
    recall = _metric_value(payload, "recall")
    f1 = _metric_value(payload, "f1")
    payload_metric_name = payload.get("metric_name", metric_name)
    if not isinstance(payload_metric_name, str) or not payload_metric_name:
        raise ValueError("metric_name must be a non-empty string when present")

    return available_result(
        dataset=dataset,
        metric_name=payload_metric_name,
        evaluator=evaluator,
        score_type=score_type,
        precision=precision,
        recall=recall,
        f1=f1,
        evaluator_version=evaluator_version,
        evaluator_commit_hash=evaluator_commit_hash,
        command=command,
        source=str(result_path),
        metadata=metadata,
        notes=notes,
    )


def _metric_value(payload: Mapping[str, Any], metric_name: str) -> float:
    for alias in _METRIC_ALIASES[metric_name]:
        if alias in payload:
            value = payload[alias]
            if not isinstance(value, int | float) or isinstance(value, bool):
                raise ValueError(f"{alias} must be a number")
            return float(value)
    expected = ", ".join(_METRIC_ALIASES[metric_name])
    raise ValueError(f"missing {metric_name}; expected one of: {expected}")


def _load_json_object(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"official metric result must be a JSON object: {path}")
    return payload


def _json_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(dict(value), ensure_ascii=False, sort_keys=True))


def _require_nonempty_string(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
