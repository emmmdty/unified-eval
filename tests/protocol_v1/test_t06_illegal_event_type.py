from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t06_illegal_event_type(tmp_path: Path) -> None:
    assert_protocol_case("T06", tmp_path)
