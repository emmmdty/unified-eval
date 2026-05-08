from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t27_test_time_mutation_guard(tmp_path: Path) -> None:
    assert_protocol_case("T27", tmp_path)
