# AGENTS.md

## Highest Authority

`docs/DEE Evaluation Protocol Final.md` is the frozen protocol and has the highest priority for this repository. If any local instruction conflicts with the frozen protocol, follow the frozen protocol.

## Repository Scope

This project implements submission-grade unified evaluation for DuEE-Fin, ChFinAnn, and DocFEE. It must not own dataset preprocessing or dataset splitting.

The sibling data project is `~/myProjects/masterProjects/DEE/data`. Do not modify it from this repository. Copy only explicitly approved, necessary, small artifacts in later phases.

## Phase 0 Boundary

Phase 0 is scaffold and planning only. Do not implement evaluator logic in Phase 0:

- no matching;
- no scoring;
- no normalization;
- no validation logic;
- no official adapter execution.

## Protocol Prohibitions

Do not introduce:

- LLM judge scoring;
- semantic equivalence matching;
- embedding similarity scoring;
- edit-distance or fuzzy matching in the main metric;
- external-KB alias repair;
- schema guessing;
- role guessing;
- event type guessing;
- gold repair;
- prediction repair.

Invalid inputs must never be silently dropped in future evaluator code; they must be counted and logged according to the frozen protocol.

## Tooling

Use the uv toolchain for Python work:

- `uv sync`
- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format .`

Prefer lightweight local verification. Do not run GPU training or GPU inference from this repository.
