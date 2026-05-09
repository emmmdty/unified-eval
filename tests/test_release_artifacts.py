from __future__ import annotations

import json
from pathlib import Path

from unified_eval.data_snapshot import sha256_file
from unified_eval.reporting import ARTIFACT_FILENAMES

GOLDEN_DIR = Path("release_artifacts/v0.9.0-rc1/golden")


def test_release_golden_artifact_hash_manifest_matches_files() -> None:
    manifest_path = GOLDEN_DIR / "artifact_hashes.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files"]

    for filename in ARTIFACT_FILENAMES:
        assert filename in files

    for relative_path, expected_hash in files.items():
        path = GOLDEN_DIR / relative_path
        assert path.is_file(), relative_path
        assert sha256_file(path) == expected_hash


def test_release_golden_config_records_rc_package_version() -> None:
    config = json.loads((GOLDEN_DIR / "config.json").read_text(encoding="utf-8"))

    assert config["dependency_versions"]["unified-eval"] in {
        "0.9.0-rc1",
        "0.9.0rc1",
    }
