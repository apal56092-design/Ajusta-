# AJUSTA Backend Foundation

This is an early deterministic backend core, not a production-ready autonomous agent.

## Requirements
- Python 3.11+
- Install test extras: `python -m pip install -e '.[test]'`

## Run tests
From this directory: `python -m pytest`

## Implemented foundation
- Validates and normalizes a user request.
- Routes requests to specialist departments using transparent keyword rules.
- Central orchestrator combines the planner, enabled-department registry and action policy.
- Reports requested departments that are not enabled instead of pretending they are connected.
- Blocks consequential actions unless explicit user approval is present.
- Unit tests specify planner, policy and orchestration behavior.

## Not connected yet
No AI provider is connected; no department performs real specialist work; no external tools are invoked; there is no database, authentication service, Android client, long-term memory, autonomous learning, or production deployment. The central orchestration layer currently creates plans only. Add integrations behind documented interfaces, permission checks and tests.
