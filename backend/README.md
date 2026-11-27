# AJUSTA Backend Foundation

AJUSTA is an evolving modular AI system, not yet a production-ready autonomous agent.

## Setup

- Python 3.11+
- Install: `python -m pip install -e '.[test]'`
- Tests: `python -m pytest`

## Implemented modules

- **Contracts and planner:** validated task request/result schemas, deterministic task planning and lifecycle states.
- **Central Brain:** explicit department allow-list, orchestration and reviewed handler dispatch.
- **Model gateway:** provider-neutral adapter plus OpenAI Responses, Anthropic Messages, xAI/Grok and DeepSeek adapters. Provider contract tests use mocked transports; live credentials/calls are not verified.
- **Research engine:** optional Tavily search adapter, bounded query/result counts, HTTPS-only source records, evidence snippets passed as untrusted content to the model, and an appended source list. Configure `TAVILY_API_KEY` as a server-side secret and pass `TavilySearchProvider()` to `register_model_departments(..., research_search_provider=...)`. No arbitrary page URLs are fetched by this adapter.
- **Other departments:** coding, design, data, business and automation currently provide model-backed text reasoning only. They do not execute code or control external apps.
- **Task service and storage:** synchronous execution with SQLite task persistence and optional user ownership.
- **User identity:** PBKDF2-HMAC-SHA256 password verifiers, normalized unique email accounts, opaque random sessions, hashed session-token persistence, expiry and revocation.
- **FastAPI:** register/login/logout/current-user endpoints in user-session mode, and task submission/read with per-user task ownership isolation. A legacy shared-token mode remains for private controlled testing only.
- **Skills:** declarative manifests and an in-memory lifecycle registry; generated skills are not executed.


## Start a configured backend

The runtime factory composes the model gateway, all six departments, optional Tavily Research, task persistence and user-session auth:

```python
from ajusta_core import create_runtime_app

app = create_runtime_app(
    database_path="/var/lib/ajusta/ajusta.sqlite3",
    auth_database_path="/var/lib/ajusta/identity.sqlite3",
)
```

Provide at least one model provider key and model name as server-side environment variables (for example `OPENAI_API_KEY` and `OPENAI_MODEL`). Add `TAVILY_API_KEY` to enable web search for the Research department. Never commit these secrets. The factory does not configure TLS, a public domain, reverse proxy, backups, rate limiting or deployment hosting.

## API usage

Create an account/session store and pass it to the app factory:

```python
from ajusta_core import SQLiteAuthStore, create_app

auth_store = SQLiteAuthStore("/var/lib/ajusta/auth.sqlite3")
app = create_app(task_service, auth_store=auth_store)
```

Set up your ASGI server and TLS termination in the deployment environment. Never embed server credentials or provider API keys in an Android APK. User-scoped API routes are ready for a configured backend, but this repository does not yet include a production deployment, public domain, or configured model provider secrets.

## Android client

The native Kotlin/Jetpack Compose client now includes registration/login, session validation, task submission and logout. Session tokens are encrypted using an AES-GCM key held in Android Keystore. Configure the backend base URL at build time:

```bash
cd android
gradle -PAJUSTA_API_BASE_URL=https://your-real-api-domain.example :app:assembleDebug
```

The default URL is a non-routable placeholder and must be replaced with a real HTTPS deployment URL. Android CI only builds the app; it does not verify a live backend connection.

## Remaining production work

- Login abuse protection, rate limits, account recovery, email verification, MFA and security review.
- Production database migrations, tenant lifecycle, encryption-at-rest, backup/restore and operational recovery.
- Durable async job queue, cancellation, retries, streaming, idempotency and bounded concurrency.
- Live provider verification, routing budgets, quotas, retries and cost reporting.
- Coding sandbox, file execution, real specialist tools, persistent skills and controlled learning/review/rollback.
- Document ingestion/indexing, user-controlled memory, adaptive object storage and retention.
- Observability, load tests, threat model, privacy/legal review and deployment operations.
- Android integration tests, real endpoint configuration, release signing and full end-to-end acceptance tests.

AJUSTA is not 100% complete. A successful local/CI build or mocked provider test is not evidence of live production behavior.
