from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t08_invalid_json_line(tmp_path: Path) -> None:
    assert_protocol_case("T08", tmp_path)
