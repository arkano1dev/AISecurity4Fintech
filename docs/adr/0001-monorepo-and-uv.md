# ADR 0001: monorepo with uv workspace

## Status

Accepted.

## Context

The platform is a small but multi-surface fintech AI system with shared security services, observability, and configuration. We expect cross-app reuse of the same audit log, settings model, and operational patterns.

## Decision

We keep a monorepo instead of splitting each app into its own repository, and we use a uv workspace to manage shared Python dependencies.

## Why monorepo over polyrepo

- Shared security services such as the audit log are consumed by multiple apps.
- Changes to a shared primitive should be reviewable and deployable in one atomic change set.
- One CI job can model cross-app regressions before release.

## Why uv over pip or poetry

- Lower latency for dependency resolution and install.
- Native workspace support for multiple Python packages in one repo.
- Simple lockfile generation and repeatable automation in CI.
- Fits modern PEP 723 and pyproject-based packaging expectations.

## Why pydantic-settings over python-dotenv

- Typed config objects reduce accidental misconfiguration.
- Environment precedence is explicit and testable.
- It pairs naturally with runtime validation and secret injection patterns used in regulated systems.

## Alternatives rejected

- Polyrepo: rejected because shared security primitives would drift across repositories and create inconsistent controls.
- Poetry-only: rejected because workspace management and speed are weaker for a multi-package monorepo.
- python-dotenv alone: rejected because it does not validate config types or enforce secure defaults.
