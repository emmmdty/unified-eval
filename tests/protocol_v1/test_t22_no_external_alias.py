from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t22_no_external_alias(tmp_path: Path) -> None:
    assert_protocol_case("T22", tmp_path)
