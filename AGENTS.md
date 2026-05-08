# AGENTS.md

## Highest Authority

`docs/DEE Evaluation Protocol Final.md` is the frozen protocol and has the highest priority for this repository. If any local instruction conflicts with the frozen protocol, follow the frozen protocol.

## Core Rules

1. The frozen protocol in `docs/DEE Evaluation Protocol Final.md` is the highest-priority project specification.
2. This repository implements only the unified evaluator and official metric adapters. It does not create or modify dataset splits.
3. The source data project at `~/myProjects/masterProjects/DEE/data` is read-only. Never modify it.
4. Data needed by this project must be copied into `unified-eval/data/` through explicit snapshot scripts.
5. Do not implement schema guessing, role guessing, event type guessing, gold repair, prediction repair, semantic equivalence, LLM judge, embedding similarity, fuzzy matching, or external alias normalization in the main metric.
6. The main Track B metric is Unified Strict Role-Value Micro-F1 under Event-Type-Constrained Hungarian Matching.
7. Track A official metrics and Track B unified strict metrics must remain separate.
8. Every protocol behavior must be backed by tests, especially T01-T30.
9. Never silently drop invalid JSON, invalid event types, invalid roles, invalid values, duplicates, or malformed predictions.
10. Do not change evaluator behavior after inspecting test results; create a new protocol version instead.

## Repository Scope

This project implements submission-grade unified evaluation for DuEE-Fin, ChFinAnn, and DocFEE. It must not own dataset preprocessing or dataset splitting.

The sibling data project is `~/myProjects/masterProjects/DEE/data`. Do not modify it from this repository. Copy only explicitly approved, necessary artifacts through `scripts/copy_data_snapshot.py`.

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
