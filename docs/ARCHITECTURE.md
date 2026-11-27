# AJUSTA — Architecture Overview

## Status
This document describes the target architecture. Only components explicitly identified in the repository's current-status documentation should be treated as implemented.

## System boundaries
- **Android client (Kotlin):** user-facing interface; sends authenticated requests to the backend.
- **Backend API (Python):** validates requests, authenticates users and exposes application services.
- **Central Intelligence:** interprets goals, plans dependencies, routes work, merges results and checks completion.
- **Skill registry and runner:** discovers versioned skills and executes approved skills in isolated, permission-scoped environments.
- **Departments:** specialist capabilities behind stable typed interfaces.
- **Model and tool connectors:** provider-neutral adapters for external AI models, APIs and approved tools.
- **Knowledge and storage layer:** manages authorized documents, records, indexes, project context and task history.
- **Security and governance:** identity, authorization, secret management, policy, audit, privacy and approvals.
- **Evaluation and improvement loop:** identifies gaps, researches options, tests proposals, requests review and supports rollback.

## Request lifecycle
1. Authenticate and validate the request.
2. Identify goal, constraints, data sensitivity and required permissions.
3. Build a bounded plan with explicit steps and dependencies.
4. Select available skills, models and departments based on capability, privacy, quality, latency and cost.
5. Execute only authorized tasks in isolated environments with timeouts and quotas.
6. Validate results using evidence, deterministic checks or tests.
7. Merge results and report partial failures and uncertainty.
8. Ask for approval before consequential external actions.
9. Record minimal, auditable task metadata and apply retention rules.

## Contracts
A request should include an identifier, authenticated user context, instruction, constraints, attachments and output format. A task result should include task identifier, status, result, evidence/validation summary, resource usage and structured error information.

Departments and skills should declare:
- stable name and version
- purpose and supported task types
- typed input and output schemas
- dependencies and supported runtime
- required permission scopes
- timeout and resource limits
- tests, evaluation score and provenance

## Skill learning and activation
A proposed skill moves through draft, isolated test, review, approved, active, deprecated or rolled-back states. Downloaded code and retrieved instructions are untrusted. Skills cannot self-grant permissions, bypass policy, access unrelated user data or deploy their own updates.

## Storage architecture
Use replaceable adapters for relational data, object/file storage, search indexes and vector retrieval. Keep data classes separated, encrypt data, enforce tenant and object-level authorization, and implement backup/restore, retention, export and deletion. Storage scaling may use configured local or cloud services, with user consent for external providers and costs.

## Security principles
Use least privilege, server-side authorization, secret management, maintained cryptography, sandboxing, prompt-injection defenses, quotas, audit logs and explicit approval for consequential actions. Fail closed when permission checks fail. Security is assessed through controls, tests, audits and residual-risk reporting; never claim absolute or 100% security.

## Research-first behavior
When a request exceeds current capabilities, AJUSTA should state the limitation, investigate evidence-backed alternatives and propose safe experiments. It must not claim success without verification.

## First implementation milestone
Keep the initial deterministic, provider-independent planner as the foundation. Add typed department contracts and orchestration tests before connecting external providers or executing tools.
