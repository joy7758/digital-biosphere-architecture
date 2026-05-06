# Execution Evidence Bridge

A runnable bridge from execution integrity proof to portable AI evidence
handoff.

For a compact one-page reviewer brief, see:
[../briefs/execution-evidence-bridge-one-pager.md](../briefs/execution-evidence-bridge-one-pager.md).

## What changed

The stack now has a documented runnable path:

```text
fdo-kernel-mvk
-> audit_bundle.json
-> AEP-compatible bundle
-> agent-evidence verification / signed export / review pack workflows
-> verifiable-agent-demo walkthrough
```

Repository roles:

- `fdo-kernel-mvk`: proves deterministic execution, replay verification,
  checkpoint/checksum integrity, and tamper detection.
- `agent-evidence`: packages and verifies portable evidence artifacts; supports
  signed exports, receipts, offline verification, and review packs.
- `verifiable-agent-demo`: provides the shortest guided walkthrough surface.
- `digital-biosphere-architecture`: maps the layer roles and architecture
  context.

`aro-audit` remains the post-execution audit review surface, and
`token-governor` remains the governance and policy-control surface.

## Why it matters

Ordinary traces are useful for debugging. This path focuses on portable evidence
and independent verification.

Execution integrity proves what happened. Evidence packaging makes that proof
handoff-friendly. The guided walkthrough makes the chain understandable for
reviewers, hiring managers, technical evaluators, and governance readers without
requiring them to read the full stack first.

## How to run

```bash
cd ../fdo-kernel-mvk
make demo
make verify-demo
make export-aep
make verify-aep

cd ../agent-evidence
agent-evidence verify-bundle --bundle-dir ../fdo-kernel-mvk/mvk-aep-bundle

cd ../verifiable-agent-demo
make mvk-aep-bridge-demo
```

## Expected artifacts

- `audit_bundle.json`
- `mvk-aep-bundle/manifest.json`
- `mvk-aep-bundle/records.jsonl`
- `mvk-aep-bundle/mvk-aep-receipt.json`
- optional signed exports / review packs from `agent-evidence`

## What this demonstrates

- deterministic execution artifact generation
- MVK-side replay / integrity verification
- AEP-compatible evidence bundle export
- offline bundle verification
- guided reviewer handoff

## Boundaries and non-claims

- not legal non-repudiation
- not compliance certification
- not AI Act approval
- not official FDO standard adoption
- not production forensic timestamping
- not a substitute for legal, compliance, or security review

## Related links

- [Execution Evidence Bridge Map](../execution-evidence-bridge-map.md)
- [fdo-kernel-mvk PR #8](https://github.com/joy7758/fdo-kernel-mvk/pull/8)
- [agent-evidence PR #73](https://github.com/joy7758/agent-evidence/pull/73)
- [verifiable-agent-demo PR #26](https://github.com/joy7758/verifiable-agent-demo/pull/26)
- [digital-biosphere-architecture PR #7](https://github.com/joy7758/digital-biosphere-architecture/pull/7)
