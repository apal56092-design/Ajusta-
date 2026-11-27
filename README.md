# AJUSTA
## Unified Artificial Intelligence & Intelligence Operating System

> **One System. Multiple Intelligences. Expanding Possibilities.**

AJUSTA is an ambitious, modular AI ecosystem designed as a Jarvis-inspired operating system: one central intelligence coordinating multiple models, specialist skills, knowledge sources, storage systems and approved tools.

Its goal is to help people move from an objective to a well-researched, verified and useful result: understand the request, plan the work, select appropriate capabilities, coordinate execution, evaluate the outcome and explain what was completed.

**Important project-status statement:** The repository now includes an initial Python backend foundation: deterministic request planning, typed task request/result contracts, a central orchestration boundary, department-availability reporting, a consequential-action approval gate, a declarative in-memory skill registry with reviewed lifecycle states, unit-test specifications, and a GitHub Actions test workflow. These components create plans only; they do not yet connect real AI providers, execute specialist work, or provide a production app. Other features remain planned until implemented and verified.

---

## 1. Vision

AJUSTA is intended to become more than a conventional chatbot. It is planned as a unified workspace in which research, reasoning, software engineering, design, data analysis, knowledge management and automation can cooperate.

The system should:
- Understand the user's objective and constraints.
- Break complex requests into manageable tasks.
- Choose suitable models, tools and specialist modules.
- Share relevant context between authorized modules.
- Verify important outputs against evidence or tests.
- Report uncertainty, limitations and completion status honestly.
- Keep users in control of sensitive or consequential actions.

The vision is ambitious; delivery will be incremental and evidence-driven. The complete target capability specification is in [docs/MASTER_CAPABILITIES.md](docs/MASTER_CAPABILITIES.md).

## 2. Core Architecture

### Central Intelligence
The orchestration layer responsible for interpreting requests, creating task plans, routing work, collecting results and checking whether the objective was met.

### Specialist Departments
Independent modules with clear interfaces and responsibilities:
- **Research:** source discovery, evidence review and synthesis.
- **Coding:** software planning, implementation, debugging and testing.
- **Design:** product concepts, interface structure and design guidance.
- **Data Intelligence:** data validation, analysis and visualization.
- **Business Intelligence:** planning, market research and decision support.
- **Automation:** permissioned workflow orchestration.
- **Knowledge:** document ingestion, retrieval and project context.

### Shared Knowledge and Adaptive Storage
A controlled layer for storing and retrieving project documents, approved knowledge, task context and references. Storage should scale through replaceable local or cloud adapters, with encryption, backups, access controls, retention, export and deletion. External storage and paid capacity require user consent.

### Skill Learning and Improvement
AJUSTA should discover capability gaps, research solutions, draft new skills, test them in isolated environments, evaluate results and activate approved versions with rollback. This is controlled, evidence-based improvement—not unrestricted self-modification.

### Model & Tool Connectors
Provider-neutral adapters will make it possible to connect different AI models and external tools without coupling the entire system to one provider. External services may require separate accounts, API keys, permissions and usage costs.

## 3. Intended Request Lifecycle

1. Receive a user request.
2. Identify the desired outcome and constraints.
3. Ask for clarification only when necessary.
4. Create a task plan and identify dependencies.
5. Select approved specialist modules and connectors.
6. Execute permitted work.
7. Validate results using evidence, checks or tests.
8. Combine findings into a clear response or deliverable.
9. Record relevant project decisions and completion status.
10. Request explicit approval before sensitive external actions.

## 4. Planned Capability Areas

| Area | Intended responsibility | Status |
|---|---|---|
| Central Intelligence | Initial deterministic planning and routing boundary | Partial |
| Research | Evidence-based investigation | Planned |
| Coding | Software engineering workflows | Planned |
| Design | Product and interface design support | Planned |
| Data Intelligence | Data quality and analysis | Planned |
| Business Intelligence | Business research and planning | Planned |
| Knowledge System | Document and context retrieval | Planned |
| Automation | Permissioned workflow execution | Planned |
| Android Client | Mobile user interface | Planned |
| Security & Governance | Initial consequential-action approval gate | Partial |

## 5. Technology Direction

Initial technology direction:
- **Android client:** Kotlin.
- **AI orchestration and backend services:** Python.
- **Interfaces:** documented APIs and provider adapters.
- **Storage:** selected according to deployment and data requirements.
- **Testing:** automated unit, integration and end-to-end checks appropriate to each component.

The final stack will be confirmed as implementation begins. No provider, database or cloud service is assumed to be connected until configured and tested.

## 6. Repository Structure

The repository will grow around explicit module boundaries. The initial proposed layout is:

```text
AJUSTA/
├── android/                 # Kotlin Android application
├── backend/                 # Backend services and API
├── brain/
│   ├── central_intelligence/ # Task understanding and orchestration
│   ├── reasoning/            # Planning and evaluation
│   └── memory/               # Controlled context management
├── departments/
│   ├── research/
│   ├── coding/
│   ├── design/
│   ├── data/
│   ├── business/
│   └── automation/
├── knowledge/                # Retrieval and document knowledge
├── connectors/               # AI providers and external tools
├── security/                 # Auth, permissions and policy
├── tests/                    # Automated tests
├── docs/                     # Architecture, decisions and roadmap
├── .gitignore
└── README.md
```

This is a target structure, not a claim that every directory or feature already exists.

## 7. Security, Privacy and Human Control

Security is a core design requirement. No system can honestly guarantee 100% security; AJUSTA will measure implemented controls, test results, audit findings and residual risks:

- Never commit API keys, passwords, tokens or private credentials.
- Keep secrets in environment variables or a dedicated secret manager.
- Apply least-privilege permissions to tools and modules.
- Validate external input and treat retrieved content as untrusted data.
- Keep sensitive actions behind explicit user approval.
- Make data retention and deletion behavior clear.
- Record important operations without exposing secrets.
- Test authorization boundaries and failure cases.

AJUSTA must not silently perform consequential actions or claim that an external action succeeded without confirmation from the relevant service.

## 8. Quality and Verification

Each implemented capability should include:
- A clear specification and defined inputs/outputs.
- Automated tests for expected behavior and edge cases.
- Error handling and useful diagnostics.
- Documentation for setup and operation.
- Verification evidence before its status is marked complete.

Tests must be run using the commands documented by each component. A feature is not considered complete merely because code has been written.

## 9. Master Capability Specification

The target design—including Jarvis-style orchestration, broad skill discovery, controlled skill learning, adaptive storage, research-first behavior and measurable security—is documented in [docs/MASTER_CAPABILITIES.md](docs/MASTER_CAPABILITIES.md).

## 10. Development Roadmap

### Phase 0 — Foundation
- Confirm repository conventions.
- Document architecture and project decisions.
- Add secure configuration and contribution guidance.

### Phase 1 — Central Intelligence MVP
- Define a request/task data model.
- Implement a small, deterministic task planner.
- Add validation and unit tests.
- Return transparent task status and errors.

### Phase 2 — First Specialist Department
- Add a research or coding department behind a stable interface.
- Test routing, result handling and failure behavior.

### Phase 3 — Model Connectors
- Add provider adapters with explicit configuration.
- Handle timeouts, rate limits, unavailable providers and cost visibility.

### Phase 4 — Knowledge System
- Add document ingestion, indexing, retrieval and access controls.

### Phase 5 — Android Client
- Build the Kotlin interface and connect it to authenticated backend APIs.

### Phase 6 — Controlled Automation
- Add user-approved workflows, audit logs and permission checks.

### Phase 7 — Evaluation and Expansion
- Measure quality, reliability, latency and cost.
- Expand capabilities only when they can be tested and maintained.

## 11. Project Principles

1. Evidence over unsupported claims.
2. Clear module boundaries over one giant codebase.
3. Tests before declaring behavior complete.
4. Privacy and security from the beginning.
5. Human approval for sensitive operations.
6. Transparent limitations and uncertainty.
7. Incremental delivery with measurable progress.
8. Replaceable providers and extensible interfaces.

## 12. Current Status

**Current stage: Backend orchestration foundation.**

The repository contains a deterministic planner, a central orchestration API, a policy approval gate, unit-test specifications, and a CI workflow intended to run the backend tests. This is not yet a connected multi-model AI system: real specialist execution, AI provider adapters, persistent skill storage, sandboxed skill execution, knowledge storage, authentication, and the Kotlin Android client still require implementation. Test status must be confirmed from an actual CI run before calling the tests passing.

---

## The Objective

Build a dependable, expandable AI ecosystem in which multiple specialized capabilities work together through one coordinated system.

**AJUSTA — One System. Multiple Intelligences. Expanding Possibilities.**
