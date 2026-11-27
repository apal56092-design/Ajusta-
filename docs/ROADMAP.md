# AJUSTA — End-to-End Delivery Roadmap

This roadmap combines the capability vision with product, security, infrastructure and operations requirements. A checkbox is complete only when implementation and verification evidence exist.

## A. Foundation and central brain
- [x] Typed task request/result contracts and lifecycle statuses
- [x] Initial department routing and central orchestration boundary
- [x] Declarative skill manifest and in-memory registry lifecycle (draft/review/activate/disable)
- [ ] Department execution interface and persistent skill catalog
- [ ] Dependency-aware planner, bounded concurrency and cancellation
- [ ] Structured task state, partial failures and idempotency
- [ ] API versioning and generated API documentation

## B. Security and identity
- [ ] Authentication, session lifecycle and account recovery
- [ ] Server-side authorization and tenant/object isolation
- [ ] Permission scopes, approval inbox and revocation
- [ ] Secret manager and credential rotation
- [ ] Threat model, security tests and audit events

## C. AI providers and routing
- [ ] Provider-neutral model adapter
- [ ] Model capability registry and routing policy
- [ ] Timeouts, bounded retries, quotas, budgets and cost reporting
- [ ] Provider fallback and emergency disable
- [ ] User-visible disclosure of external processing and consent

## D. Skills and departments
- [ ] Research department with evidence provenance
- [ ] Coding department with sandbox and test execution
- [ ] Design, data, business, writing and productivity departments
- [ ] Persistent skill catalog with audit history
- [ ] Isolated skill execution, dependency controls and resource limits
- [ ] Skill authoring workflow, evaluation benchmarks and rollback

## E. Knowledge, memory and storage
- [ ] Storage adapter abstraction
- [ ] Relational database and object/file storage
- [ ] Document ingestion, indexing and retrieval
- [ ] Provenance, source freshness and access filtering
- [ ] User-visible memory inspection, correction, export and deletion
- [ ] Retention across indexes, caches and backups
- [ ] Encryption, backups, restoration and capacity/cost dashboard
- [ ] User consent for external storage and paid capacity

## F. Android and user experience
- [ ] Kotlin Android app skeleton and secure API client
- [ ] Unified chat, projects and file attachments
- [ ] Task plan, progress, cancellation and result screens
- [ ] Approval inbox and connected-account controls
- [ ] Skills catalog and permissions screen
- [ ] Storage, usage and privacy dashboard
- [ ] Hindi/English localization and accessibility

## G. Reliability and operations
- [ ] Queue and durable task state for long-running work
- [ ] Health/readiness checks, circuit breakers and graceful degradation
- [ ] Structured logs, metrics, traces and alerts
- [ ] Operational dashboards and incident runbooks
- [ ] Disaster recovery objectives and tested restore drills
- [ ] Load, latency and resource tests

## H. Multimodal and integrations
- [ ] Image, audio and document adapters
- [ ] Explicit camera/microphone and device permission flows
- [ ] Connector catalog, sandbox/test accounts and webhook validation
- [ ] Device automation only through OS-approved permission scopes
- [ ] Connector disable and credential revocation

## I. Quality, governance and release
- [ ] Per-department and end-to-end benchmark suite
- [ ] Factuality, robustness, safety and privacy evaluation
- [ ] CI: tests, lint, type checks, static analysis and secret scanning
- [ ] Dependency review, signed builds and protected release process
- [ ] Privacy notice, terms, acceptable-use and legal review
- [ ] Security review and remediation
- [ ] Gradual release, monitoring, rollback and support process

## Current implementation status
The repository contains a deterministic Python planner/orchestrator, approval-policy foundation, typed task contracts, a declarative in-memory skill registry and a CI workflow definition. The registry does not execute code and is not a sandbox. Other unchecked items remain planned unless implementation and test evidence are recorded. Check actual CI results before marking tests successful.


## J. Explicit end-to-end capability delivery
These requirements expand the existing workstreams; they remain planned until implemented and verified.
- [ ] Real AI model adapters connected to at least one selected provider, with secure server-side secrets and verified integration tests
- [ ] Central AI Brain coordinating planning, dependency graphs, model routing, departments, skills, progress, cancellation and result evaluation
- [ ] Secure Skill Execution Engine with isolated sandbox, permission scopes, resource limits, audit, approval, disable and rollback
- [ ] Persistent database for identity, tasks, skills, permissions and audit history; durable file/object storage with configurable adapters
- [ ] Adaptive storage policy based on data sensitivity, configured capacity, provider limits, availability and cost; backups and restore verification
- [ ] Learning and Research Engine with source provenance, freshness, evidence evaluation and reviewed skill-improvement lifecycle
- [ ] Complete authentication and server-enforced authorization across users, tenants, departments, skills, connectors and data
- [ ] Native Kotlin Android app connected to authenticated APIs, with task workspace, approvals, skills, storage and privacy controls
- [ ] Real execution implementations for every department, each with typed contracts, permissions, evidence and department-specific tests
- [ ] End-to-end acceptance tests proving a user request can travel from Android/API through brain, model, department/skill, storage and verified result
