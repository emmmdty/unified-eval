# Unified Eval

`unified-eval` is a protocol-first repository for Chinese financial document-level event extraction evaluation over DuEE-Fin, ChFinAnn, and DocFEE.

The frozen authority is `docs/DEE Evaluation Protocol Final.md`. Implementations must follow that protocol exactly.

## Phase 0 Status

This repository is initialized as a scaffold only.

Phase 0 includes:

- uv-managed Python project metadata;
- an importable `unified_eval` package;
- a smoke test;
- repository docs and command wiring.

Phase 0 does not include:

- matching, scoring, validation, or normalization logic;
- Track A official adapter implementations;
- copied dataset files;
- dataset splitting or data preprocessing.

## Boundaries

- Do not modify `~/myProjects/masterProjects/DEE/data`.
- Do not copy large files into this repository.
- Do not implement LLM judge scoring, semantic matching, embedding similarity, alias repair, schema guessing, role guessing, event type guessing, gold repair, or prediction repair.
- Keep Track A official metrics and Track B unified strict metrics separate.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
make check
```
