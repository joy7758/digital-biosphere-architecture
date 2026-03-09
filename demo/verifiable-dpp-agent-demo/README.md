# Verifiable DPP Agent Demo

A minimal end-to-end demo connecting DPP-style objects, ARO-style audit evidence, and MVK-style deterministic verification.

Workflow:
DPP Object -> Agent Result -> Audit Record -> MVK Input -> Public Evidence Summary

Core related repositories:
- redrock-opendpp-core
- aro-audit
- fdo-kernel-mvk
- token-governor
- digital-biosphere-architecture

Public anchors:
- Paper DOI: 10.5281/zenodo.18501430
- ARO profile: 21.T11966/aro-audit-profile-v1
- ARO demo: 21.T11966/aro-audit-demo-do-1

Usage:
make all

Expected output:
DEMO_BUILD_OK
VERIFY_PASS

Screenshot-ready pages:
- [Demo Results Snapshot](docs/results.md)
- [Poster And QR Sync Copy](docs/poster-sync.md)
- [Print Copy](docs/print-copy.md)
