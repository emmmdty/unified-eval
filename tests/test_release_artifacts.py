from __future__ import annotations

import json
from pathlib import Path

import pytest

from unified_eval.data_snapshot import sha256_file
from unified_eval.reporting import ARTIFACT_FILENAMES

RELEASE_CASES = (
    ("v0.9.0-rc1", {"0.9.0-rc1", "0.9.0rc1"}),
    ("v1.0.0", {"1.0.0"}),
)
INPUT_FILENAMES = ("gold.jsonl", "pred.jsonl", "schema.json")


@pytest.mark.parametrize(("release", "expected_versions"), RELEASE_CASES)
def test_release_golden_artifact_hash_manifest_matches_files(
    release: str,
    expected_versions: set[str],
) -> None:
    golden_dir = Path("release_artifacts") / release / "golden"
    manifest_path = golden_dir / "artifact_hashes.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files"]

    assert manifest["release"] == release
    assert manifest["package_version"] in expected_versions

    for filename in ARTIFACT_FILENAMES:
        assert filename in files
    for filename in INPUT_FILENAMES:
        assert f"inputs/{filename}" in files

    for relative_path, expected_hash in files.items():
        path = golden_dir / relative_path
        assert path.is_file(), relative_path
        assert sha256_file(path) == expected_hash


@pytest.mark.parametrize(("release", "expected_versions"), RELEASE_CASES)
def test_release_golden_config_records_package_version(
    release: str,
    expected_versions: set[str],
) -> None:
    golden_dir = Path("release_artifacts") / release / "golden"
    config = json.loads((golden_dir / "config.json").read_text(encoding="utf-8"))

    assert config["dependency_versions"]["unified-eval"] in expected_versions
