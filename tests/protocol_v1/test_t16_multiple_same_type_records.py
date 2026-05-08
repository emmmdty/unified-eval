from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t16_multiple_same_type_records(tmp_path: Path) -> None:
    assert_protocol_case("T16", tmp_path)
