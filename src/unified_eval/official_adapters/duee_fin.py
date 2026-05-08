from __future__ import annotations

from pathlib import Path

from unified_eval.official_adapters.result import (
    OfficialMetricResult,
    available_result,
    load_metric_result,
    unavailable_result,
)

DATASET = "DuEE-Fin"
ONLINE_METRIC_NAME = "DuEE-Fin Online Official F1"
OFFLINE_METRIC_NAME = "DuEE-Fin Offline Official-Style F1"
UNAVAILABLE_METRIC_NAME = "DuEE-Fin Official / Offline Official-Style F1"
ONLINE_EVALUATOR = "duee-fin-online-official"
OFFLINE_EVALUATOR = "duee-fin-offline-official-style"
UNAVAILABLE_EVALUATOR = "duee-fin-official"

OFFLINE_OFFICIAL_STYLE_NOTE = (
    "DuEE-Fin official test evaluation is not fully reproducible offline in this "
    "setting. When online submission is available, report the official online "
    "score. Otherwise, report an offline official-style reproduction separately "
    "from official hidden-test leaderboard results."
)


def online_result(
    *,
    precision: float,
    recall: float,
    f1: float,
    submission_date: str,
    source: str,
) -> OfficialMetricResult:
    return available_result(
        dataset=DATASET,
        metric_name=ONLINE_METRIC_NAME,
        evaluator=ONLINE_EVALUATOR,
        score_type="online_official",
        precision=precision,
        recall=recall,
        f1=f1,
        source=source,
        metadata={"submission_date": submission_date},
    )


def load_offline_official_style_result(
    path: Path | str,
    *,
    evaluator_version: str,
    evaluator_commit_hash: str,
    command: str,
) -> OfficialMetricResult:
    return load_metric_result(
        path,
        dataset=DATASET,
        metric_name=OFFLINE_METRIC_NAME,
        evaluator=OFFLINE_EVALUATOR,
        score_type="offline_official_style",
        evaluator_version=evaluator_version,
        evaluator_commit_hash=evaluator_commit_hash,
        command=command,
        notes=(OFFLINE_OFFICIAL_STYLE_NOTE,),
    )


def offline_official_style_result(
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
        metric_name=OFFLINE_METRIC_NAME,
        evaluator=OFFLINE_EVALUATOR,
        score_type="offline_official_style",
        precision=precision,
        recall=recall,
        f1=f1,
        evaluator_version=evaluator_version,
        evaluator_commit_hash=evaluator_commit_hash,
        command=command,
        source=source,
        notes=(OFFLINE_OFFICIAL_STYLE_NOTE,),
    )


def unavailable(reason: str) -> OfficialMetricResult:
    return unavailable_result(
        dataset=DATASET,
        metric_name=UNAVAILABLE_METRIC_NAME,
        evaluator=UNAVAILABLE_EVALUATOR,
        reason=reason,
    )
