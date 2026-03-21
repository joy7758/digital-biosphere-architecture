# Root Inventory

Pre-refactor snapshot for the `fix/dba-boundary-hub` branch.

## Root Surface Before Cleanup

- `README.md`
- `LICENSE`
- `.gitignore`
- `assets/`
- `demo/`
- `diagrams/`
- `docs/`
- `outreach/`
- `print-final/`
- `scripts/`

## Boundary Problems Observed

- `demo/verifiable-dpp-agent-demo/` is a runnable demo subtree with its own `Makefile`, `scripts/`, `input/`, and `output/`.
- `print-final/` and `outreach/` are event and presentation materials, not narrative-hub primitives.
- `scripts/` mixes generation support into the root instead of a documentation or diagram tooling area.
- `README.md` currently mixes canonical stack navigation with FDO proposal materials, Vienna event materials, and whitepaper links at the same entry layer.

## Canonical Hub Target

After cleanup, the root should present only the narrative-hub surface:

- `README.md`
- `LICENSE`
- `.gitignore`
- `assets/`
- `diagrams/`
- `docs/`
- `archive/`
