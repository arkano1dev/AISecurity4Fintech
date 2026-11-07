# ADR 0005: VaultRAG retrieval design

## Status

Accepted.

## Date

2026-11-07

## Context

VaultRAG is the first application to run the full platform pipeline: ingest a
document, redact PII, embed, retrieve, generate a cited answer, and audit. Three
non-trivial choices shape the code: where vectors live, how retrieval ranks
chunks, and how the app talks to the shared services.

## Decisions

### 1. In-memory vector store with a linear cosine scan (not pgvector)

`VectorStore` holds `Chunk` objects in a Python list. `retrieve` scores every
chunk against the query with cosine similarity and returns the top-k.

**Why:** the PRD defers a real vector database until the platform is proven end
to end. A linear scan is correct for the small demo corpus and keeps the system
understandable. The `add_chunk` / `chunks` interface is exactly what a future
pgvector-backed store will also implement, so the swap is mechanical.

**Trade-off:** O(n) per query. Fine for now; pgvector with an index is the later
layer.

### 2. Dense-only retrieval (cosine similarity)

Ranking uses embedding distance only. Hybrid BM25 + dense is deferred.

**Why:** cosine over embeddings is simple, length-independent, and already works
with the local `nomic-embed-text` model. BM25 adds a second index and a merge
step that is not needed to prove the pipeline.

### 3. HTTP boundaries to pii-proxy and audit-log (not in-process imports)

VaultRAG calls the shared services over HTTP, the same way AgentFlow calls
auth-service.

**Why:** the PII proxy and the audit log must be genuine trust boundaries. If
VaultRAG imported the redaction function directly, the "PII never reaches the
model" guarantee would rest on a function call inside the same process — not a
separate, independently deployable control. The audit log must survive
independently of the app so it can be the single source of truth.

### 4. Redact before embed

Masking happens before the chunk is embedded, not after retrieval.

**Why:** the vector store must never contain raw PII at all. Redacting first
means a compromise of the store leaks only placeholders, and the invariant is
simple to test.

## Alternatives rejected

- pgvector from day 1: adds infrastructure before the pipeline is proven.
- Hybrid BM25 + dense: adds complexity with no demo benefit yet.
- In-process PII/audit functions: weakens the trust boundaries.

## Follow-up

- Postgres + pgvector persistence.
- Hybrid retrieval, tenant isolation, PDF ingestion.
