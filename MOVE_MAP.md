# Move Map

Planned boundary cleanup for `digital-biosphere-architecture`.

## Root Directories

| Source | Destination | Reason |
| --- | --- | --- |
| `demo/verifiable-dpp-agent-demo/` | `archive/legacy-demo/verifiable-dpp-agent-demo/` | Quarantine runnable demo content from the narrative hub |
| `print-final/` | `archive/legacy-event-materials/print-final/` | Remove print output and event collateral from the root surface |
| `outreach/` | `archive/legacy-event-materials/outreach/` | Remove root-level outreach/event material from the canonical hub |
| `scripts/` | `archive/legacy-support-scripts/` | Quarantine legacy support scripts before selectively promoting doc-generation tooling |
| `archive/legacy-support-scripts/render_architecture_diagram.py` | `diagrams/tools/render_architecture_diagram.py` | Keep only diagram-generation tooling in a diagram-scoped location |

## Documentation Moves

| Source | Destination | Reason |
| --- | --- | --- |
| `docs/standard-entry-matrix.md` | `docs/annexes/fdo/standard-entry-matrix.md` | Move FDO annex material out of the primary entry layer |
| `docs/fdo-profile-proposal-entry.md` | `docs/annexes/fdo/fdo-profile-proposal-entry.md` | Move FDO annex material out of the primary entry layer |
| `docs/fdo-terminology-alignment.md` | `docs/annexes/fdo/fdo-terminology-alignment.md` | Move FDO annex material out of the primary entry layer |
| `docs/minimal-fdo-crosswalk.md` | `docs/annexes/fdo/minimal-fdo-crosswalk.md` | Move FDO annex material out of the primary entry layer |
| `docs/execution-evidence-layer-position.md` | `docs/annexes/fdo/execution-evidence-layer-position.md` | Move FDO annex material out of the primary entry layer |
| `docs/vienna-poster-talking-points.md` | `docs/annexes/events/vienna/vienna-poster-talking-points.md` | Move event material out of the primary entry layer |
| `docs/vienna-poster-cn-brief.md` | `docs/annexes/events/vienna/vienna-poster-cn-brief.md` | Move event material out of the primary entry layer |
| `docs/vienna-poster-qa-pack.md` | `docs/annexes/events/vienna/vienna-poster-qa-pack.md` | Move event material out of the primary entry layer |
| `docs/vienna/` | `docs/annexes/events/vienna/` | Consolidate Vienna event scripts into one annex area |
| `docs/governance_architecture_whitepaper.md` | `docs/whitepaper/governance_architecture_whitepaper.md` | Separate long-form whitepaper material from the primary navigation layer |
| `docs/governance_architecture_whitepaper.pdf` | `docs/whitepaper/governance_architecture_whitepaper.pdf` | Separate long-form whitepaper material from the primary navigation layer |

## New Files

- `docs/layer-boundaries.md`
- `docs/start-here.md`
- `docs/core/README.md`
- `docs/redirects/README.md`
- `archive/README.md`
- `FINAL_BOUNDARY_REPORT.md`
