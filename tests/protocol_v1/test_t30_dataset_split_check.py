from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t30_dataset_split_check(tmp_path: Path) -> None:
    assert_protocol_case("T30", tmp_path)
