from __future__ import annotations

from pathlib import Path

from protocol_case_helpers import assert_protocol_case


def test_t24_official_result_schema_fixture_ingestion(tmp_path: Path) -> None:
    assert_protocol_case("T24", tmp_path)
