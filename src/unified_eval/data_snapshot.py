from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DATASETS = ("DuEE-Fin-dev500", "ChFinAnn", "DocFEE-dev1000")
DEFAULT_SOURCE_ROOT = Path("~/myProjects/masterProjects/DEE/data").expanduser()
DEFAULT_TARGET_ROOT = Path("data")
MANIFEST_NAME = "snapshot_manifest.json"
README_NAME = "README.md"
HASH_METHOD = "sha256"


class SnapshotError(RuntimeError):
    """Raised when a data snapshot cannot be copied or verified."""


@dataclass(frozen=True, slots=True)
class SourceFile:
    relative_path: str
    category: str


def _source_files() -> tuple[SourceFile, ...]:
    files: list[SourceFile] = [
        SourceFile("processed/PROCESSING_SUMMARY.json", "source_stats_manifest"),
        SourceFile("processed/PROCESSING_SUMMARY.md", "source_stats_manifest"),
        SourceFile("reports/RAW_SOURCE_MANIFEST.json", "source_hash_manifest"),
        SourceFile("reports/raw_inspection.json", "source_stats_manifest"),
        SourceFile("reports/raw_inspection.md", "source_stats_manifest"),
        SourceFile("reports/raw_format_warnings.jsonl", "source_stats_manifest"),
        SourceFile("raw/DocFEE/sample.json", "sample"),
        SourceFile("raw/DocFEE/schema.json", "official_adapter_sample"),
        SourceFile("raw/DuEE-Fin/duee_fin_sample.json", "sample"),
        SourceFile(
            "raw/DuEE-Fin/duee_fin_event_schema.json", "official_adapter_sample"
        ),
        SourceFile("raw/ChFinAnn/schema.json", "official_adapter_sample"),
        SourceFile(
            "processed/ChFinAnn_Doc2EDAG/schema.json",
            "official_adapter_sample",
        ),
        SourceFile(
            "reports/chfinann_doc2edag_reference_inspection.json",
            "official_adapter_sample",
        ),
        SourceFile(
            "reports/chfinann_doc2edag_reference_inspection.md",
            "official_adapter_sample",
        ),
        SourceFile(
            "evaluation/examples/DocFEE-dev1000_test_pred_empty.jsonl",
            "official_adapter_sample",
        ),
    ]

    for dataset in DATASETS:
        for name in (
            "schema.json",
            "split_manifest.json",
            "stats.json",
            "stats.md",
            "validation_report.json",
            "validation_report.md",
        ):
            files.append(SourceFile(f"processed/{dataset}/{name}", _category_for(name)))

        for name in (
            "schema.json",
            "train.jsonl",
            "dev.jsonl",
            "test.jsonl",
            "view_manifest.json",
            "view_stats.json",
            "validation_report.json",
            "validation_report.md",
            "view_warnings.jsonl",
        ):
            files.append(
                SourceFile(
                    f"processed/views/evaluator_gold/{dataset}/{name}",
                    "evaluator_gold",
                )
            )

    return tuple(files)


def _category_for(filename: str) -> str:
    if filename == "schema.json":
        return "schema"
    if filename == "split_manifest.json":
        return "split_manifest"
    if filename.startswith("stats") or filename.startswith("validation"):
        return "source_stats_manifest"
    return "source_metadata"


REQUIRED_SOURCE_FILES = _source_files()


def copy_snapshot(
    source_root: Path | str = DEFAULT_SOURCE_ROOT,
    target_root: Path | str = DEFAULT_TARGET_ROOT,
    *,
    copied_at_utc: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    source = Path(source_root).expanduser()
    target = Path(target_root).expanduser()
    copied_at = copied_at_utc or datetime.now(UTC).replace(microsecond=0).isoformat()

    _validate_source_root(source)
    _prepare_target_root(source, target, force=force)
    _validate_required_files(source)

    copied_files: list[dict[str, Any]] = []
    target.mkdir(parents=True, exist_ok=True)

    for item in REQUIRED_SOURCE_FILES:
        source_file = source / item.relative_path
        destination_file = target / item.relative_path
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination_file, follow_symlinks=False)
        copied_files.append(
            _manifest_entry(source, target, item, source_file, destination_file)
        )

    readme_path = target / README_NAME
    readme_path.write_text(
        _render_readme(
            source=source,
            target=target,
            copied_at=copied_at,
            copied_files=copied_files,
        ),
        encoding="utf-8",
    )
    copied_files.append(
        _generated_manifest_entry(
            target=target,
            relative_path=README_NAME,
            category="snapshot_readme",
        )
    )

    manifest = {
        "schema_version": "unified-eval-data-snapshot-v1",
        "created_at_utc": copied_at,
        "source_root": str(source.resolve()),
        "snapshot_root": str(target.resolve()),
        "hash_method": HASH_METHOD,
        "datasets": list(DATASETS),
        "file_count": len(copied_files),
        "files": copied_files,
        "notes": [
            "No train/dev/test split membership is changed.",
            "Gold files and schemas are copied byte-for-byte without repair.",
            "Raw large train/dev/test files are not part of this allowlist.",
        ],
    }
    (target / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def verify_snapshot(snapshot_root: Path | str = DEFAULT_TARGET_ROOT) -> dict[str, Any]:
    root = Path(snapshot_root).expanduser()
    manifest_path = root / MANIFEST_NAME

    if not root.exists():
        raise SnapshotError(f"snapshot root does not exist: {root}")
    if not manifest_path.is_file():
        raise SnapshotError(f"snapshot manifest does not exist: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("hash_method") != HASH_METHOD:
        raise SnapshotError(
            f"unsupported hash method in manifest: {manifest.get('hash_method')!r}"
        )

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise SnapshotError("snapshot manifest has no file entries")

    checked = 0
    for entry in files:
        relative_path = entry.get("relative_path")
        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes")
        if not isinstance(relative_path, str) or not isinstance(expected_hash, str):
            raise SnapshotError(f"invalid manifest file entry: {entry!r}")
        path = root / relative_path
        if path.is_symlink():
            raise SnapshotError(f"snapshot file is a symlink: {relative_path}")
        if not path.is_file():
            raise SnapshotError(f"snapshot file is missing: {relative_path}")
        actual_size = path.stat().st_size
        if expected_size != actual_size:
            raise SnapshotError(
                f"size mismatch for {relative_path}: "
                f"expected {expected_size}, got {actual_size}"
            )
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise SnapshotError(
                f"hash mismatch for {relative_path}: "
                f"expected {expected_hash}, got {actual_hash}"
            )
        checked += 1

    return {
        "ok": True,
        "snapshot_root": str(root.resolve()),
        "manifest": str(manifest_path.resolve()),
        "hash_method": HASH_METHOD,
        "checked_files": checked,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_source_root(source: Path) -> None:
    if not source.exists():
        raise SnapshotError(f"source root does not exist: {source}")
    if not source.is_dir():
        raise SnapshotError(f"source root is not a directory: {source}")


def _prepare_target_root(source: Path, target: Path, *, force: bool) -> None:
    source_resolved = source.resolve()
    target_resolved = target.resolve(strict=False)
    if (
        source_resolved == target_resolved
        or target_resolved.is_relative_to(source_resolved)
        or source_resolved.is_relative_to(target_resolved)
    ):
        raise SnapshotError("target root must not overlap source root")
    if target.exists() and any(target.iterdir()):
        if not force:
            raise SnapshotError(f"target already exists and is not empty: {target}")
        shutil.rmtree(target)


def _validate_required_files(source: Path) -> None:
    missing: list[str] = []
    symlinks: list[str] = []
    for item in REQUIRED_SOURCE_FILES:
        path = source / item.relative_path
        if path.is_symlink():
            symlinks.append(item.relative_path)
        elif not path.is_file():
            missing.append(item.relative_path)
    if missing or symlinks:
        parts = []
        if missing:
            parts.append("missing required files: " + ", ".join(missing))
        if symlinks:
            parts.append("symlink sources are not allowed: " + ", ".join(symlinks))
        raise SnapshotError("; ".join(parts))


def _manifest_entry(
    source_root: Path,
    target_root: Path,
    item: SourceFile,
    source_file: Path,
    destination_file: Path,
) -> dict[str, Any]:
    stat = destination_file.stat()
    return {
        "relative_path": item.relative_path,
        "category": item.category,
        "source_path": str(source_file.resolve()),
        "snapshot_path": str(destination_file.resolve()),
        "source_relative_path": str(source_file.relative_to(source_root)),
        "snapshot_relative_path": str(destination_file.relative_to(target_root)),
        "size_bytes": stat.st_size,
        "sha256": sha256_file(destination_file),
    }


def _generated_manifest_entry(
    target: Path,
    relative_path: str,
    category: str,
) -> dict[str, Any]:
    path = target / relative_path
    stat = path.stat()
    return {
        "relative_path": relative_path,
        "category": category,
        "source_path": None,
        "snapshot_path": str(path.resolve()),
        "source_relative_path": None,
        "snapshot_relative_path": relative_path,
        "size_bytes": stat.st_size,
        "sha256": sha256_file(path),
    }


def _render_readme(
    *,
    source: Path,
    target: Path,
    copied_at: str,
    copied_files: list[dict[str, Any]],
) -> str:
    category_counts: dict[str, int] = {}
    total_bytes = 0
    for entry in copied_files:
        category = str(entry["category"])
        category_counts[category] = category_counts.get(category, 0) + 1
        total_bytes += int(entry["size_bytes"])

    categories = "\n".join(
        f"- {category}: {count} files"
        for category, count in sorted(category_counts.items())
    )

    return f"""# Data Snapshot

This directory is an isolated copy of the files required by `unified-eval`.

- Source path: `{source.resolve()}`
- Snapshot path: `{target.resolve()}`
- Copy time UTC: `{copied_at}`
- Hash method: `{HASH_METHOD}` over file bytes
- Snapshot manifest: `{MANIFEST_NAME}`
- Copied source files: {len(copied_files)}
- Copied source bytes: {total_bytes}

## Categories

{categories}

## Boundaries

- The copy process does not modify the source directory.
- The copy process does not create symlinks.
- The copy process does not re-split train/dev/test.
- The copy process does not repair gold files.
- The copy process does not edit schemas.
- The copy process does not copy complete raw train/dev/test files.
- The generated `data/` tree is ignored by Git and is intended as a local snapshot.
"""


def copy_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy the isolated evaluator data snapshot."
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    manifest = copy_snapshot(args.source_root, args.target_root, force=args.force)
    print(
        json.dumps(
            _copy_summary(manifest), ensure_ascii=False, indent=2, sort_keys=True
        )
    )
    return 0


def verify_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the isolated evaluator data snapshot."
    )
    parser.add_argument("--snapshot-root", type=Path, default=DEFAULT_TARGET_ROOT)
    args = parser.parse_args(argv)

    result = verify_snapshot(args.snapshot_root)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _copy_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "source_root": manifest["source_root"],
        "snapshot_root": manifest["snapshot_root"],
        "manifest": str(Path(manifest["snapshot_root"]) / MANIFEST_NAME),
        "hash_method": manifest["hash_method"],
        "file_count": manifest["file_count"],
    }
