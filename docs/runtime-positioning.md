# Runtime Positioning

## What Digital Biosphere Architecture is

Digital Biosphere Architecture is a parent architecture and narrative hub for
verifiable AI systems. It gives the ecosystem a common reading order for
persona, governance, execution integrity, and audit evidence without forcing
those concerns into one repository or one runtime.

## What it is not

It is not a monolithic agent framework, not a single protocol, and not a
mandatory deployment model. It is a working draft for architecture alignment,
so it should be read as framing rather than as a claim that the whole stack is
already standardized.

## Where a verifiable interaction layer fits

A verifiable interaction layer fits at the boundary where runtime actions are
turned into reviewable records. In the current ecosystem, AAR-MCP-2.0 and
ARO-Audit are best read as candidate layer materials for that boundary: they
help describe how an interaction can be recorded, checked, and exported
without claiming to replace the rest of the stack.

## Relationship to governance / execution integrity / audit evidence

Governance comes first because policy and permission boundaries decide what an
agent is allowed to do before a run is treated as acceptable.

Execution integrity focuses on what actually happened during a run and defines
the bounded verification surface for runtime claims.

Audit evidence preserves the resulting records as exportable evidence so a
reviewer can inspect, hand off, or verify the artifacts outside the original
runtime.

A verifiable interaction layer sits between those concerns. It can help carry
action-level records from runtime behavior into an audit-ready form, but it
does not replace governance control or execution-integrity mechanisms.

## Why this is a candidate layer, not the whole stack

This layer is candidate material because it addresses only one part of the
problem: interaction records and their evidence surface. It does not define
portable persona objects, it does not define the governance plane, and it does
not by itself prove full runtime integrity. It should therefore be treated as
a candidate layer inside Digital Biosphere Architecture, not the whole stack.
