# AJUSTA Backend Foundation

This is an early deterministic backend core, not a production-ready autonomous agent.

## Requirements
- Python 3.11+
- Install test extras: `python -m pip install -e '.[test]'`

## Run tests
From this directory: `python -m pytest`

## Implemented foundation
- Typed, validated task request/result contracts and lifecycle statuses.
- Validates and normalizes a user request.
- Routes requests to specialist departments using transparent keyword rules.
- Central orchestrator combines the planner, enabled-department registry and action policy.
- Reports requested departments that are not enabled instead of pretending they are connected.
- Blocks consequential actions unless explicit user approval is present.
- Declarative skill manifests with name/version/schema/permission validation.
- In-memory skill registry with draft → approved → active lifecycle and explicit disable/re-review.
- Skill registration stores metadata only; it does not execute downloaded or generated code.
- Unit tests specify contracts, planner, policy, orchestration and skill-registry behavior.

## Not connected yet
No AI provider is connected; no department performs real specialist work; no external tools are invoked; no persistent database, authentication service, Android client, long-term memory, sandboxed skill runner, autonomous learning pipeline, or production deployment exists. The skill registry is currently in-memory and is not a security sandbox. The central orchestration layer creates plans only. Add integrations behind documented interfaces, permission checks and tests.
