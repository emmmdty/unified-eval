from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from unified_eval import __version__
from unified_eval.data_snapshot import sha256_file
from unified_eval.reporting import ARTIFACT_FILENAMES

DEFAULT_OUTPUT_DIR = Path("release_artifacts/v1.0.0/golden")
REPO_ROOT = Path(__file__).resolve().parents[1]
NORMALIZER_CONFIG = REPO_ROOT / "configs" / "strict_normalizer_v1.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the v1.0.0 public toy CLI golden artifacts."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the golden artifact set is written.",
    )
    args = parser.parse_args(argv)

    output_dir = args.output_dir.resolve()
    inputs_dir = output_dir / "inputs"
    _prepare_output_dir(output_dir, inputs_dir)

    schema_path = _write_json(
        inputs_dir / "schema.json",
        {
            "canonical_version": "v1.0",
            "dataset": "ChFinAnn",
            "event_types": [
                {"event_type": "EquityPledge", "roles": ["Pledger", "Pledgee"]},
                {"event_type": "EquityRepurchase", "roles": ["CompanyName"]},
            ],
        },
    )
    gold_path = _write_jsonl(
        inputs_dir / "gold.jsonl",
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
    pred_path = _write_jsonl(
        inputs_dir / "pred.jsonl",
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

    with tempfile.TemporaryDirectory(prefix="unified-eval-golden-") as cwd:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "unified_eval.protocol_v1",
                "--dataset",
                "ChFinAnn",
                "--split",
                "dev",
                "--schema",
                str(schema_path),
                "--gold",
                str(gold_path),
                "--pred",
                str(pred_path),
                "--output-dir",
                str(output_dir),
                "--normalizer-config",
                str(NORMALIZER_CONFIG),
            ],
            check=True,
            cwd=cwd,
        )

    _normalize_csv_line_endings(output_dir)
    _write_hash_manifest(output_dir)
    print(f"wrote release golden artifacts to {output_dir}")
    return 0


def _prepare_output_dir(output_dir: Path, inputs_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(parents=True, exist_ok=True)
    for filename in (*ARTIFACT_FILENAMES, "artifact_hashes.json"):
        path = output_dir / filename
        if path.exists():
            path.unlink()
    for filename in ("schema.json", "gold.jsonl", "pred.jsonl"):
        path = inputs_dir / filename
        if path.exists():
            path.unlink()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
    )
    return path


def _normalize_csv_line_endings(output_dir: Path) -> None:
    for filename in ARTIFACT_FILENAMES:
        if filename.endswith(".csv"):
            path = output_dir / filename
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


def _write_hash_manifest(output_dir: Path) -> None:
    files = {
        filename: sha256_file(output_dir / filename) for filename in ARTIFACT_FILENAMES
    }
    files.update(
        {
            f"inputs/{filename}": sha256_file(output_dir / "inputs" / filename)
            for filename in ("schema.json", "gold.jsonl", "pred.jsonl")
        }
    )
    _write_json(
        output_dir / "artifact_hashes.json",
        {
            "release": "v1.0.0",
            "hash_method": "sha256",
            "generated_by": "scripts/generate_release_golden.py",
            "package_version": __version__,
            "files": dict(sorted(files.items())),
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
