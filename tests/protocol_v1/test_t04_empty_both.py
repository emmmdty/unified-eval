from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t04_empty_both(tmp_path: Path) -> None:
    assert_protocol_case("T04", tmp_path)
