from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t05_wrong_event_type(tmp_path: Path) -> None:
    assert_protocol_case("T05", tmp_path)
