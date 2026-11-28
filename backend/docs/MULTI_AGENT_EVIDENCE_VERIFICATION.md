# Multi-Agent Evidence Verification Integration

Departments may optionally return a `DepartmentEvidenceResponse` instead of plain
text. It contains bounded structured claims and evidence records. The multi-agent
coordinator verifies explicit claim/source links and carries the report alongside
the department result. The task service adds a concise verification section to the
combined task result.

Plain-string department handlers remain fully backward compatible. They are not
silently treated as verified: no verification section is emitted for them.

Statuses are provenance labels based on the declared evidence relation:
supported, contradicted, contested, unsupported, or invalid. This integration
does not fetch URLs, authenticate publishers, or prove semantic entailment. It
does not infer agreement between agents as evidence. A structured response must
be supplied by a trusted department adapter; model-generated labels still require
independent review before high-stakes use.
