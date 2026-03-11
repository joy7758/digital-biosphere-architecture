# Canonical Terms

This document provides the canonical interpretive vocabulary for the Digital Biosphere Architecture ecosystem. It distinguishes architecture terms from repository or project names so that layer concepts and repository identities are not conflated.

## Digital Biosphere Architecture

Type: architecture term.

Digital Biosphere Architecture is a governance-oriented architecture for increasingly autonomous AI systems. It is the top-level interpretive frame for the ecosystem, not a standalone runtime framework or a single repository other than its narrative hub. Use this term when describing the stack as a whole.

## Persona Layer

Type: architecture term.

The Persona Layer defines how an AI system appears as a portable persona object across runtimes and tools. It concerns persona attachment, projection, and reuse rather than execution, governance, or audit logic.

## Governance Layer

Type: architecture term.

The Governance Layer defines runtime constraints, policy boundaries, budget controls, and related decision surfaces. It exists to make system behavior governable before execution claims are treated as acceptable.

## Execution Integrity Layer

Type: architecture term.

The Execution Integrity Layer concerns what actually happened during runtime and whether those claims can be checked. It covers traceability, integrity surfaces, and verifiable runtime evidence rather than post-run audit packaging alone.

## Audit Evidence Layer

Type: architecture term.

The Audit Evidence Layer packages reviewable artifacts that can be exported, replayed, verified, and audited. It is distinct from raw execution trace capture because it emphasizes bounded evidence outputs for external review.

## POP (Persona Object Protocol)

Type: repository and project name.

POP is the persona-layer protocol work in the ecosystem. It provides a portable persona object interface and projection model, but it is not the full architecture, the audit layer, or the end-to-end demo path.

## Token Governor

Type: repository and project name.

Token Governor is the governance-layer repository in the ecosystem. It focuses on runtime budget, policy, routing, fallback, and trade-off control rather than acting as the narrative hub or the full agent stack.

## ARO-Audit

Type: repository and project name.

ARO-Audit is the audit-evidence-layer repository in the ecosystem. It focuses on bounded evidence artifacts, verification, replay, and conformance-oriented review, not on being a generic logging repository or the top-level architecture explanation.

## Verifiable Agent Demo

Type: repository and project name.

Verifiable Agent Demo is the smallest guided walkthrough across layers. It exists as a reference path that helps external readers see cross-layer coherence, but it is not the normative specification for each layer.

## MVK

Type: ecosystem project term.

MVK is used in the ecosystem as execution-integrity reference work. In the canonical stack it belongs under the Execution Integrity Layer and should not be read as a separate fifth architecture axis.

## portable persona object

Type: architecture concept.

A portable persona object is a persona representation that can be referenced, resolved, validated, and projected across runtime environments. It is meant to be reusable and framework-agnostic rather than tied to one agent framework.

## bounded audit evidence

Type: architecture concept.

Bounded audit evidence is a deliberately scoped evidence artifact that can be exported and reviewed without claiming to be an exhaustive model of all runtime state. The boundary is important because it keeps evidence interpretable, portable, and reviewable.

## verifiable runtime evidence

Type: architecture concept.

Verifiable runtime evidence is the subset of runtime information that can be checked or corroborated rather than merely asserted. It belongs to execution-integrity concerns before it is packaged as audit evidence.

## conformance-oriented review

Type: architecture concept.

Conformance-oriented review evaluates whether artifacts, records, or interactions meet stated structural and policy expectations. It is narrower than general trust judgment and exists to support repeatable review and adjudication.
