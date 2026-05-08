from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from unified_eval.matching import MATCHING_LOG_CSV_FIELDS, FrozenRecord
from unified_eval.normalization import (
    NORMALIZATION_LOG_CSV_FIELDS,
    StrictNormalizer,
    normalization_config_hash,
)
from unified_eval.reporting import (
    ARTIFACT_FILENAMES,
    DUPLICATE_LOG_CSV_FIELDS,
    ERROR_CASES_CSV_FIELDS,
    UNMATCHED_CASES_CSV_FIELDS,
    ReportArtifactInput,
    build_config_manifest,
    write_report_artifacts,
)
from unified_eval.schema import SchemaRegistry
from unified_eval.scoring import score_records
from unified_eval.validation import (
    DUPLICATE_VALUE_LOG_CSV_FIELDS,
    INVALID_CASE_CSV_FIELDS,
    DuplicateValueLogEntry,
    FPAtom,
    InvalidCase,
)

STRICT_CONFIG_PATH = Path("configs/strict_normalizer_v1.json")


@pytest.fixture
def schema_registry() -> SchemaRegistry:
    return SchemaRegistry(
        dataset="ToyDEE",
        split="dev",
        event_roles={
            "EventA": frozenset({"r1", "r2"}),
        },
        schema_hash="sha256:schema",
        split_hash="sha256:split",
    )


def _record(
    *,
    record_index: int,
    document_id: str,
    arguments: dict[str, str | tuple[str, ...]],
) -> FrozenRecord:
    return FrozenRecord(
        dataset="ToyDEE",
        split="dev",
        document_id=document_id,
        event_type="EventA",
        record_index=record_index,
        roles_to_values={
            role: frozenset((value,) if isinstance(value, str) else value)
            for role, value in arguments.items()
        },
    )


def _read_csv_header(path: Path) -> tuple[str, ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(next(csv.reader(handle)))


def test_report_artifacts_write_required_files_and_stable_headers(
    tmp_path: Path,
    schema_registry: SchemaRegistry,
) -> None:
    normalizer_config = json.loads(STRICT_CONFIG_PATH.read_text(encoding="utf-8"))
    normalizer = StrictNormalizer.from_config(normalizer_config)
    normalization_logs = normalizer.normalize("Ａ，Ｂ").logs
    predictions = (
        _record(
            record_index=0,
            document_id="doc_001",
            arguments={"r1": "A", "r2": "wrong"},
        ),
        _record(
            record_index=0,
            document_id="doc_002",
            arguments={"r1": "extra"},
        ),
        _record(
            record_index=1,
            document_id="doc_002",
            arguments={"r1": "extra"},
        ),
    )
    golds = (
        _record(
            record_index=0,
            document_id="doc_001",
            arguments={"r1": "A", "r2": "right"},
        ),
        _record(
            record_index=0,
            document_id="doc_003",
            arguments={"r1": "missing"},
        ),
    )
    invalid_fp_atoms = (
        FPAtom(
            document_id="doc_004",
            line_number=4,
            record_index=0,
            event_type="EventA",
            role="r1",
            value="invalid-fp",
            raw_value=1000,
        ),
    )
    scoring_result = score_records(
        predictions,
        golds,
        schema_registry,
        invalid_fp_atoms=invalid_fp_atoms,
    )

    artifact_input = ReportArtifactInput(
        schema=schema_registry,
        schema_version="schema-v1",
        split_version="official",
        evaluator_version="dee-eval-v1.0.0",
        scoring_result=scoring_result,
        predictions=predictions,
        golds=golds,
        normalizer_config=normalizer_config,
        normalization_logs=normalization_logs,
        invalid_cases=(
            InvalidCase(
                code="invalid_value_type",
                message="role value must be a string, list[string], or null",
                line_number=4,
                document_id="doc_004",
                record_index=0,
                event_type="EventA",
                role="r1",
                raw_value=1000,
            ),
        ),
        invalid_fp_atoms=invalid_fp_atoms,
        duplicate_value_logs=(
            DuplicateValueLogEntry(
                document_id="doc_001",
                line_number=1,
                record_index=0,
                event_type="EventA",
                role="r1",
                value="A",
                count=2,
            ),
        ),
        commit_hash="abc123",
    )

    paths = write_report_artifacts(tmp_path, artifact_input)

    assert set(paths) == set(ARTIFACT_FILENAMES)
    for filename in ARTIFACT_FILENAMES:
        assert (tmp_path / filename).is_file()

    overall = json.loads((tmp_path / "overall_metrics.json").read_text())
    assert set(overall) == {
        "dataset",
        "split",
        "evaluator_version",
        "schema_version",
        "schema_hash",
        "split_version",
        "normalization_config_hash",
        "matching_config_hash",
        "official",
        "unified_strict",
        "aux_normalized",
        "diagnostics",
    }
    assert overall["dataset"] == "ToyDEE"
    assert overall["split"] == "dev"
    assert overall["schema_hash"] == "sha256:schema"
    assert overall["normalization_config_hash"] == normalizer.config_hash
    assert (
        overall["matching_config_hash"]
        == scoring_result.matching_result.matching_config_hash
    )
    assert overall["official"]["available"] is False
    assert overall["aux_normalized"]["enabled"] is False
    assert overall["unified_strict"] == {
        "tp": 1,
        "fp": 4,
        "fn": 2,
        "precision": pytest.approx(0.2),
        "recall": pytest.approx(1 / 3),
        "f1": pytest.approx(0.25),
    }

    assert _read_csv_header(tmp_path / "matching_log.csv") == MATCHING_LOG_CSV_FIELDS
    assert (
        _read_csv_header(tmp_path / "unmatched_cases.csv") == UNMATCHED_CASES_CSV_FIELDS
    )
    assert _read_csv_header(tmp_path / "error_cases.csv") == ERROR_CASES_CSV_FIELDS
    assert _read_csv_header(tmp_path / "invalid_cases.csv") == INVALID_CASE_CSV_FIELDS
    assert (
        _read_csv_header(tmp_path / "normalization_log.csv")
        == NORMALIZATION_LOG_CSV_FIELDS
    )
    assert _read_csv_header(tmp_path / "duplicate_log.csv") == DUPLICATE_LOG_CSV_FIELDS
    assert DUPLICATE_VALUE_LOG_CSV_FIELDS == DUPLICATE_LOG_CSV_FIELDS
    with (tmp_path / "duplicate_log.csv").open(newline="", encoding="utf-8") as handle:
        duplicate_rows = list(csv.DictReader(handle))
    assert {row["duplicate_type"] for row in duplicate_rows} == {
        "duplicate_record",
        "duplicate_role_value",
    }

    config = json.loads((tmp_path / "config.json").read_text())
    assert config["dataset"] == "ToyDEE"
    assert config["split"] == "dev"
    assert config["schema_version"] == "schema-v1"
    assert config["schema_hash"] == "sha256:schema"
    assert config["split_version"] == "official"
    assert config["split_hash"] == "sha256:split"
    assert config["python_version"]
    assert config["scipy_version"] == scoring_result.matching_result.scipy_version
    assert config["dependency_versions"]["python"] == config["python_version"]
    assert config["dependency_versions"]["scipy"] == config["scipy_version"]
    assert config["commit_hash"] == "abc123"
    assert config["mutation_guard"]["leaderboard_valid"] is True


def test_t26_config_hashes_are_stable_for_same_data_and_equivalent_config(
    schema_registry: SchemaRegistry,
) -> None:
    normalizer_config = json.loads(STRICT_CONFIG_PATH.read_text(encoding="utf-8"))
    reordered_config = {
        key: normalizer_config[key] for key in reversed(normalizer_config)
    }
    record = _record(record_index=0, document_id="doc_001", arguments={"r1": "A"})
    scoring_result = score_records((record,), (record,), schema_registry)

    first = build_config_manifest(
        ReportArtifactInput(
            schema=schema_registry,
            schema_version="schema-v1",
            split_version="official",
            evaluator_version="dee-eval-v1.0.0",
            scoring_result=scoring_result,
            predictions=(record,),
            golds=(record,),
            normalizer_config=normalizer_config,
            commit_hash="abc123",
        )
    )
    second = build_config_manifest(
        ReportArtifactInput(
            schema=schema_registry,
            schema_version="schema-v1",
            split_version="official",
            evaluator_version="dee-eval-v1.0.0",
            scoring_result=scoring_result,
            predictions=(record,),
            golds=(record,),
            normalizer_config=reordered_config,
            commit_hash="abc123",
        )
    )

    assert first["schema_hash"] == second["schema_hash"] == "sha256:schema"
    assert first["normalization_config_hash"] == second["normalization_config_hash"]
    assert first["matching_config_hash"] == second["matching_config_hash"]


def test_t27_config_mutation_reports_changed_hash_and_invalidates_leaderboard_result(
    schema_registry: SchemaRegistry,
) -> None:
    original_config = json.loads(STRICT_CONFIG_PATH.read_text(encoding="utf-8"))
    changed_config = json.loads(json.dumps(original_config))
    changed_config["punctuation_map"]["。"] = "."
    record = _record(record_index=0, document_id="doc_001", arguments={"r1": "A"})
    scoring_result = score_records((record,), (record,), schema_registry)

    config = build_config_manifest(
        ReportArtifactInput(
            schema=schema_registry,
            schema_version="schema-v1",
            split_version="official",
            evaluator_version="dee-eval-v1.0.0",
            scoring_result=scoring_result,
            predictions=(record,),
            golds=(record,),
            normalizer_config=changed_config,
            expected_hashes={
                "normalization_config_hash": normalization_config_hash(original_config)
            },
            commit_hash="abc123",
        )
    )

    assert config["normalization_config_hash"] == normalization_config_hash(
        changed_config
    )
    assert config["normalization_config_hash"] != normalization_config_hash(
        original_config
    )
    assert config["mutation_guard"]["leaderboard_valid"] is False
    assert config["mutation_guard"]["mismatched_hashes"] == [
        "normalization_config_hash"
    ]
