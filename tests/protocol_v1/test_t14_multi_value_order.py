from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t14_multi_value_order(tmp_path: Path) -> None:
    assert_protocol_case("T14", tmp_path)
