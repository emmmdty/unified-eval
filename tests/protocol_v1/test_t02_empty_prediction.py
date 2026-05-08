from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t02_empty_prediction(tmp_path: Path) -> None:
    assert_protocol_case("T02", tmp_path)
