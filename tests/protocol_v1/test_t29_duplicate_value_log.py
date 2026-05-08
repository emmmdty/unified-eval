from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t29_duplicate_value_log(tmp_path: Path) -> None:
    assert_protocol_case("T29", tmp_path)
