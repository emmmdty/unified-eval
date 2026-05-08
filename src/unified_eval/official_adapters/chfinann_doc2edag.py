from __future__ import annotations

from pathlib import Path

from unified_eval.official_adapters.result import (
    OfficialMetricResult,
    available_result,
    load_metric_result,
    unavailable_result,
)

DATASET = "ChFinAnn"
METRIC_NAME = "ChFinAnn Official F1"
EVALUATOR = "chfinann-doc2edag-official"


def load_result(
    path: Path | str,
    *,
    evaluator_version: str,
    evaluator_commit_hash: str,
    command: str,
) -> OfficialMetricResult:
    return load_metric_result(
        path,
        dataset=DATASET,
        metric_name=METRIC_NAME,
        evaluator=EVALUATOR,
        score_type="official",
        evaluator_version=evaluator_version,
        evaluator_commit_hash=evaluator_commit_hash,
        command=command,
    )


def result_from_metrics(
    *,
    precision: float,
    recall: float,
    f1: float,
    evaluator_version: str,
    evaluator_commit_hash: str,
    command: str,
    source: str = "",
) -> OfficialMetricResult:
    return available_result(
        dataset=DATASET,
        metric_name=METRIC_NAME,
        evaluator=EVALUATOR,
        score_type="official",
        precision=precision,
        recall=recall,
        f1=f1,
        evaluator_version=evaluator_version,
        evaluator_commit_hash=evaluator_commit_hash,
        command=command,
        source=source,
    )


def unavailable(reason: str) -> OfficialMetricResult:
    return unavailable_result(
        dataset=DATASET,
        metric_name=METRIC_NAME,
        evaluator=EVALUATOR,
        reason=reason,
    )
