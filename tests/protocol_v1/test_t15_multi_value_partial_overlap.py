from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t15_multi_value_partial_overlap(tmp_path: Path) -> None:
    assert_protocol_case("T15", tmp_path)
