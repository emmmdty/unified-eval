from __future__ import annotations

from pathlib import Path


def test_run_all_checks_script_exists_and_runs_required_gates() -> None:
    script = Path("scripts/run_all_checks.sh")

    assert script.is_file()
    assert script.stat().st_mode & 0o111

    body = script.read_text(encoding="utf-8")
    assert "uv run ruff format --check ." in body
    assert "uv run ruff check ." in body
    assert "uv run pytest" in body
