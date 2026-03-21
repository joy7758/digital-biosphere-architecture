# Final Boundary Report

- root cleaned? yes
  Root directories now resolve to `archive/`, `assets/`, `diagrams/`, and `docs/`.
- demo quarantined? yes
  `demo/verifiable-dpp-agent-demo/` moved to `archive/legacy-demo/verifiable-dpp-agent-demo/`.
- event materials quarantined? yes
  `print-final/` moved to `archive/legacy-event-materials/print-final/`, and the root `outreach/` shell was removed from the canonical surface.
- docs annex separated? yes
  FDO proposal material moved to `docs/annexes/fdo/`, Vienna material moved to `docs/annexes/events/vienna/`, and the whitepaper moved to `docs/whitepaper/`.
- README normalized? yes
  The root README now uses the required `Role`, `Not this repo`, `Canonical Stack`, `Start here`, `Depends on`, `Annexes / historical context`, and `Status` structure.
- start-here path unique? yes
  `docs/start-here.md` now gives one explicit reading order from this hub to POP, AIP, Token Governor, MVK, Agent Evidence, ARO-Audit, and the demo.
- remaining risks
  Direct external links to the old PDF path `docs/governance_architecture_whitepaper.pdf` cannot be redirected with a markdown stub and will need callers to update.
  `docs/outreach/` remains as secondary context inside `docs/`; it no longer occupies the README entry surface, but it is still narrative-adjacent material rather than core stack documentation.
