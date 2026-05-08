from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from unified_eval.contracts import CanonicalRoleValue

NORMALIZATION_LOG_CSV_FIELDS = ("raw_value", "normalized_value", "applied_rule")

_ALLOWED_STRICT_RULES = frozenset(
    {
        "unicode_nfkc",
        "fullwidth_ascii_to_halfwidth",
        "strip_whitespace",
        "collapse_whitespace",
        "punctuation_to_ascii",
        "remove_thousands_separators",
        "remove_invisible_controls",
    }
)
_THOUSANDS_PATTERN = re.compile(r"(?<!\d)\d{1,3}(?:,\d{3})+(?!\d)")
_WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class NormalizationLogEntry:
    raw_value: str
    normalized_value: str
    applied_rule: str


@dataclass(frozen=True, slots=True)
class NormalizedString:
    raw_value: str
    normalized_value: str
    applied_rules: tuple[str, ...]
    logs: tuple[NormalizationLogEntry, ...]


@dataclass(frozen=True, slots=True)
class NormalizedRoleValue:
    raw_value: CanonicalRoleValue
    normalized_value: CanonicalRoleValue
    logs: tuple[NormalizationLogEntry, ...]

    @property
    def applied_rules(self) -> tuple[str, ...]:
        return _unique_preserving_order(entry.applied_rule for entry in self.logs)


class StrictNormalizer:
    def __init__(self, config: Mapping[str, Any]) -> None:
        _validate_config(config)
        self._config = _json_roundtrip(config)
        self._rule_order = tuple(self._config["rule_order"])
        self._punctuation_map = dict(self._config.get("punctuation_map", {}))
        self._zero_width_chars = frozenset(self._config.get("zero_width_chars", ()))
        self._thousands_separator = self._config.get("thousands_separator", ",")
        self.config_hash = normalization_config_hash(self._config)

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> StrictNormalizer:
        return cls(config)

    @classmethod
    def from_config_path(cls, path: Path | str) -> StrictNormalizer:
        with Path(path).open(encoding="utf-8") as handle:
            config = json.load(handle)
        return cls(config)

    def normalize(self, value: str) -> NormalizedString:
        if not isinstance(value, str):
            raise TypeError("strict normalization accepts strings only")

        original = value
        normalized = value
        applied_rules: list[str] = []

        for rule in self._rule_order:
            before = normalized
            normalized = self._apply_rule(rule, normalized)
            if normalized != before:
                applied_rules.append(rule)

        logs = tuple(
            NormalizationLogEntry(
                raw_value=original,
                normalized_value=normalized,
                applied_rule=rule,
            )
            for rule in applied_rules
        )
        return NormalizedString(
            raw_value=original,
            normalized_value=normalized,
            applied_rules=tuple(applied_rules),
            logs=logs,
        )

    def normalize_role_value(self, value: CanonicalRoleValue) -> NormalizedRoleValue:
        if value is None:
            return NormalizedRoleValue(raw_value=None, normalized_value=None, logs=())
        if isinstance(value, str):
            result = self.normalize(value)
            return NormalizedRoleValue(
                raw_value=value,
                normalized_value=result.normalized_value,
                logs=result.logs,
            )

        normalized_values: list[str] = []
        logs: list[NormalizationLogEntry] = []
        for item in value:
            result = self.normalize(item)
            normalized_values.append(result.normalized_value)
            logs.extend(result.logs)

        return NormalizedRoleValue(
            raw_value=value,
            normalized_value=tuple(normalized_values),
            logs=tuple(logs),
        )

    def _apply_rule(self, rule: str, value: str) -> str:
        if rule == "remove_invisible_controls":
            return self._remove_invisible_controls(value)
        if rule == "fullwidth_ascii_to_halfwidth":
            return _fullwidth_ascii_to_halfwidth(value)
        if rule == "unicode_nfkc":
            return unicodedata.normalize("NFKC", value)
        if rule == "strip_whitespace":
            return value.strip()
        if rule == "collapse_whitespace":
            return _WHITESPACE_PATTERN.sub(" ", value)
        if rule == "punctuation_to_ascii":
            return value.translate(str.maketrans(self._punctuation_map))
        if rule == "remove_thousands_separators":
            return self._remove_thousands_separators(value)
        raise ValueError(f"unsupported strict normalization rule: {rule}")

    def _remove_invisible_controls(self, value: str) -> str:
        return "".join(
            char
            for char in value
            if char not in self._zero_width_chars and not _is_invisible_control(char)
        )

    def _remove_thousands_separators(self, value: str) -> str:
        if self._thousands_separator != ",":
            raise ValueError("strict normalizer v1 only supports comma separators")
        return _THOUSANDS_PATTERN.sub(
            lambda match: match.group(0).replace(",", ""), value
        )


def normalization_config_hash(config: Mapping[str, Any]) -> str:
    payload = json.dumps(
        config,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def normalization_logs_to_csv_rows(
    logs: Sequence[NormalizationLogEntry],
) -> list[dict[str, str]]:
    return [
        {
            "raw_value": entry.raw_value,
            "normalized_value": entry.normalized_value,
            "applied_rule": entry.applied_rule,
        }
        for entry in logs
    ]


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("track") != "unified_strict":
        raise ValueError("strict normalizer config must target unified_strict")

    rule_order = config.get("rule_order")
    if not isinstance(rule_order, list) or not all(
        isinstance(rule, str) for rule in rule_order
    ):
        raise ValueError("strict normalizer config requires rule_order: list[str]")

    disallowed = sorted(set(rule_order) - _ALLOWED_STRICT_RULES)
    if disallowed:
        raise ValueError(f"disallowed strict normalization rules: {disallowed}")
    if len(rule_order) != len(set(rule_order)):
        raise ValueError("strict normalizer rule_order must not contain duplicates")

    punctuation_map = config.get("punctuation_map", {})
    if not isinstance(punctuation_map, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in punctuation_map.items()
    ):
        raise ValueError("punctuation_map must be object[str, str]")

    zero_width_chars = config.get("zero_width_chars", ())
    if not isinstance(zero_width_chars, list) or not all(
        isinstance(char, str) for char in zero_width_chars
    ):
        raise ValueError("zero_width_chars must be list[str]")


def _json_roundtrip(config: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(config, ensure_ascii=False))


def _fullwidth_ascii_to_halfwidth(value: str) -> str:
    return "".join(
        chr(ord(char) - 0xFEE0) if "\uff01" <= char <= "\uff5e" else char
        for char in value
    )


def _is_invisible_control(char: str) -> bool:
    category = unicodedata.category(char)
    return category == "Cf" or (category == "Cc" and not char.isspace())


def _unique_preserving_order(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)
