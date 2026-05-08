from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t18_zero_score_pair(tmp_path: Path) -> None:
    assert_protocol_case("T18", tmp_path)
