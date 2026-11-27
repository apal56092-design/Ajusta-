# AJUSTA Unified Intelligence Architecture

## Mission
Build AJUSTA as a unified, measurable, secure AI work system—not as a thin chat interface or a claim that one model is universally superior. The system should select and coordinate available models, tools, departments, skills and user-owned knowledge to complete permitted tasks with evidence and clear status.

## Architecture layers

### 1. Central Intelligence Core
Owns request intake, identity context, policy checks, task decomposition, capability routing, budget/deadline controls, evidence collection, result verification and response synthesis. It chooses only configured providers and approved tools. It must expose why a route was selected and when it fell back.

### 2. Specialist agents and departments
Research, coding, data, design, business and productivity specialists use typed input/output contracts. Delegation is bounded by depth, parallelism, time, token/cost budgets and user permissions. Agents cannot grant themselves permissions or execute arbitrary code. Conflicting outputs are compared and escalated or qualified.

### 3. Reasoning and verification
Complex tasks are decomposed into explicit steps. Each step records assumptions, evidence, dependencies and completion state. Independent checks validate calculations, citations, code tests and output constraints. Confidence is treated as an estimate, not a guarantee.

### 4. Research and knowledge
Retrieval gathers multiple sources, preserves URL/title/date/excerpt provenance, checks source quality and separates source claims from synthesis. User knowledge remains owner-scoped. Document ingestion must enforce MIME, size, parser, malware-scanning, retention and access controls before indexing.

### 5. Skill system
Skills have versioned manifests, typed schemas, declared permission scopes, trusted host operations, review/approval state, evaluation tests and rollback. Untrusted generated code must run only in a separately designed OS/process-isolated sandbox with strict resource limits; current allowlisted dispatch is not that sandbox.

### 6. Durable task execution
The SQLite queue primitives are a foundation only. The complete engine still needs a bounded worker lifecycle, idempotent enqueue, lease renewal, task-store synchronization, cancellation tokens, progress events, retry classification, deadlines and graceful shutdown. Queue state and user-visible task state must reconcile after crashes.

### 7. Persistent memory
Memory is explicit, user-controlled and scoped. It supports retrieval, correction, export and deletion across primary records and derived indexes. Do not silently train model weights from user data. Improvement uses evaluated software/configuration changes with review and rollback.

### 8. Multimodal interface
Text, image, audio, video and document capabilities are added through adapters with explicit device permissions, data minimization, provenance and retention controls. Android is one client of a stable API, not the intelligence layer itself.

### 9. Security and governance
Authentication, least privilege, server-side permission resolution, explicit approvals for consequential actions, rate limits, secrets management, audit events, privacy controls, threat modelling and incident response are cross-cutting requirements.

### 10. Evaluation and operations
Every department has task-specific benchmark sets. Measure task success, factuality/grounding, citation quality, code test pass rate, robustness, latency, cost and privacy/security failures. Production releases require CI, static analysis, dependency and secret scanning, observability, backup/restore drills, staged rollout and rollback.

## Delivery sequence

1. **Reliability foundation:** wire the durable queue to a bounded worker; add idempotency, lease renewal, cancellation, progress, crash recovery and API/Android status synchronization.
2. **Security foundation:** threat model, rate limits, approval inbox, audit events, secret rotation and sandbox design.
3. **Intelligence core:** capability registry, provider routing, budgets, typed planning graph, evidence and independent verification.
4. **Specialists and research:** bounded multi-agent delegation, deep research, source verification and real department workflows.
5. **Knowledge and memory:** file ingestion, chunking, provenance, embeddings/knowledge graph and user controls.
6. **Skills and controlled improvement:** reviewed skill authoring, isolated evaluation, benchmark-driven changes and rollback.
7. **Multimodal and Android:** image/audio/video/document workflows, permissions, project workspace and full live API integration.
8. **Production readiness:** load tests, monitoring, backups, recovery, privacy/legal review and staged deployment.

## Definition of done
A feature is not complete because a file or large code block exists. It is complete only when its contract is defined, implementation is integrated, tests cover failure and permission boundaries, CI passes, documentation states limitations, and end-to-end evidence exists where applicable. No claim of superiority is made without comparative benchmark evidence.

## Current known boundary
AJUSTA currently has a FastAPI backend, SQLite stores, model adapter interfaces, department routing, authenticated APIs, user-scoped task history and knowledge search, a governed host-operation skill dispatcher, a Kotlin Android client and a durable queue primitive. The queue is not yet wired to an active worker. Provider and research contract tests are mocked; live credentials and deployed end-to-end operation are not verified. The skill dispatcher is not an OS sandbox. There is no autonomous model-weight learning loop.
