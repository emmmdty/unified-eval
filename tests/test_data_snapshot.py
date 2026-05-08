from __future__ import annotations

from pathlib import Path

import pytest

from unified_eval.data_snapshot import (
    REQUIRED_SOURCE_FILES,
    SnapshotError,
    copy_snapshot,
    verify_snapshot,
)


def _write_required_source_tree(root: Path) -> None:
    for item in REQUIRED_SOURCE_FILES:
        path = root / item.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{item.category}:{item.relative_path}\n", encoding="utf-8")


def test_copy_snapshot_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(SnapshotError, match="source root does not exist"):
        copy_snapshot(tmp_path / "missing-source", tmp_path / "snapshot")


def test_copy_snapshot_rejects_existing_target_without_force(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    _write_required_source_tree(source)
    target.mkdir()
    (target / "existing.txt").write_text("do not overwrite\n", encoding="utf-8")

    with pytest.raises(SnapshotError, match="target already exists"):
        copy_snapshot(source, target)


def test_copy_snapshot_reports_missing_required_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    _write_required_source_tree(source)
    missing = source / REQUIRED_SOURCE_FILES[0].relative_path
    missing.unlink()

    with pytest.raises(SnapshotError, match=REQUIRED_SOURCE_FILES[0].relative_path):
        copy_snapshot(source, target)


def test_copy_snapshot_rejects_target_inside_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _write_required_source_tree(source)

    with pytest.raises(SnapshotError, match="target root must not overlap source root"):
        copy_snapshot(source, source / "data")


def test_verify_snapshot_detects_hash_change(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    _write_required_source_tree(source)

    manifest = copy_snapshot(
        source,
        target,
        copied_at_utc="2026-05-08T00:00:00Z",
    )
    assert manifest["file_count"] == len(REQUIRED_SOURCE_FILES) + 1
    assert verify_snapshot(target)["ok"] is True

    copied_file = target / REQUIRED_SOURCE_FILES[0].relative_path
    original = copied_file.read_text(encoding="utf-8")
    copied_file.write_text("X" + original[1:], encoding="utf-8")

    with pytest.raises(SnapshotError, match="hash mismatch"):
        verify_snapshot(target)
