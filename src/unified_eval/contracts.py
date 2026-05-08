from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

CanonicalRoleValue: TypeAlias = str | tuple[str, ...] | None
RecordsField: TypeAlias = Literal["predictions", "gold_events"]


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    line_number: int | None = None
    document_id: str | None = None
    record_index: int | None = None
    event_type: str | None = None
    role: str | None = None
    raw_value: Any = None


class ContractValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue] | tuple[ValidationIssue, ...]):
        self.issues = tuple(issues)
        summary = "; ".join(f"{issue.code}: {issue.message}" for issue in self.issues)
        super().__init__(summary or "canonical contract validation failed")


@dataclass(frozen=True, slots=True)
class CanonicalRecord:
    event_type: str
    arguments: dict[str, CanonicalRoleValue]
    event_id: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalDocument:
    dataset: str
    split: str
    document_id: str
    records_field: RecordsField
    records: tuple[CanonicalRecord, ...]
