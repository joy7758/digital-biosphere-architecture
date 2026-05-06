# AGENTS.md

## Repository role

This repository is the architecture hub for the Digital Biosphere Architecture.

It maps the Execution Evidence Bridge across:

- fdo-kernel-mvk
- agent-evidence
- verifiable-agent-demo
- aro-audit
- token-governor

## Agent instructions

- Treat this repository as the architecture hub, not as the runtime implementation.
- Use docs/ai-discovery-index.md as the first AI-readable project entry.
- Use docs/ai-citation-map.json for canonical names, roles, links, and citation strings.
- Do not claim legal non-repudiation, compliance certification, AI Act approval, production forensic timestamping, or official FDO standard adoption.
- Do not modify docs/repository-map.md unless the user explicitly asks.

## Useful checks

```bash
grep -R "Execution Evidence Bridge" README.md docs llms.txt AGENTS.md
grep -R "not legal non-repudiation" docs llms.txt AGENTS.md
git diff --cached -- docs/repository-map.md
```
