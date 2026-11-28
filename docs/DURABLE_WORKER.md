# Durable worker runtime

`DurableTaskWorker` is a bounded, explicitly managed polling worker for
`SQLiteTaskQueue`. It claims at most one item per iteration, invokes only a
trusted handler supplied by the host application, and completes the lease with
a success/failure outcome. Handler exception messages are not copied into queue
storage; only the exception type is retained. Queue transitions and worker lifecycle
milestones are persisted as owner-scoped progress events and returned by the async
status endpoint.

Start and stop are explicit. The worker is not started as an import or app
construction side effect. Applications must own its lifecycle and call
`stop()` during shutdown. A stop request waits for the current handler up to
the configured timeout; Python cannot safely interrupt a handler that ignores
cooperative cancellation.

Handlers may accept a second `TaskExecutionContext` argument. It provides
`cancellation_requested`, `raise_if_cancelled()`, and lease-bound
`report_progress()`. A running-task DELETE request records a cancellation
request; the handler must poll the context and stop at a safe checkpoint. The
worker then records a terminal `cancelled` state. Existing one-argument
handlers remain compatible. The worker renews its lease periodically while a
handler is active, using the current lease token. Lease renewal stops when the
handler exits or the lease is no longer owned.

## Important limits

- This is one worker thread per instance, not a distributed worker pool.
- Progress currently reports coarse lifecycle milestones (queued, worker started,
  handler dispatched/returned, terminal result), not token-level or model-streaming
  progress. Specialist handlers can later report finer progress using the lease-bound
  `report_progress` API.
- Cancellation is cooperative: a handler blocked inside an external call cannot
  be forcibly interrupted. Provider calls should use bounded timeouts and handlers
  should check cancellation between steps.
- Lease renewal reduces accidental expiry for long handlers, but does not make
  execution exactly-once. A process crash can still cause a retry; handlers should
  remain idempotent.
- Queue payloads are untrusted data. The worker never evaluates payload text,
  imports user modules, launches processes, or executes generated code.
- The authenticated async status API exposes the latest progress percentage,
  message, and up to 50 persisted progress events. Events are filtered by task owner.
