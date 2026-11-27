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
- Provider-neutral model gateway routes to explicitly registered model adapters and falls back only on declared provider unavailability.\n- OpenAI Responses API adapter uses server-side environment configuration, bounded timeouts, typed authentication/transient/request errors, and response text validation.\n- `create_default_model_gateway()` builds the gateway from `OPENAI_API_KEY` and `OPENAI_MODEL`; `ModelDepartmentHandler` connects approved department handlers to that gateway.\n- `register_model_departments()` installs six bounded model-backed departments: research, coding, design, data, business and automation.
- Explicit duplicate-ID handling, missing-task errors and evidence serialization.
- Blocks consequential actions unless explicit user approval is present.
- Declarative skill manifests and in-memory skill registry with draft/review/activate/disable lifecycle.
- Unit tests specify contracts, planning, policy, orchestration, brain dispatch, skill registry and SQLite storage.

## Not connected or production-ready yet
The OpenAI Responses adapter and environment-configured gateway factory are implemented, but the provider is not live-connected until a trusted deployment operator configures an API key and model name as server-side environment secrets. Example server configuration names: `OPENAI_API_KEY` and `OPENAI_MODEL`. No key belongs in Android, GitHub source, or chat. The model gateway currently supports this adapter and future explicitly registered providers. The six default departments can now generate text through the model gateway, but they do not yet browse the web, read private files, execute code, manipulate external apps, or perform real-world actions; no external tools are invoked; no authentication service, Kotlin Android client, sandboxed skill runner, autonomous learning pipeline, or production deployment exists. The skill registry remains in-memory and is not a sandbox. SQLite currently stores task records only; it is not yet a complete database model for users, permissions, skills, audit history or files. There is no migration, backup/restore, encryption-at-rest or multi-user authorization layer. The central brain does not yet automatically select models through the gateway, schedule dependencies, stream progress, cancel running work or evaluate evidence.
