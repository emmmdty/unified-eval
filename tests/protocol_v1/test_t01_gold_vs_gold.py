from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t01_gold_vs_gold(tmp_path: Path) -> None:
    assert_protocol_case("T01", tmp_path)
