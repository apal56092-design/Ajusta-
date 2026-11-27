# AJUSTA Development Roadmap

This roadmap is an evolving plan. A milestone becomes complete only after implementation, tests and documentation are committed.

## Milestone 0 — Repository foundation
- [x] Create repository README (initial version)
- [ ] Add architecture and roadmap documents
- [ ] Add secure .gitignore
- [ ] Agree module naming and coding conventions

## Milestone 1 — Central Intelligence MVP
- [ ] Define task/request/result data structures
- [ ] Define department interface
- [ ] Implement deterministic task planning
- [ ] Add unit tests for valid, empty and malformed requests
- [ ] Document local setup and test commands

## Milestone 2 — First department
- [ ] Select first department
- [ ] Implement its interface
- [ ] Test successful and failed execution paths

## Milestone 3 — AI provider adapter
- [ ] Define provider-neutral interface
- [ ] Add environment-based configuration
- [ ] Add timeout, retry and rate-limit handling
- [ ] Never commit secrets

## Milestone 4 — Knowledge system
- [ ] Define document and source metadata
- [ ] Add ingestion and retrieval
- [ ] Add authorization checks and provenance

## Milestone 5 — Android client
- [ ] Create Kotlin application skeleton
- [ ] Add authenticated API client
- [ ] Add task submission and status screens

## Milestone 6 — Controlled automation
- [ ] Define permission scopes
- [ ] Add approval gates
- [ ] Add audit events and safe failure handling

## Definition of done
A milestone is complete only when its code exists, automated tests pass, setup instructions are current, and the README/status documentation reflects reality.
