# AJUSTA — End-to-End Delivery Roadmap

A checkbox is complete only when implementation and verification evidence exist.

## A. Foundation and central brain
- [x] Typed task request/result contracts and lifecycle statuses
- [x] Initial department routing, central orchestration and allow-listed Brain dispatch
- [x] Declarative skill manifest and in-memory registry lifecycle
- [x] SQLite-backed durable task request/result storage foundation
- [ ] Persistent skill catalog, schema migrations and dependency-aware planner
- [ ] Bounded concurrency, durable execution queue, idempotency and cancellation
- [x] Versioned authenticated task API scaffold (shared service token only)

## B. Security and identity
- [x] SQLite account/session primitives: normalized unique email, PBKDF2 password verifier, opaque random session token, token-hash persistence, expiry and revocation
- [ ] Wire user registration/login/logout and session authentication into FastAPI
- [ ] Enforce per-user task ownership and tenant/object isolation
- [ ] Rate limiting, abuse protection, account recovery and session/device management
- [ ] Permission scopes, approval inbox, audit events, secret manager and credential rotation
- [ ] Threat model, independent security review and remediation

## C. AI providers and routing
- [x] Provider-neutral model adapter and bounded request/response contract
- [x] OpenAI Responses, Anthropic Messages, xAI Grok Responses and DeepSeek Responses adapters (mocked contract tests only)
- [x] Configurable provider registration and transient-unavailability fallback
- [ ] Live provider verification, capability-aware routing, budgets, quotas, retries and cost reporting
- [ ] Emergency provider disable and user consent for external processing

## D. Skills and departments
- [x] Six model-backed text departments registered in the Brain (no external tools)
- [ ] Research department with source retrieval, citations, freshness and provenance
- [ ] Coding department with isolated sandbox and test execution
- [ ] Persistent skills, isolated execution, permissions, resource limits, review, evaluation and rollback
- [ ] Real specialist workflows for design, data, business, writing and productivity

## E. Knowledge, memory and storage
- [ ] Storage adapter abstraction and object/file storage
- [ ] Document ingestion, indexing, retrieval, provenance and access filtering
- [ ] User-controlled memory inspection, correction, export and deletion
- [ ] Retention across indexes, caches and backups
- [ ] Encryption, backups, restoration and capacity/cost dashboard

## F. Android and user experience
- [x] Kotlin Android Jetpack Compose app skeleton and APK build workflow
- [ ] Secure API client and user-scoped sign-in/register/logout
- [ ] Unified chat, projects, attachments, task plan/progress/cancellation/results
- [ ] Approval inbox, skills catalog, permissions, storage/usage/privacy dashboard
- [ ] Hindi/English localization and accessibility

## G. Reliability and operations
- [ ] Background queue, retries, timeouts, circuit breakers and graceful degradation
- [ ] Structured logs, metrics, traces, alerts and runbooks
- [ ] Load/latency/resource tests and disaster-recovery restore drills

## H. Multimodal and integrations
- [ ] Image, audio and document adapters
- [ ] OS-approved camera/microphone/device permission flows
- [ ] Connector catalog, sandbox accounts, webhook validation and credential revocation

## I. Quality, governance and release
- [ ] Per-department and end-to-end benchmark suite
- [ ] Factuality, robustness, safety and privacy evaluation
- [ ] CI lint, type checks, static analysis and secret scanning
- [ ] Dependency review, signed builds and protected release process
- [ ] Privacy notice, terms, acceptable-use and legal review
- [ ] Security review, gradual release, monitoring, rollback and support

## Current implementation status
AJUSTA has a real but early backend foundation: task contracts, planner/orchestrator, Brain dispatcher, model adapters, synchronous task service, SQLite task persistence, a shared-token FastAPI API, and account/session storage primitives. Android is a Compose starter shell with a CI APK build. The account/session primitives are not yet connected to the API or task ownership. No live model credentials, external research, code sandbox, autonomous learning loop, complete storage system or production deployment have been verified. This is not 100% complete.

## J. End-to-end capability targets
- [x] Model adapters and mocked provider contract tests
- [x] Synchronous task execution and persisted terminal results
- [x] Native Android app scaffold and successful debug APK CI build
- [ ] Per-user authenticated end-to-end Android-to-Brain workflow
- [ ] Central AI Brain with model routing, dependency graphs, progress, cancellation and result evaluation
- [ ] Secure Skill Execution Engine with isolation, permissions, resource limits, audit, approval and rollback
- [ ] Complete multi-user database, adaptive storage, backups and restore
- [ ] Research and learning engine with provenance and reviewed improvements
- [ ] Real department integrations and evidence-backed end-to-end acceptance tests
