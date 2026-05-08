from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t09_invalid_record(tmp_path: Path) -> None:
    assert_protocol_case("T09", tmp_path)
