from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t21_no_auto_split(tmp_path: Path) -> None:
    assert_protocol_case("T21", tmp_path)
