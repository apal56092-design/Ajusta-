# AJUSTA — End-to-End Delivery Roadmap

A checkbox is complete only when implementation and verification evidence exist.

## A. Foundation and central brain
- [x] Typed task request/result contracts and lifecycle statuses
- [x] Initial department routing, central orchestration and allow-listed Brain dispatch
- [x] Declarative skill manifest and in-memory registry lifecycle
- [x] SQLite-backed durable task request/result storage foundation
- [x] Persistent SQLite skill catalog with versioned manifests and reviewed lifecycle state
- [x] Governed skill execution for host-registered operations, active-state checks, schema validation, server-resolved permission scopes, explicit approval for consequential scopes and minimal audit digests
- [x] Authenticated skill execution API with fail-closed permission resolution
- [x] Built-in private knowledge-search skill with authenticated-user isolation
- [x] Optional source-provenance research-search skill when a search provider is configured
- [ ] Versioned schema migrations and dependency-aware planner
- [ ] Bounded concurrency, durable execution queue, idempotency and cancellation
- [x] FastAPI task API with both private service-token mode and user-session mode
- [x] Bounded, authenticated, per-user task history endpoint with owner isolation
- [x] Runtime factory composes model gateway, departments, persistence and user authentication

## B. Security and identity
- [x] SQLite account/session primitives: normalized unique email, PBKDF2 password verifier, opaque random session token, token-hash persistence, expiry and revocation
- [x] User registration, login, logout and current-user API routes
- [x] Per-user task ownership isolation in SQLite task reads and writes
- [x] Android session token encrypted with AES-GCM using Android Keystore
- [ ] Login abuse protection, rate limits, account recovery, email verification, MFA and session/device management
- [ ] Permission scopes, approval inbox, audit events, secret manager and credential rotation
- [ ] Threat model, independent security review and remediation

## C. AI providers and routing
- [x] Provider-neutral model adapter and bounded request/response contract
- [x] OpenAI Responses, Anthropic Messages, xAI Grok Responses and DeepSeek adapters (mocked contract tests only)
- [x] Configurable provider registration and transient-unavailability fallback
- [ ] Live provider verification, capability-aware routing, budgets, quotas, retries and cost reporting
- [ ] Emergency provider disable and user consent for external processing

## D. Skills and departments
- [x] Six model-backed departments registered in the Brain
- [x] Optional Tavily search adapter for Research, with bounded results, HTTPS source validation, untrusted-excerpt handling and source list
- [x] Runtime factory enables Tavily Research when TAVILY_API_KEY is configured server-side
- [ ] Coding department with isolated sandbox and test execution
- [x] Persistent declarative skill catalog and governed allowlisted host-operation execution with schema checks, server-resolved permission scopes, approval gates and audit digests
- [ ] OS/process-isolated execution sandbox, hard CPU/memory/time limits, skill evaluation evidence and rollback
- [ ] Real specialist workflows for design, data, business, writing and productivity

## E. Knowledge, memory and storage
- [ ] Storage adapter abstraction and object/file storage
- [x] User-owned text knowledge records, FTS5 search and per-user access filtering
- [ ] File/document ingestion, chunking, embeddings, provenance and access filtering across all indexes
- [ ] User-controlled memory inspection, correction, export and deletion
- [ ] Retention across indexes, caches and backups
- [ ] Encryption-at-rest, backups, restoration and capacity/cost dashboard

## F. Android and user experience
- [x] Kotlin Android Jetpack Compose app and CI debug APK build
- [x] Registration/login, current-session validation, logout and task submission client
- [x] HTTPS-only API client and Keystore-backed encrypted session persistence
- [ ] Configure real HTTPS backend domain and verify live Android-to-API-to-Brain workflow
- [ ] Android unified chat-history screen consuming the task-history API, projects, attachments, live task progress/cancellation and result views
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
AJUSTA now has a user-session FastAPI mode with registration/login/logout/current-user routes and per-user task isolation. The Android client has login/register, session validation, logout, task submission, HTTPS-only transport, Keystore-backed token encryption, a recent per-user task-history screen, and polling of persisted task status while synchronous task execution is running. A runtime factory composes backend services, enables optional Tavily research from server configuration, and exposes a governed skill engine. The Android debug APK CI workflow passed after earlier integration changes, but no live mobile-to-deployed-backend workflow is verified. The backend includes a bounded authenticated task-history endpoint that returns only the caller's own recent tasks, plus user-owned text knowledge storage with FTS5 search, a built-in knowledge-search skill scoped to the authenticated user, and an optional research-search skill that returns source provenance when a provider is configured. Skills execute only through trusted host-registered operations, with active-state checks, input/output validation, server-resolved permission scopes, approval for consequential scopes and minimal audit digests. This is an allowlisted dispatcher, not an OS sandbox; no uploaded or model-generated code is executed. Research and model provider tests are mocked, not live credential verification. No public API domain, production deployment, isolated coding sandbox, autonomous learning loop, complete file/document storage system or live end-to-end mobile workflow has been verified. This is not 100% complete.

## J. End-to-end capability targets
- [x] Model adapters and mocked provider contract tests
- [x] Synchronous task execution and persisted terminal results
- [x] User-scoped task API and ownership isolation
- [x] Bounded per-user task-history listing API
- [x] Android recent task-history screen with task status/result/error and refresh
- [x] Android polling of persisted task status during synchronous submission
- [x] Native Android login/task client and successful debug APK build
- [x] Optional source-backed Research handler with Tavily search adapter
- [ ] Per-user authenticated live Android-to-Brain workflow against a deployed HTTPS API
- [ ] Central Brain with model routing, dependency graphs, progress, cancellation and result evaluation
- [x] Governed allowlisted skill dispatcher with schema validation, server-side permission resolution, approval gates and minimal audit digests
- [ ] Isolated skill/code sandbox with hard resource limits, full review/evaluation pipeline and rollback
- [ ] Complete multi-user database, adaptive object/file storage, backups and restore
- [ ] Reviewed learning engine and persistent skill catalog
- [ ] Real department integrations and evidence-backed end-to-end acceptance tests
