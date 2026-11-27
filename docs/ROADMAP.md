# AJUSTA — End-to-End Delivery Roadmap

This roadmap combines the capability vision with product, security, infrastructure and operations requirements. A checkbox is complete only when implementation and verification evidence exist.

## A. Foundation and central brain
- [ ] Typed request, task, result and error contracts
- [ ] Department interface, skill manifest and registry
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
- [ ] Skill authoring specification and versioning
- [ ] Isolated skill execution, review, approval and rollback
- [ ] Skill evaluation benchmarks and regression tests

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
The repository has an initial deterministic Python planner/orchestrator and approval-policy foundation, plus a CI workflow definition. The remaining items above are planned unless their implementation and test evidence are recorded. Check actual CI results before marking tests successful.
