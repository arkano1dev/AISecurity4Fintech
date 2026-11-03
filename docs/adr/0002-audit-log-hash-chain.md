# ADR 0002: SHA-256 hash chain with DB-level immutability

## Status

Accepted.

## Context

The platform needs a tamper-evident record of sensitive actions before adding broader agentic workflows, payment operations, and external verification. We need a trusted source of truth that is cheap to operate, easy to reason about in interviews, and robust enough to support compliance evidence.

## Decision

We implement the audit log as a SHA-256 hash chain over canonical JSON. Each record includes the previous hash, the payload hash, and the computed current hash. The database itself enforces append-only behavior with a `BEFORE UPDATE/DELETE` trigger that raises an exception.

## Why this decision

- SHA-256 is the most defensible default in compliance work: it is widely accepted, stable, and easy to explain to auditors and regulators.
- Canonical JSON removes variability from object ordering so the same logical record always hashes the same way.
- DB-layer immutability provides defense in depth even if the application layer is buggy or compromised.

## Why not application-only append-only logic

Application code alone is not enough. A privileged operator with database access or a compromised service account can still rewrite or delete rows outside the intended control flow. The app-level invariant is useful, but it is not a substitute for an immutable storage layer.

## Why not blockchain from day 1

A blockchain anchor is a valid later-stage control, but it is overkill for the initial story. It adds operational complexity, latency, and cost before the team has proven the local chain semantics, retention rules, and forensic workflows. The more sensible approach is to prove the append-only design first and then add Merkle or chain anchoring when the real operational volume justifies it.

## Trade-off

The verification algorithm is O(n) over the stored records. This is acceptable for periodic verification and forensic review, but if request volume becomes high, the platform should move to Merkle-tree batching and a separate external anchor in W7.

## Exit criteria for revisiting

Revisit this design if sustained append rate exceeds roughly 1,000 rows per minute or if the verification process becomes a production bottleneck. At that point, a Merkle batch and anchor will be more cost-effective than repeated full-chain scans.
