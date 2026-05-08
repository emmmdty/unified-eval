from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t28_silent_drop_guard(tmp_path: Path) -> None:
    assert_protocol_case("T28", tmp_path)
