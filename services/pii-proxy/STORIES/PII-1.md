# PII-1: shared PII proxy

## Goal

Provide a shared service that redacts sensitive values before they reach downstream AI tools and stores regulated metadata under an encrypted receipt model, without exposing raw PII in responses.

## Acceptance criteria

- Given a message with an email and SSN, when the PII proxy masks it, then the response redacts those fields and keeps the message usable for downstream analysis.
- Given a record payload, when the vault endpoint stores it, then the service returns a non-empty receipt and never exposes the original email in the receipt payload.
- Given a missing receipt, when the lookup endpoint is called, then the API returns a 404 instead of leaking metadata.

## Security expectations

- Fail closed: sensitive values are replaced before downstream processing.
- Encrypted vaulting: the receipt model stores encrypted payload metadata with a stable keyed reference.
- Minimal exposure: only redacted text and opaque receipt metadata are returned to callers.
