# AJUSTA — End-to-End Delivery Roadmap

A checkbox is complete only when implementation and verification evidence exist.

## A. Foundation and central brain
- [x] Typed task request/result contracts and lifecycle statuses
- [x] Initial department routing and central orchestration boundary
- [x] Declarative skill manifest and in-memory registry lifecycle (draft/review/activate/disable)
- [x] Explicit department-handler interface, allow-listed registry and central plan dispatcher (in-memory; no real specialist integrations yet)
- [x] SQLite-backed durable task request/result storage foundation
- [ ] Persistent skill catalog and database migrations
- [ ] Dependency-aware planner, bounded concurrency and cancellation
- [ ] Structured task state, idempotency and durable execution queue
- [ ] API versioning and generated API documentation

## B. Security and identity
- [ ] Authentication, session lifecycle and account recovery
- [ ] Server-side authorization and tenant/object isolation
- [ ] Permission scopes, approval inbox and revocation
- [ ] Secret manager and credential rotation
- [ ] Threat model, security tests and audit events

## C. AI providers and routing
- [x] Provider-neutral model adapter and bounded request/response contract
- [ ] Model capability registry and routing policy
- [ ] Timeouts, bounded retries, quotas, budgets and cost reporting
- [x] Provider fallback only for declared transient unavailability\n- [ ] Emergency provider disable and operator controls
- [ ] User-visible disclosure of external processing and consent

## D. Skills and departments
- [x] Six default model-backed text departments registered in the Brain (no external tools)\n- [ ] Research department with evidence provenance
- [ ] Coding department with sandbox and test execution
- [ ] Design, data, business, writing and productivity departments
- [ ] Persistent skill catalog with audit history
- [ ] Isolated skill execution, dependency controls and resource limits
- [ ] Skill authoring workflow, evaluation benchmarks and rollback

## E. Knowledge, memory and storage
- [ ] Storage adapter abstraction and object/file storage
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
Implemented foundations: deterministic planner/orchestrator, approval-policy foundation, typed task contracts, in-memory skill registry, in-memory department-handler dispatcher, and file-backed SQLite persistence for task requests/results. This is not a production-ready application. A concrete OpenAI Responses adapter, server-environment gateway factory, and six model-backed text departments now exist, but live provider credentials are not configured. Specialist department workflows, authentication, secure skill sandbox, Android app, complete storage lifecycle, learning/research engine and operational controls remain incomplete. Automated tests have been added; verify the latest GitHub Actions run before treating them as passing.

## J. End-to-end capability targets
- [x] OpenAI Responses API adapter with server-side environment-secret boundary and mocked contract tests\n- [ ] Live provider integration test with deployment-managed credentials
- [x] Model-backed department-handler bridge into the central Brain (single bounded model request; no tool execution)\n- [ ] Central AI Brain with model routing, dependency graphs, progress, cancellation and result evaluation
- [ ] Secure Skill Execution Engine with isolation, permissions, resource limits, audit, approval and rollback
- [ ] Complete persistent database for identity, tasks, skills, permissions and audit history
- [ ] Adaptive object/file storage with capacity, cost, backup and restore controls
- [ ] Learning and Research Engine with provenance, freshness and reviewed improvements
- [ ] Authentication and server-enforced authorization across all data and actions
- [ ] Native Kotlin Android app connected to authenticated APIs
- [ ] Real implementations for every department, with evidence and tests
- [ ] End-to-end acceptance tests from Android/API through brain, model, department/skill, storage and verified result
