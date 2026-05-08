from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t17_greedy_vs_hungarian_difference(tmp_path: Path) -> None:
    assert_protocol_case("T17", tmp_path)
