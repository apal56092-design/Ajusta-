# AJUSTA — Architecture Overview

## Status
This document describes the proposed architecture. It is not evidence that the components have already been implemented.

## System boundaries

- **Android client (Kotlin):** user-facing interface; sends authenticated requests to the backend.
- **Backend API (Python):** validates requests, authenticates users and exposes application services.
- **Central Intelligence:** turns a request into a structured task plan and coordinates approved departments.
- **Departments:** implement specialist capabilities behind stable interfaces.
- **Connectors:** isolate external AI providers and tools behind adapters.
- **Knowledge layer:** retrieves authorized project documents and context.
- **Security layer:** enforces identity, permissions, secret handling and audit requirements.

## Initial request contract

A request should eventually include:
- request identifier
- user identity and authorization context
- user instruction
- optional constraints and attachments
- requested output format

A task result should include:
- task identifier
- status (queued, running, succeeded, failed, needs_approval)
- concise result
- evidence or validation summary where applicable
- structured error information when unsuccessful

## Orchestration principles

1. Validate the request before planning.
2. Build a bounded plan with explicit steps and dependencies.
3. Route only to enabled and authorized departments.
4. Apply timeouts and resource limits to external calls.
5. Treat model output and retrieved documents as untrusted input.
6. Validate outputs before presenting them as verified.
7. Ask for approval before consequential external actions.
8. Preserve an auditable record without logging secrets.

## First implementation milestone

Build a deterministic, provider-independent task planner before connecting paid or external AI services. This creates a testable foundation and avoids pretending that an AI provider is already connected.
