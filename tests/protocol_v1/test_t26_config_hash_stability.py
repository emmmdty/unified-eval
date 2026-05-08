from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t26_config_hash_stability(tmp_path: Path) -> None:
    assert_protocol_case("T26", tmp_path)
