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
- Provider-neutral model gateway routes to explicitly registered model adapters and falls back only on declared provider unavailability.\n- OpenAI Responses API adapter uses server-side environment configuration, bounded timeouts, typed authentication/transient/request errors, and response text validation.\n- `create_default_model_gateway()` builds an OpenAI-only gateway from `OPENAI_API_KEY` and `OPENAI_MODEL`; `create_configured_model_gateway()` registers all configured providers in an operator-defined fallback order.
- Provider adapters: OpenAI Responses, Anthropic Claude Messages, xAI Grok Responses, and DeepSeek Responses. Grok and DeepSeek use their documented Responses-compatible APIs; Claude uses Anthropic's Messages format.\n- `register_model_departments()` installs six bounded model-backed departments: research, coding, design, data, business and automation.\n- `TaskExecutionService` joins task persistence, planning, approval checks, department dispatch and terminal result storage in one synchronous execution path.
- Explicit duplicate-ID handling, missing-task errors and evidence serialization.
- Blocks consequential actions unless explicit user approval is present.
- Declarative skill manifests and in-memory skill registry with draft/review/activate/disable lifecycle.
- Unit tests specify contracts, planning, policy, orchestration, brain dispatch, skill registry and SQLite storage.

## Not connected or production-ready yet
Provider adapters for OpenAI, Anthropic Claude, xAI Grok and DeepSeek are implemented with mocked contract tests. They are not live-connected until a trusted deployment operator configures each provider's API key and model name as server-side environment secrets: `OPENAI_API_KEY`/`OPENAI_MODEL`, `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL`, `XAI_API_KEY`/`XAI_MODEL`, and `DEEPSEEK_API_KEY`/`DEEPSEEK_MODEL`. `create_configured_model_gateway()` registers only configured providers; fallback order defaults to OpenAI, Anthropic, xAI, DeepSeek and can be changed with `AJUSTA_MODEL_PROVIDER_ORDER`. No key belongs in Android, GitHub source, or chat. Provider adapters are implemented, but live provider calls have not been verified. The six default departments can now generate text through the model gateway, but they do not yet browse the web, read private files, execute code, manipulate external apps, or perform real-world actions; no external tools are invoked; no authentication service, Kotlin Android client, sandboxed skill runner, autonomous learning pipeline, or production deployment exists. The skill registry remains in-memory and is not a sandbox. SQLite currently stores task records only; it is not yet a complete database model for users, permissions, skills, audit history or files. There is no migration, backup/restore, encryption-at-rest or multi-user authorization layer. The task service is synchronous only: it does not yet schedule background jobs, stream progress, cancel running work, provide multi-user authorization, or evaluate evidence quality.
