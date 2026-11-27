# AJUSTA Backend Foundation

This is an early deterministic backend core, not a production-ready autonomous agent.

## Requirements
- Python 3.11+
- Install test extras: `python -m pip install -e '.[test]'`

## Run tests
From this directory: `python -m pytest`

## Implemented foundation
- Typed, validated task request/result contracts and lifecycle statuses.
- Validates and normalizes a user request and routes it using transparent keyword rules.
- Central orchestrator combines planning, enabled-department registry and action policy.
- Explicit department-handler interface and allow-listed central brain dispatcher.
- Brain reports completed, partial or unavailable department outcomes.
- SQLite-backed durable task store persists task requests and results across store instances.
- Provider-neutral model gateway routes to explicitly registered model adapters and falls back only on declared provider unavailability.
- Explicit duplicate-ID handling, missing-task errors and evidence serialization.
- Blocks consequential actions unless explicit user approval is present.
- Declarative skill manifests and in-memory skill registry with draft/review/activate/disable lifecycle.
- Unit tests specify contracts, planning, policy, orchestration, brain dispatch, skill registry and SQLite storage.

## Not connected or production-ready yet
No concrete AI provider adapter is connected yet; the model gateway is an interface and routing layer until real provider adapters and server-side credentials are configured. Department handlers are interfaces until real specialist adapters are implemented; no external tools are invoked; no authentication service, Kotlin Android client, sandboxed skill runner, autonomous learning pipeline, or production deployment exists. The skill registry remains in-memory and is not a sandbox. SQLite currently stores task records only; it is not yet a complete database model for users, permissions, skills, audit history or files. There is no migration, backup/restore, encryption-at-rest or multi-user authorization layer. The central brain does not yet automatically select models through the gateway, schedule dependencies, stream progress, cancel running work or evaluate evidence.
