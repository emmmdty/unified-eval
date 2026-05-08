from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t13_wrong_role_value(tmp_path: Path) -> None:
    assert_protocol_case("T13", tmp_path)
