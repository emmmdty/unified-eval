from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t25_unified_regression(tmp_path: Path) -> None:
    assert_protocol_case("T25", tmp_path)
