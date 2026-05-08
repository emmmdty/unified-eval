from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path

from unified_eval.normalization import (
    NORMALIZATION_LOG_CSV_FIELDS,
    StrictNormalizer,
    normalization_config_hash,
    normalization_logs_to_csv_rows,
)

STRICT_CONFIG_PATH = Path("configs/strict_normalizer_v1.json")


def test_t19_strict_normalization_allows_only_protocol_character_rules() -> None:
    normalizer = StrictNormalizer.from_config_path(STRICT_CONFIG_PATH)

    prediction = normalizer.normalize(
        "\u200b　“ＡＣＭＥ（中国）股份有限公司”；金额：１，２３４　　万元\n"
    )
    gold = normalizer.normalize('"ACME(中国)股份有限公司";金额:1234 万元')

    assert prediction.normalized_value == gold.normalized_value
    assert set(prediction.applied_rules) >= {
        "collapse_whitespace",
        "fullwidth_ascii_to_halfwidth",
        "punctuation_to_ascii",
        "remove_thousands_separators",
        "remove_invisible_controls",
        "strip_whitespace",
        "unicode_nfkc",
    }


def test_normalization_log_csv_rows_contain_required_protocol_fields() -> None:
    normalizer = StrictNormalizer.from_config_path(STRICT_CONFIG_PATH)

    result = normalizer.normalize("“１，２３４”\u200b")
    rows = normalization_logs_to_csv_rows(result.logs)

    assert rows
    assert set(rows[0]) == set(NORMALIZATION_LOG_CSV_FIELDS)
    assert {row["applied_rule"] for row in rows} >= {
        "fullwidth_ascii_to_halfwidth",
        "punctuation_to_ascii",
        "remove_thousands_separators",
        "remove_invisible_controls",
    }

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(NORMALIZATION_LOG_CSV_FIELDS))
    writer.writeheader()
    writer.writerows(rows)

    csv_text = buffer.getvalue()
    assert "raw_value,normalized_value,applied_rule" in csv_text
    assert "1234" in csv_text


def test_normalization_config_hash_is_stable_for_semantically_same_config() -> None:
    normalizer = StrictNormalizer.from_config_path(STRICT_CONFIG_PATH)
    config = json.loads(STRICT_CONFIG_PATH.read_text(encoding="utf-8"))
    reordered_config = {key: config[key] for key in reversed(config)}

    assert normalizer.config_hash.startswith("sha256:")
    assert normalizer.config_hash == normalization_config_hash(config)
    assert normalizer.config_hash == normalization_config_hash(reordered_config)
    assert normalizer.config_hash == StrictNormalizer.from_config(config).config_hash


def test_t20_auxiliary_date_amount_alias_rules_do_not_affect_unified_strict() -> None:
    normalizer = StrictNormalizer.from_config_path(STRICT_CONFIG_PATH)

    assert (
        normalizer.normalize("2024年1月2日").normalized_value
        != normalizer.normalize("2024-01-02").normalized_value
    )
    assert (
        normalizer.normalize("1000万元").normalized_value
        != normalizer.normalize("1亿元").normalized_value
    )
    assert (
        normalizer.normalize("平安银行").normalized_value
        != normalizer.normalize("平安银行股份有限公司").normalized_value
    )
    assert normalizer.normalize("张 三").normalized_value == "张 三"


def test_t21_no_auto_split_in_unified_strict_normalization() -> None:
    normalizer = StrictNormalizer.from_config_path(STRICT_CONFIG_PATH)

    prediction = normalizer.normalize_role_value("张三、李四")
    gold = normalizer.normalize_role_value(("张三", "李四"))

    assert prediction.normalized_value == "张三、李四"
    assert gold.normalized_value == ("张三", "李四")
    assert prediction.normalized_value != gold.normalized_value


def test_t22_no_external_alias_or_company_short_full_mapping() -> None:
    normalizer = StrictNormalizer.from_config_path(STRICT_CONFIG_PATH)

    short_name = normalizer.normalize_role_value("平安银行")
    full_name = normalizer.normalize_role_value("平安银行股份有限公司")

    assert short_name.normalized_value == "平安银行"
    assert full_name.normalized_value == "平安银行股份有限公司"
    assert short_name.normalized_value != full_name.normalized_value
