from __future__ import annotations

from collections.abc import Mapping, Set
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SchemaRegistry:
    dataset: str
    split: str
    event_roles: Mapping[str, Set[str]]
    schema_hash: str
    split_hash: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.dataset, "dataset")
        _require_nonempty_string(self.split, "split")
        _require_nonempty_string(self.schema_hash, "schema_hash")
        _require_nonempty_string(self.split_hash, "split_hash")

        normalized: dict[str, frozenset[str]] = {}
        for event_type, roles in self.event_roles.items():
            _require_nonempty_string(event_type, "event_type")
            normalized_roles = frozenset(roles)
            for role in normalized_roles:
                _require_nonempty_string(role, "role")
            normalized[event_type] = normalized_roles

        object.__setattr__(self, "event_roles", normalized)

    @property
    def legal_event_types(self) -> frozenset[str]:
        return frozenset(self.event_roles)

    def has_event_type(self, event_type: str) -> bool:
        return event_type in self.event_roles

    def legal_roles(self, event_type: str) -> frozenset[str]:
        try:
            return frozenset(self.event_roles[event_type])
        except KeyError as exc:
            raise KeyError(f"unknown event type: {event_type}") from exc

    def has_role(self, event_type: str, role: str) -> bool:
        return role in self.event_roles.get(event_type, frozenset())


def _require_nonempty_string(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
