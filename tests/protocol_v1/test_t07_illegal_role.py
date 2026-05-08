from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t07_illegal_role(tmp_path: Path) -> None:
    assert_protocol_case("T07", tmp_path)
