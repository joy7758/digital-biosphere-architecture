# Execution Evidence Bridge Map

For the reviewer-facing announcement, see:
[docs/announcements/execution-evidence-bridge.md](announcements/execution-evidence-bridge.md).

## Layer roles

```text
Architecture hub: digital-biosphere-architecture
Execution integrity: fdo-kernel-mvk
Evidence packaging: agent-evidence
Guided walkthrough: verifiable-agent-demo
Post-execution audit: aro-audit
Governance: token-governor
```

## Runnable path

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

## What this proves

- deterministic execution artifact generated
- MVK audit bundle verified
- AEP-compatible bundle exported
- bundle integrity verified offline
- guided demo documents the handoff

## What this does not claim

- not legal non-repudiation
- not compliance certification
- not AI Act approval
- not official FDO standard adoption
- not a production forensic timestamping system

## Related PRs

- fdo-kernel-mvk: [https://github.com/joy7758/fdo-kernel-mvk/pull/8](https://github.com/joy7758/fdo-kernel-mvk/pull/8)
- agent-evidence: [https://github.com/joy7758/agent-evidence/pull/73](https://github.com/joy7758/agent-evidence/pull/73)
- verifiable-agent-demo: [https://github.com/joy7758/verifiable-agent-demo/pull/26](https://github.com/joy7758/verifiable-agent-demo/pull/26)
