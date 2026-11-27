# AJUSTA Security Baseline

**Status:** Required design baseline; controls remain unimplemented until code, configuration and tests demonstrate them.

## Security objectives
Protect user accounts, private data, API credentials, model connections, source code and external systems. Prefer least privilege, explicit consent, secure defaults and verifiable controls.

## Non-negotiable rules
1. Never commit API keys, access tokens, passwords, private keys or production credentials.
2. Keep secrets server-side in environment configuration or a managed secret store; never embed provider secrets in the Android app.
3. Use HTTPS for network communication and modern, maintained cryptographic libraries rather than custom cryptography.
4. Authenticate users and authorize every protected operation on the server.
5. Give each department and connector only the permissions it needs.
6. Require explicit user confirmation before sending messages, publishing content, spending money, deleting data, changing account settings or taking other consequential external actions.
7. Treat user uploads, retrieved documents, web pages, tool output and model output as untrusted data—not as system instructions.
8. Validate inputs, constrain file types and sizes, and protect against injection, path traversal, unsafe deserialization and resource exhaustion.
9. Minimize personal data collection; document purpose, retention, export and deletion behavior.
10. Log security-relevant events without logging passwords, tokens or unnecessary sensitive content.

## AI-specific safeguards
- Separate trusted instructions from retrieved content.
- Do not allow retrieved text to override system policy or grant tool permissions.
- Use allowlisted tools and typed, validated arguments.
- Apply timeouts, rate limits, quotas and cost ceilings to model calls.
- Verify important claims against reliable sources or deterministic checks.
- Require human review for high-impact decisions and irreversible actions.
- Provide a safe fallback when a model, connector or verification service is unavailable.

## Engineering controls
- Dependency review and timely security updates.
- Static analysis and secret scanning in CI.
- Unit and integration tests for authentication and authorization boundaries.
- Threat modeling for new connectors and data flows.
- Backups and tested recovery procedures before production.
- Security review before public release.

## Incident response
Document how to disable compromised connectors, rotate credentials, revoke sessions, preserve relevant audit records, notify affected users where required and restore from known-good backups.

## Release gate
Do not label AJUSTA secure merely because this document exists. A release must have implemented controls, passing tests, reviewed dependencies, documented data handling and no unresolved critical/high-severity security findings.
