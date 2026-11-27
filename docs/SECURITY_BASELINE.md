# AJUSTA Security Baseline

**Status:** Required design baseline. Controls remain unimplemented until code, configuration and tests demonstrate them.

## Security objective
Protect user accounts, private data, credentials, models, skills, source code, devices and connected services through defense in depth. Absolute security cannot be guaranteed; report measurable controls, test results, audit findings and residual risks instead of invented percentages.

## Non-negotiable controls
1. Never commit API keys, access tokens, passwords, private keys or production credentials.
2. Keep provider secrets server-side in a secret manager or protected environment configuration.
3. Use HTTPS and maintained cryptographic libraries; encrypt sensitive stored data and manage keys securely.
4. Authenticate users and authorize every protected operation on the server.
5. Enforce least privilege and isolated permission scopes for every department, skill, connector and device.
6. Require explicit approval for sending messages, publishing, purchases, deleting data, changing accounts, controlling devices or other consequential actions.
7. Treat uploads, retrieved documents, websites, tool outputs, model outputs and downloaded skills as untrusted.
8. Validate inputs and typed tool arguments; constrain file types, sizes, execution time, memory and network access.
9. Minimize personal data; document purpose, retention, export, deletion and external processing.
10. Log security-relevant events without logging passwords, tokens or unnecessary sensitive content.
11. Apply rate limits, quotas, abuse detection and cost ceilings.
12. Fail closed when identity, authorization or approval cannot be verified.

## AI and skill safeguards
- Separate trusted system policy from user content and retrieved data.
- Defend against prompt injection; retrieved text cannot grant permissions or override policy.
- Run third-party or generated skills in a sandbox with minimal filesystem and network access.
- Require manifest review, dependency checks, automated tests and evaluation before activation.
- Prevent skills from granting themselves permissions, changing security policy or deploying unreviewed updates.
- Version skills and support disable, rollback and revocation.
- Require human review for meaningful permission or behavior changes.

## Storage and recovery
- Separate structured data, files, indexes, task context and audit records.
- Enforce tenant/object-level access checks and encryption in transit and at rest.
- Obtain consent before external storage providers or paid capacity are enabled.
- Provide retention controls, export and deletion workflows.
- Maintain encrypted backups, integrity checks and tested restoration procedures.

## Engineering controls
- Dependency review, vulnerability scanning and timely updates.
- Secret scanning and static analysis in CI.
- Unit and integration tests for authentication, authorization and isolation.
- Threat modeling for each new connector, skill runtime and data flow.
- Independent security review and penetration testing before production.
- Monitoring, incident response, credential rotation and session revocation procedures.

## Incident response
Document how to disable compromised skills/connectors, rotate credentials, revoke sessions, preserve appropriate audit evidence, notify affected users where required and restore from known-good backups.

## Release gate
Do not label AJUSTA secure merely because this document exists. A release requires implemented controls, passing tests, reviewed dependencies, documented data handling, tested recovery and no unresolved critical/high-severity security findings. Never claim 100% security or a mathematically unsupported security percentage.
