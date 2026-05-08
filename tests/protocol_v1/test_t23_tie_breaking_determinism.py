from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t23_tie_breaking_determinism(tmp_path: Path) -> None:
    assert_protocol_case("T23", tmp_path)
