from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t20_auxiliary_normalization_isolation(tmp_path: Path) -> None:
    assert_protocol_case("T20", tmp_path)
