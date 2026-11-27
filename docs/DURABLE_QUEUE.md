# AJUSTA — Durable queue primitives

This increment adds a persistent SQLite queue foundation. It provides bounded JSON
payloads, per-owner reads, atomic worker claims, expiring leases, bounded retries,
lease-token completion, and owner-checked cancellation of queued items.

Important: this is queue storage, not yet an active background execution service.
No worker is started by the API runtime, and running work cannot yet be interrupted.
The existing task endpoint remains synchronous. A later integration step must add
a bounded trusted worker lifecycle, queue-to-task status synchronization, and
cooperative cancellation before this is presented as end-to-end background execution.
