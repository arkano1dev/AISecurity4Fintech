# US-V6: Append-only, tamper-evident audit log

## Title
Append-only, tamper-evident audit log

## User story
As an auditor, I want tamper-evident records of every sensitive action, so I can prove what happened and when without trusting the operator.

## Why this story first
This story has no LLM dependency, is shared by both apps, and exercises the crypto and persistence patterns the platform will reuse. It also matches the candidate’s blockchain background: the natural baseline is a hash chain, where each record is bound to the previous one with SHA-256, before we later consider a Merkle batch and blockchain anchor in W7.

## Definition of Ready
### API contract
```yaml
openapi: 3.1.0
paths:
  /audit/append:
    post:
      summary: Append an audit record
      responses:
        '201':
          description: created
  /audit/verify:
    get:
      summary: Verify the hash chain integrity
      responses:
        '200':
          description: verification result
```

### Data model
`audit_record` table with columns:
- id UUID PK
- seq BIGINT UNIQUE
- timestamp TIMESTAMPTZ
- actor_sub TEXT
- tenant_id TEXT
- action TEXT
- payload JSONB
- payload_hash TEXT
- prev_hash TEXT
- hash TEXT
- retention_until TIMESTAMPTZ

### Security impact
Prevents after-the-fact tampering and provides a forensic trail for sensitive actions. This supports GDPR Art. 30 records of processing and AMLD Art. 40 retention obligations.

### Regulatory impact
Retention is mandatory for compliance; immutable storage reduces the risk of audit record manipulation during investigations and regulator inquiries.

### Dependencies pinned
- Python 3.12
- FastAPI 0.115+
- Pydantic 2.9+
- SQLAlchemy 2.0+
- asyncpg 0.29+

### Out of scope
Blockchain anchoring (W7), Merkle batch publishing (W7), and endpoint-level authentication (W2). The service currently trusts localhost in v1 and documents the gap in the threat model.

## Acceptance criteria
### Given/When/Then
- Given a fresh audit log, when I append one record, then the response is 201 and the hash chain starts at seq 1 with prev_hash equal to 64 zeroes.
- Given three sequential appends, then each next record links to the prior hash and seq increments monotonically.
- Given N >= 3 records exist, when I call `GET /audit/verify`, then the verification result is valid and the first broken index is null.
- Given 5 records exist, when a middle record is modified directly in the database, then `GET /audit/verify` returns `valid: false` and the first broken index.
- Given an existing record, when I attempt UPDATE or DELETE as the application role, then the database rejects the action.
- Given the same dict in different insertion orders, then canonical JSON serialization is deterministic and the hash matches.

## Threat model reference
This story directly addresses audit log tampering and supports the draft threat model in `docs/threat-model/v1.md`.
