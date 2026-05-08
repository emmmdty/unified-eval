from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from unified_eval.reporting import ARTIFACT_FILENAMES


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def cli_fixture(tmp_path: Path) -> dict[str, Path]:
    schema = _write_json(
        tmp_path / "schema.json",
        {
            "canonical_version": "v1.0",
            "dataset": "ChFinAnn",
            "event_types": [
                {"event_type": "EquityPledge", "roles": ["Pledger", "Pledgee"]},
                {"event_type": "EquityRepurchase", "roles": ["CompanyName"]},
            ],
        },
    )
    gold = _write_jsonl(
        tmp_path / "dev.jsonl",
        [
            {
                "doc_id": "doc_001",
                "dataset": "ChFinAnn",
                "split": "dev",
                "events": [
                    {
                        "event_id": "gold-1",
                        "event_type": "EquityPledge",
                        "arguments": {
                            "Pledger": [{"text": "张三", "norm_text": "张三"}],
                            "Pledgee": [{"text": "李四", "norm_text": "李四"}],
                        },
                    }
                ],
            },
            {
                "doc_id": "doc_002",
                "dataset": "ChFinAnn",
                "split": "dev",
                "events": [
                    {
                        "event_id": "gold-2",
                        "event_type": "EquityRepurchase",
                        "arguments": {
                            "CompanyName": [{"text": "示例股份有限公司"}],
                        },
                    }
                ],
            },
        ],
    )
    toy_pred = _write_jsonl(
        tmp_path / "toy_pred.jsonl",
        [
            {
                "document_id": "doc_001",
                "predictions": [
                    {
                        "event_type": "EquityPledge",
                        "arguments": {"Pledger": "张三", "Pledgee": "WRONG"},
                    }
                ],
            },
            {"document_id": "doc_002", "predictions": []},
        ],
    )
    gold_as_pred = _write_jsonl(
        tmp_path / "gold_as_pred.jsonl",
        [
            {
                "document_id": "doc_001",
                "predictions": [
                    {
                        "event_type": "EquityPledge",
                        "arguments": {"Pledger": ["张三"], "Pledgee": ["李四"]},
                    }
                ],
            },
            {
                "document_id": "doc_002",
                "predictions": [
                    {
                        "event_type": "EquityRepurchase",
                        "arguments": {"CompanyName": "示例股份有限公司"},
                    }
                ],
            },
        ],
    )
    empty_pred = _write_jsonl(
        tmp_path / "empty_pred.jsonl",
        [
            {"document_id": "doc_001", "predictions": []},
            {"document_id": "doc_002", "predictions": []},
        ],
    )
    return {
        "schema": schema,
        "gold": gold,
        "toy_pred": toy_pred,
        "gold_as_pred": gold_as_pred,
        "empty_pred": empty_pred,
    }


def _run_cli(
    tmp_path: Path,
    fixture: dict[str, Path],
    *,
    pred_name: str,
    output_name: str,
    dataset: str = "ChFinAnn",
    split: str = "dev",
) -> subprocess.CompletedProcess[str]:
    output_dir = tmp_path / output_name
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "unified_eval.protocol_v1",
            "--dataset",
            dataset,
            "--split",
            split,
            "--schema",
            str(fixture["schema"]),
            "--gold",
            str(fixture["gold"]),
            "--pred",
            str(fixture[pred_name]),
            "--output-dir",
            str(output_dir),
        ],
        check=False,
        cwd=Path(__file__).parents[2],
        text=True,
        capture_output=True,
    )


def _overall(output_dir: Path) -> dict[str, Any]:
    return json.loads((output_dir / "overall_metrics.json").read_text())


def test_cli_writes_required_artifacts_for_toy_prediction(
    tmp_path: Path,
    cli_fixture: dict[str, Path],
) -> None:
    result = _run_cli(
        tmp_path,
        cli_fixture,
        pred_name="toy_pred",
        output_name="toy_output",
    )

    assert result.returncode == 0, result.stderr
    output_dir = tmp_path / "toy_output"
    assert set(path.name for path in output_dir.iterdir()) == set(ARTIFACT_FILENAMES)
    overall = _overall(output_dir)
    assert overall["dataset"] == "ChFinAnn"
    assert overall["split"] == "dev"
    assert overall["official"]["available"] is False
    assert overall["unified_strict"]["tp"] == 1
    assert overall["unified_strict"]["fp"] == 1
    assert overall["unified_strict"]["fn"] == 2
    assert "wrote protocol-v1 artifacts" in result.stdout


def test_cli_gold_vs_gold_outputs_f1_one(
    tmp_path: Path,
    cli_fixture: dict[str, Path],
) -> None:
    result = _run_cli(
        tmp_path,
        cli_fixture,
        pred_name="gold_as_pred",
        output_name="gold_vs_gold",
    )

    assert result.returncode == 0, result.stderr
    overall = _overall(tmp_path / "gold_vs_gold")
    assert overall["unified_strict"] == {
        "tp": 3,
        "fp": 0,
        "fn": 0,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
    }


def test_cli_empty_prediction_outputs_fn(
    tmp_path: Path,
    cli_fixture: dict[str, Path],
) -> None:
    result = _run_cli(
        tmp_path,
        cli_fixture,
        pred_name="empty_pred",
        output_name="empty_output",
    )

    assert result.returncode == 0, result.stderr
    output_dir = tmp_path / "empty_output"
    overall = _overall(output_dir)
    assert overall["unified_strict"]["tp"] == 0
    assert overall["unified_strict"]["fp"] == 0
    assert overall["unified_strict"]["fn"] == 3
    with (output_dir / "error_cases.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["case_type"] for row in rows} == {"FN"}


def test_cli_rejects_dataset_mismatch_with_clear_error(
    tmp_path: Path,
    cli_fixture: dict[str, Path],
) -> None:
    result = _run_cli(
        tmp_path,
        cli_fixture,
        pred_name="toy_pred",
        output_name="bad_dataset",
        dataset="DocFEE",
    )

    assert result.returncode == 2
    assert "dataset mismatch" in result.stderr
    assert "explicit --dataset DocFEE" in result.stderr
    assert not (tmp_path / "bad_dataset").exists()
