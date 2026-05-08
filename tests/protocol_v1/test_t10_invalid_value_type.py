from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t10_invalid_value_type(tmp_path: Path) -> None:
    assert_protocol_case("T10", tmp_path)
