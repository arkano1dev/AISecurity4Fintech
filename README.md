# Fintech AI Platform

This repository is a production-oriented reference implementation for secure AI systems in regulated financial environments. It is designed for organizations that need to deploy AI-powered workflows for compliance, support, and operations without giving up governance, traceability, or data protection.

## Why this project exists

Financial institutions are adopting AI for knowledge work, customer support, and internal operations, but the risk profile is higher than in standard SaaS environments. The core problem is not whether the model can answer a question; it is whether the system can do so safely, transparently, and in a way that can be defended under audit.

In regulated fintech environments, teams need to address the following problems at the same time:

- unauthorized exposure of customer or employee data to LLMs
- invisible or untraceable AI decisions during support and compliance tasks
- prompt injection or tool misuse from untrusted data sources
- weak evidence of what happened when a workflow executed
- poor alignment with governance requirements such as GDPR, PSD2, DORA, and the EU AI Act

This project is built to answer those concerns with a clear technical foundation instead of a model-only prototype.

## Product value

The platform is organized around two primary business-facing experiences:

- VaultRAG for compliance analysts and risk teams who need secure retrieval over policy, process, and investigation content
- AgentFlow for customer support and operations teams that need structured multi-agent workflows with controlled tool use

Both applications rely on a shared security primitive: an append-only, tamper-evident audit log that records sensitive actions in a way that can be independently verified.

## How the platform solves the problem

The project takes a control-oriented approach to AI in finance:

1. Secure retrieval
   - documents and policy knowledge are retrieved under access-aware boundaries
   - usage stays aligned with internal compliance and investigation workflows

2. Controlled orchestration
   - multi-agent actions are supervised and scoped to explicit operational responsibilities
   - tool execution is treated as a governed capability, not a free-form agent action

3. Tamper-evident auditing
   - every significant action is recorded as an append-only hash-linked event
   - the chain can be verified to detect modification or deletion attempts

4. Operational transparency
   - logs, structured settings, and tracing are built around shared platform primitives
   - the design supports later integration with stronger security controls such as service mTLS, KMS-backed secrets, and external verification anchors

## What type of solution this is

This is a reference architecture for secure AI in regulated enterprise settings. It combines:

- FastAPI services for API-based workflow access
- Pydantic v2 for typed runtime validation
- SQLAlchemy and Postgres for durable persistence
- a hash-chain audit model for integrity proof
- a monorepo workspace structure for shared security primitives

It is not a generic toy app. It is a platform blueprint for teams that need to operationalize AI in environments where auditability, data controls, and governance are business-critical.

## Business applicability

This architecture can be adapted to several regulated or high-trust sectors beyond fintech:

- banks and payment providers
- insurers and claims operations
- wealth and asset management firms
- lending and underwriting platforms
- B2B fintech platforms with compliance-heavy workflows
- internal enterprise knowledge systems handling sensitive operational records

The same design pattern applies wherever AI supports human decision-making but must preserve evidence, limit data exposure, and provide reviewer confidence.

## Repository structure

- apps/vaultrag — secure retrieval workflows for compliance and analyst-facing search
- apps/agentflow — multi-agent customer support and operational orchestration
- services/audit-log — append-only, hash-linked audit service for sensitive actions
- services/pii-proxy — shared PII redaction and encrypted vault flow for regulated payloads
- packages/py-shared — common logging, settings, and tracing utilities
- docs/adr — architecture decisions and trade-offs
- docs/threat-model — current system risk model and control mapping
- infra/docker-compose — local environment for Postgres, Redis, and observability tooling

## Security and compliance focus

This project is intentionally aligned with enterprise control needs:

- GDPR for personal data handling and record retention obligations
- PSD2 for transaction integrity and operational accountability
- DORA for resilience and auditability of critical digital systems
- EU AI Act for trustworthy and observable AI behavior in regulated settings

## Local development

```bash
make test
make lint
make ci
```

## Operating principles

- privacy by design
- evidence over opacity
- security controls first, model features second
- auditable systems over hidden automation
- portability across financial and regulated business contexts

This project is intended as a practical foundation for secure AI system design in financial services, with the audit log and governance model acting as the first critical control layer.
