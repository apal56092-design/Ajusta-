# AJUSTA
## Unified Artificial Intelligence & Intelligence Operating System

> **One System. Multiple Intelligences. Expanding Possibilities.**

AJUSTA is an ambitious, modular AI ecosystem designed as a Jarvis-inspired operating system: one central intelligence coordinating multiple models, specialist skills, knowledge sources, storage systems and approved tools.

Its goal is to help people move from an objective to a well-researched, verified and useful result: understand the request, plan the work, select appropriate capabilities, coordinate execution, evaluate the outcome and explain what was completed.

**Current project-status statement (2026-11-28):** AJUSTA has a working Python backend foundation with deterministic planning, authenticated user sessions, multiple server-side model-provider adapters and fallback routing, specialist department execution, a bounded multi-agent coordinator, source-evidence verification, persistent SQLite task/skill/knowledge stores, governed skill execution, durable task queues and workers, async task progress/cancellation, privacy-safe model-routing telemetry, and a governed supervised-training dataset/run engine. The Kotlin Android client has task submission and progress integration. These are implemented components, not proof of production deployment or superiority over other AI systems. Live provider calls require valid server credentials; actual weight training requires a deployment-registered framework-specific trainer and suitable compute. See the current implementation docs and CI results before treating any capability as production-ready.

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
A persistent SQLite knowledge store now supports owner-scoped records, full-text search, source provenance annotations, and authenticated create/list/search/delete APIs. Broader document ingestion, embeddings, encrypted cloud storage, backup/restore, and retention automation remain future work.

### Governed Training and Learning
A supervised-training foundation now provides owner-scoped datasets, reviewed input/target examples, bounded JSON configuration, explicit approval, host-registered trainer adapters, persisted run status, sanitized failures, and numeric metrics. Actual fine-tuning is not claimed until a real framework adapter, compute, evaluation, and artifact lifecycle are configured. See [docs/TRAINING_SYSTEM.md](docs/TRAINING_SYSTEM.md).

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
| Central Intelligence | Deterministic planning, department dispatch, bounded multi-agent coordination | Partial / implemented foundation |
| Model Routing | Server-side provider adapters, fallback and privacy-safe attempt telemetry | Implemented; live credentials deployment-dependent |
| Research | Configurable search adapter and source evidence structures | Partial |
| Coding | Specialist department adapter and task coordination | Partial |
| Design | Specialist department adapter and task coordination | Partial |
| Data / Business | Specialist department adapters | Partial |
| Knowledge System | Persistent owner-scoped FTS knowledge and provenance annotations | Implemented foundation |
| Training System | Curated datasets, explicit approval, trusted trainer registry, run metrics | Implemented orchestration; real trainer not yet provisioned |
| Skills | Persistent catalog, permissioned host operations, audit records | Partial |
| Automation | Durable task queue, worker, progress and cooperative cancellation | Partial |
| Android Client | Authenticated API and async task progress integration | Partial |
| Security & Governance | User sessions, owner isolation, permissions, approval gates, evidence checks | Partial; ongoing hardening |

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

### Implemented foundation
- Authenticated API and owner-scoped SQLite storage.
- Model-provider adapters, routing, and fallback telemetry.
- Multi-agent department coordination and evidence verification.
- Durable task queue, worker, progress events, and cooperative cancellation.
- Persistent knowledge and governed skill execution.
- Training datasets, approval gates, and trainer adapter interface.
- Android async task integration.

### Next engineering milestones
- Register and validate a real framework-specific training adapter.
- Add train/validation/test splitting, dataset quality checks, and leakage detection.
- Add evaluation gates, checkpoint/artifact storage, versioning, rollback, and human promotion.
- Add long-running training jobs with durable scheduling, progress, resource limits, and cancellation.
- Complete Android training/knowledge interfaces and backend end-to-end tests.
- Deploy staging infrastructure and verify live model/provider behavior with authorized credentials.

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

**Current stage: Expanding backend intelligence and governed learning foundation.**

The repository contains working backend modules for authenticated orchestration, provider adapters, specialist coordination, evidence verification, persistent owner-scoped knowledge, durable async tasks, governed skill execution, and supervised-training orchestration. Backend tests run in GitHub Actions. The training engine currently manages curated datasets and calls only trusted host-registered trainer adapters; no framework-specific LLM fine-tuning adapter or GPU infrastructure is bundled. The Android client is partially integrated. Production deployment, live provider credentials, real model training, evaluation gates, artifact promotion, and additional end-to-end validation remain open work.

---

## The Objective

Build a dependable, expandable AI ecosystem in which multiple specialized capabilities work together through one coordinated system.

**AJUSTA — One System. Multiple Intelligences. Expanding Possibilities.**


## Configuring live LLM providers

AJUSTA includes server-side adapters for OpenAI Responses, Anthropic Messages,
xAI Grok, DeepSeek Responses-compatible, and Google Gemini generateContent.
Adapters are not the same as active credentials: a provider is registered only
when both its API key and model name are configured on the backend.

Supported environment variables:

| Provider | API key | Model |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_MODEL` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` |
| xAI | `XAI_API_KEY` | `XAI_MODEL` |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_MODEL` |
| Google Gemini | `GEMINI_API_KEY` | `GEMINI_MODEL` |

Set `AJUSTA_MODEL_PROVIDER_ORDER` to a comma-separated preference order,
for example `gemini,openai,anthropic,xai,deepseek`. Fallback is attempted only
when a provider is temporarily unavailable; authentication and request errors
are surfaced rather than silently routed elsewhere. Keep all keys in a server
secret manager or environment configuration. Never put provider keys in the
Android app or commit them to this repository.

No live provider connection is implied by adding an adapter. Live use requires
valid provider credentials, an available model, network access, and provider
billing/quota. The automated tests use an injected offline transport and do
not validate live credentials or model quality.
