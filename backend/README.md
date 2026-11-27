# AJUSTA Backend Foundation

This is the first deterministic foundation, not a production-ready autonomous agent.

## Requirements
- Python 3.11+
- Install test extras: `python -m pip install -e '.[test]'`

## Run tests
From this directory: `python -m pytest`

## Current behavior
- Validates and normalizes a user request.
- Routes it to specialist departments using transparent keyword rules.
- Produces a bounded task plan.
- Blocks consequential actions unless explicit user approval is present.

## Not implemented yet
No AI provider is connected; no external tools are invoked; there is no database, authentication service, Android client, autonomous learning, or production deployment. Add these only behind documented interfaces, permission checks and tests.
