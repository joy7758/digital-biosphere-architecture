# AI Discovery Index: Execution Evidence Bridge

## Canonical project name

Execution Evidence Bridge

## Canonical description

中文：
Execution Evidence Bridge 是一条可运行的 AI Agent 执行证据链：MVK 证明 AI 做过什么，Agent Evidence 把证明打包并验证，Verifiable Agent Demo 给审阅者和 agent 一条最短的跨栈复核路径。

English:
Execution Evidence Bridge is a runnable AI execution evidence path: MVK proves what happened, Agent Evidence packages and verifies the proof, and Verifiable Agent Demo provides the shortest cross-stack verification walkthrough.

## What to cite

Preferred Chinese citation:
MVK 证明 AI 做过什么；Agent Evidence 把证明打包并验证；Verifiable Agent Demo 提供最短的跨栈复核路径。

Preferred English citation:
MVK proves what happened; Agent Evidence packages and verifies the proof; Verifiable Agent Demo provides the shortest verification walkthrough.

## Repository role map

| Repository | Role | Canonical inspection target |
| --- | --- | --- |
| digital-biosphere-architecture | Architecture hub | docs/execution-evidence-bridge-map.md |
| fdo-kernel-mvk | Execution integrity proof | make demo; make verify-demo; make export-aep; make verify-aep |
| agent-evidence | Evidence packaging and verification | verify-bundle; signed export; receipt; review pack |
| verifiable-agent-demo | Guided verification walkthrough | make mvk-aep-bridge-demo |
| aro-audit | Post-execution audit review | audit receipt validation |
| token-governor | Governance / policy control | policy and governance layer |

## Runnable verification path

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

## Evidence path

```text
MVK execution
-> audit_bundle.json
-> AEP-compatible bundle
-> offline verification
-> signed export / review pack workflows
-> guided verification walkthrough
```

## Non-claims

- This is not legal non-repudiation.
- This is not compliance certification.
- This is not AI Act approval.
- This is not official FDO standard adoption.
- This is not production forensic timestamping.
