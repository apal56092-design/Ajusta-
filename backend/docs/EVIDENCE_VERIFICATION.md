# AJUSTA Evidence Verification

The `ajusta_core.verification` module validates explicit provenance links between
structured claims and evidence records.

## Status meanings

- `supported`: at least one explicitly linked source is marked `supports`, with no linked contradiction.
- `contradicted`: at least one linked source is marked `contradicts`, with no linked support.
- `contested`: linked evidence includes both declared support and contradiction.
- `unsupported`: no linked support or contradiction is present (including context-only or no links).
- `invalid`: one or more claim source IDs do not exist in the supplied evidence set.

## Important limits

This is a deterministic provenance and evidence-direction checker. It does not
verify that a publisher is authentic, fetch or independently inspect URLs, decide
whether an excerpt logically entails a claim, or establish that a claim is true.
The `relation` field is a declared annotation supplied by an upstream reviewer or
pipeline and must not be treated as a model-independent truth label. HTTPS is a
transport-format requirement, not proof of source trustworthiness.

All claim-to-source links are explicit. Unlinked evidence never changes a claim's
status. Duplicate IDs are rejected and report order follows input order.
