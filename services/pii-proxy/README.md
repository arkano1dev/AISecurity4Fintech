# PII Proxy

The shared PII proxy provides fail-closed de-identification and encrypted record storage for regulated customer data.

## Responsibilities

- Mask sensitive values such as email, SSN, and date patterns before they reach downstream tools.
- Store payload metadata in an encrypted vault using an AES-GCM backed receipt model.
- Expose consistent API contracts for downstream services without leaking raw PII in responses.

## Local checks

```bash
PYTHONPATH=services/pii-proxy/src pytest services/pii-proxy/tests -q
```
