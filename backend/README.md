# AJUSTA Backend Foundation

This is an evolving backend foundation for AJUSTA. It is not yet a production-ready autonomous agent.

## Requirements
- Python 3.11+
- Install test extras: `python -m pip install -e '.[test]'`

## Run tests
From this directory: `python -m pytest`

## Implemented foundation
- Typed, validated task request/result contracts and lifecycle statuses.
- Transparent keyword planner, central orchestrator, allow-listed Brain dispatcher and approval-policy boundary.
- SQLite-backed durable task request/result store.
- Provider-neutral model gateway and adapters for OpenAI Responses, Anthropic Messages, xAI Grok and DeepSeek; contract tests use mocked transports, not live credentials.
- Six bounded model-backed text departments: research, coding, design, data, business and automation. These currently generate text only; they do not yet browse, execute code or control external apps.
- Synchronous task service joining planning, approval checks, department dispatch and result persistence.
- FastAPI task API scaffold with a shared server-side bearer token for controlled testing.
- New account/session primitives in `ajusta_core.auth`: PBKDF2-HMAC-SHA256 password verifiers, normalized unique email accounts, opaque random session tokens, SHA-256 token-hash storage, expiry and revocation.
- Declarative skill manifests and an in-memory skill lifecycle registry.

## Important integration and production gaps
The account/session store is a tested backend primitive, **not yet wired into FastAPI routes or task ownership**. The current task API still uses a shared service token; do not expose it publicly or embed it in Android. Per-user task ownership, login/register/logout endpoints, rate limiting, account recovery, authorization scopes and audit events are still required.

Provider adapters have not been verified against live accounts. Configure credentials only as server-side deployment secrets; never place them in Android, GitHub source or chat. No live provider call has been verified. Research does not yet browse or cite sources; coding does not execute in a sandbox; the skill registry does not run generated code; the learning pipeline, durable job queue, cancellation, streaming, adaptive file storage, backup/restore, observability and production deployment remain incomplete.

SQLite currently provides task and auth primitives, not a complete multi-tenant data model. There is no production migration system, encryption-at-rest, backup/restore or security review. The Android app is a Jetpack Compose scaffold and is not connected to the backend.

## Android scaffold
The native Android project lives in `../android` and uses Kotlin with Jetpack Compose. Build locally with Gradle 8.13 and JDK 17:

```bash
cd android
gradle :app:assembleDebug
```
