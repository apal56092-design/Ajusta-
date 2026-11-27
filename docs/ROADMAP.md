# AJUSTA Development Roadmap

A milestone is complete only after implementation, automated tests, documentation and verification evidence are committed.

## Milestone 0 — Repository foundation
- [x] Initial README, architecture, roadmap and security baseline
- [x] Initial Python backend planner and orchestration boundary
- [x] Approval-policy foundation and CI workflow definition
- [ ] Confirm CI run status and resolve any failures
- [ ] Add contribution, local setup and threat-model documentation

## Milestone 1 — Central Intelligence contracts
- [ ] Typed request, task, result and structured error models
- [ ] Stable department/skill interface and registry
- [ ] Dependency-aware bounded task plans
- [ ] Structured partial-failure and cancellation handling
- [ ] Unit and integration tests for routing, authorization and edge cases

## Milestone 2 — Security foundation
- [ ] Authentication and server-side authorization
- [ ] Permission scopes and least-privilege policy
- [ ] Secret management, input validation and safe configuration
- [ ] Audit events that exclude secrets and unnecessary personal data
- [ ] Threat model and security test suite

## Milestone 3 — First real AI provider
- [ ] Provider-neutral adapter contract
- [ ] Server-side environment/secret-manager configuration
- [ ] Timeouts, retries, rate limits, quotas and cost visibility
- [ ] Provider failure and fallback tests
- [ ] No provider key in Android app or repository

## Milestone 4 — First specialist departments
- [ ] Research department with source provenance and evidence summaries
- [ ] Coding department with isolated execution and automated tests
- [ ] Shared typed result contract and validation
- [ ] Department-level permissions and resource limits

## Milestone 5 — Skill system and controlled learning
- [ ] Versioned skill manifest and registry
- [ ] Isolated skill execution and dependency controls
- [ ] Skill proposal workflow: draft, test, review, approve, activate
- [ ] Evaluation benchmarks and regression checks
- [ ] Rollback and disable controls
- [ ] No unrestricted self-modification or self-granted permissions

## Milestone 6 — Adaptive storage and knowledge
- [ ] Storage adapter interfaces
- [ ] Database and object/file storage integration
- [ ] Document ingestion, indexing and retrieval with provenance
- [ ] Encryption, access controls and tenant isolation
- [ ] User-controlled retention, export and deletion
- [ ] Backups, restore tests, integrity checks and capacity/cost reporting
- [ ] Consent before external/cloud storage or paid capacity

## Milestone 7 — Android client
- [ ] Kotlin application skeleton
- [ ] Authenticated API client and secure session handling
- [ ] Chat/task submission, progress and approval screens
- [ ] Skill, storage, privacy and permission controls
- [ ] Accessible error, cancellation and offline states

## Milestone 8 — Approved connectors and automation
- [ ] Connector catalog with scopes and trust levels
- [ ] Explicit user approval for consequential actions
- [ ] Audit logs, rate limits, safe failure and revocation
- [ ] Integration tests against sandbox/test accounts

## Milestone 9 — Evaluation and release
- [ ] Capability benchmarks by department
- [ ] Reliability, latency, cost and load testing
- [ ] Dependency and secret scanning
- [ ] Independent security review and remediation
- [ ] Incident response and disaster-recovery drills
- [ ] Release only with verified controls and honest status reporting

## Definition of done
A milestone is complete only when its code exists, automated tests pass, setup instructions are current, security/privacy implications are reviewed, and README/status documentation reflects reality. Aspirational features remain marked planned until verified.
