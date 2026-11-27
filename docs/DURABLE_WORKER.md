# Durable worker runtime

`DurableTaskWorker` is a bounded, explicitly managed polling worker for
`SQLiteTaskQueue`. It claims at most one item per iteration, invokes only a
trusted handler supplied by the host application, and completes the lease with
a success/failure outcome. Handler exception messages are not copied into queue
storage; only the exception type is retained.

Start and stop are explicit. The worker is not started as an import or app
construction side effect. Applications must own its lifecycle and call
`stop()` during shutdown. A stop request waits for the current handler up to
the configured timeout; Python cannot safely interrupt a handler that ignores
cooperative cancellation.

## Important limits

- This is one worker thread per instance, not a distributed worker pool.
- The queue lease must exceed the handler's maximum expected runtime. Lease
  renewal and cooperative cancellation of running work are not implemented yet.
- If a handler outlives its lease, another worker may reclaim the task. Handlers
  should therefore be idempotent.
- Queue payloads are untrusted data. The worker never evaluates payload text,
  imports user modules, launches processes, or executes generated code.
- This worker is not yet wired into the FastAPI task submission route or Android
  client. Synchronous task submission remains the active API behavior.
