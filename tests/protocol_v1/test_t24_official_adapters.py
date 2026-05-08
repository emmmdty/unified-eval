from __future__ import annotations

import json
from pathlib import Path

import pytest

from unified_eval.matching import FrozenRecord
from unified_eval.official_adapters import (
    OFFICIAL_RESULT_FIELDS,
    OFFICIAL_RESULT_SCHEMA_VERSION,
    chfinann_doc2edag,
    docfee,
    duee_fin,
)
from unified_eval.reporting import ReportArtifactInput, build_overall_metrics
from unified_eval.schema import SchemaRegistry
from unified_eval.scoring import score_records

FIXTURES = Path(__file__).parents[1] / "fixtures" / "protocol_v1"


@pytest.fixture
def schema_registry() -> SchemaRegistry:
    return SchemaRegistry(
        dataset="ChFinAnn",
        split="dev",
        event_roles={"EquityPledge": frozenset({"pledger"})},
        schema_hash="sha256:schema",
        split_hash="sha256:split",
    )


def _record() -> FrozenRecord:
    return FrozenRecord(
        dataset="ChFinAnn",
        split="dev",
        document_id="doc_001",
        event_type="EquityPledge",
        record_index=0,
        roles_to_values={"pledger": frozenset({"ACME"})},
    )


def test_t24_chfinann_doc2edag_fixed_sample_loads_official_result() -> None:
    result = chfinann_doc2edag.load_result(
        FIXTURES / "t24_chfinann_doc2edag_official_sample.json",
        evaluator_version="doc2edag-official-v1",
        evaluator_commit_hash="chfinann123",
        command="python official_eval.py pred.json gold.json",
    )

    assert result.to_overall_metrics_block() == {
        "schema_version": OFFICIAL_RESULT_SCHEMA_VERSION,
        "available": True,
        "dataset": "ChFinAnn",
        "metric_name": "ChFinAnn Official F1",
        "evaluator": "chfinann-doc2edag-official",
        "score_type": "official",
        "precision": 0.75,
        "recall": 0.6,
        "f1": 0.6666666666666666,
        "evaluator_version": "doc2edag-official-v1",
        "evaluator_commit_hash": "chfinann123",
        "command": "python official_eval.py pred.json gold.json",
        "source": str(FIXTURES / "t24_chfinann_doc2edag_official_sample.json"),
        "unavailable_reason": "",
        "metadata": {},
        "notes": [],
    }


def test_t24_docfee_fixed_sample_loads_official_result() -> None:
    result = docfee.load_result(
        FIXTURES / "t24_docfee_official_sample.json",
        evaluator_version="docfee-official-v1",
        evaluator_commit_hash="docfee123",
        command="python score_docfee.py pred.json gold.json",
    )

    assert result.to_overall_metrics_block() == {
        "schema_version": OFFICIAL_RESULT_SCHEMA_VERSION,
        "available": True,
        "dataset": "DocFEE",
        "metric_name": "DocFEE Official F1",
        "evaluator": "docfee-official",
        "score_type": "official",
        "precision": 0.5,
        "recall": 0.25,
        "f1": 0.3333333333333333,
        "evaluator_version": "docfee-official-v1",
        "evaluator_commit_hash": "docfee123",
        "command": "python score_docfee.py pred.json gold.json",
        "source": str(FIXTURES / "t24_docfee_official_sample.json"),
        "unavailable_reason": "",
        "metadata": {},
        "notes": [],
    }


def test_duee_fin_online_and_offline_official_style_are_separate() -> None:
    online = duee_fin.online_result(
        precision=0.9,
        recall=0.7,
        f1=0.7875,
        submission_date="2026-05-08",
        source="official-online-platform",
    )
    offline = duee_fin.load_offline_official_style_result(
        FIXTURES / "t24_duee_fin_offline_official_style_sample.json",
        evaluator_version="duee-fin-offline-style-v1",
        evaluator_commit_hash="dueeoffline123",
        command="python duee_fin_offline_eval.py pred.json gold.json",
    )

    online_block = online.to_overall_metrics_block()
    offline_block = offline.to_overall_metrics_block()

    assert online_block["score_type"] == "online_official"
    assert online_block["evaluator"] == "duee-fin-online-official"
    assert online_block["metadata"] == {"submission_date": "2026-05-08"}

    assert offline_block["score_type"] == "offline_official_style"
    assert offline_block["evaluator"] == "duee-fin-offline-official-style"
    assert offline_block["metric_name"] == "DuEE-Fin Offline Official-Style F1"
    assert any(
        "not fully reproducible offline" in note for note in offline_block["notes"]
    )


def test_unavailable_adapter_result_has_stable_available_false_schema() -> None:
    result = chfinann_doc2edag.unavailable("official script is not configured")
    block = result.to_overall_metrics_block()

    assert tuple(block) == OFFICIAL_RESULT_FIELDS
    assert block == {
        "schema_version": OFFICIAL_RESULT_SCHEMA_VERSION,
        "available": False,
        "dataset": "ChFinAnn",
        "metric_name": "ChFinAnn Official F1",
        "evaluator": "chfinann-doc2edag-official",
        "score_type": "unavailable",
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "evaluator_version": "",
        "evaluator_commit_hash": "",
        "command": "",
        "source": "",
        "unavailable_reason": "official script is not configured",
        "metadata": {},
        "notes": [],
    }


def test_overall_metrics_accepts_official_schema_without_replacing_unified_strict(
    schema_registry: SchemaRegistry,
) -> None:
    record = _record()
    scoring_result = score_records((record,), (record,), schema_registry)
    official_result = chfinann_doc2edag.load_result(
        FIXTURES / "t24_chfinann_doc2edag_official_sample.json",
        evaluator_version="doc2edag-official-v1",
        evaluator_commit_hash="chfinann123",
        command="python official_eval.py pred.json gold.json",
    )

    overall = build_overall_metrics(
        ReportArtifactInput(
            schema=schema_registry,
            schema_version="schema-v1",
            split_version="official",
            evaluator_version="dee-eval-v1.0.0",
            scoring_result=scoring_result,
            predictions=(record,),
            golds=(record,),
            normalizer_config={"version": 1},
            official=official_result,
            commit_hash="abc123",
        )
    )

    assert tuple(overall["official"]) == OFFICIAL_RESULT_FIELDS
    assert overall["official"]["score_type"] == "official"
    assert overall["official"]["f1"] == 0.6666666666666666
    assert overall["unified_strict"] == {
        "tp": 1,
        "fp": 0,
        "fn": 0,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
    }
    assert json.dumps(overall, ensure_ascii=False, sort_keys=True)


def test_official_adapters_do_not_import_track_b_matcher_or_scorer() -> None:
    for module in (chfinann_doc2edag, docfee, duee_fin):
        module_path = Path(module.__file__)
        source = module_path.read_text(encoding="utf-8")
        assert "unified_eval.matching" not in source
        assert "unified_eval.scoring" not in source
