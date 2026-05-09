# Scripts

This directory contains thin repository-maintenance and release helpers. Core
evaluation behavior lives in `src/unified_eval/`; scripts must remain wrappers
around package code or explicit snapshot/release operations.

- `copy_data_snapshot.py`: copies the approved small allowlist from
  `~/myProjects/masterProjects/DEE/data` into ignored local `data/`.
- `verify_data_snapshot.py`: verifies the copied snapshot manifest and file
  hashes.
- `run_all_checks.sh`: runs the local format, lint, and pytest gate.
- `generate_release_golden.py`: regenerates the public v1.0.0 toy CLI
  golden artifact set and hash manifest.

These scripts must follow `docs/DEE Evaluation Protocol Final.md`. They must
not create dataset splits, repair gold or prediction data, or implement
dataset-official evaluator runners.
