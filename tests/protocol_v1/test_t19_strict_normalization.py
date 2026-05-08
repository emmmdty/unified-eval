from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t19_strict_normalization(tmp_path: Path) -> None:
    assert_protocol_case("T19", tmp_path)
