# AJUSTA Governed Training System

## Purpose

AJUSTA now has a persistent supervised-training foundation. It separates four concerns:

1. **Dataset management** — owner-scoped datasets and reviewed input/target examples.
2. **Training governance** — explicit approval, bounded configuration, and a host-registered trainer allowlist.
3. **Execution lifecycle** — running/completed/failed run records with sanitized outcomes.
4. **Evaluation telemetry** — bounded numeric metrics returned by a trusted trainer.

This is a training orchestration engine and adapter contract. It is not, by itself, an LLM, a GPU runtime, or a claim that model weights have already been fine-tuned. A deployment must register a real trainer adapter backed by its selected training framework and hardware before actual optimization can run.

## Architecture

```text
Authenticated user
      |
      v
Training API (session required)
      |
      +--> Dataset Store (SQLite, owner scoped)
      |       +--> Dataset metadata
      |       +--> Input / target examples
      |       +--> Source provenance
      |
      +--> Explicit approval gate
              |
              v
       TrainingEngine
              |
              +--> Host-registered trainer allowlist
              |       +--> framework-specific adapter
              |       +--> bounded config
              |       +--> reviewed dataset only
              |
              v
       TrainingRun record
              +--> status
              +--> sanitized error code
              +--> numeric metrics
              +--> timestamps
```

## Data and isolation

- Every dataset, example, and run carries an authenticated owner ID.
- Dataset lookups and example writes are scoped to that owner.
- A user cannot append to or read another user's dataset by guessing its ID.
- Input and target examples are each limited to 8,000 characters.
- Dataset names are limited to 120 characters; descriptions to 1,000.
- Source annotations are limited to 500 characters.
- Training configuration is JSON-only and limited to 10 KB.
- A minimum of two examples is required to create a run.
- Run metrics are limited to 50 finite numeric values.
- Raw trainer exception messages are not persisted or returned.

## API

All routes require a valid authenticated user session and a configured training store/engine.

### Create a dataset

`POST /v1/training/datasets`

```json
{
  "name": "Reviewed reasoning examples",
  "description": "Human-reviewed supervised examples"
}
```

### Add an example

`POST /v1/training/datasets/{dataset_id}/examples`

```json
{
  "input": "What is 2 + 2?",
  "target": "4",
  "source": "human-reviewed"
}
```

### List datasets and examples

- `GET /v1/training/datasets`
- `GET /v1/training/datasets/{dataset_id}/examples`

### Start a run

`POST /v1/training/runs`

```json
{
  "dataset_id": "DATASET_ID",
  "trainer_name": "deployment_registered_trainer",
  "config": {"epochs": 2},
  "approved_by_user": true
}
```

The approval flag must be explicitly true. A trainer name is not executable code: it must resolve to a callable registered by the trusted host process. Unknown trainers are rejected.

### Inspect runs

- `GET /v1/training/runs`
- `GET /v1/training/runs/{run_id}`

## Registering a real trainer

A deployment can register a reviewed callable on the runtime's `app.state.training_engine`:

```python
def trusted_trainer(examples, config):
    # Invoke the deployment's approved training framework here.
    # Load only the intended base model and reviewed dataset.
    # Apply resource limits, timeouts, checkpoints, and evaluation.
    # Return finite numeric metrics; never return secrets or raw examples.
    return {"examples_seen": len(examples), "training_loss": 0.0}

app.state.training_engine.register_trainer("deployment_registered_trainer", trusted_trainer)
```

The example above illustrates the adapter contract only; it is not a model-training implementation. The host must supply the actual framework-specific training operation. AJUSTA deliberately does not accept Python source, shell commands, package installation requests, or executable model scripts from API users.

## Production readiness gates for actual fine-tuning

Before registering a production trainer, a deployment should provide:

- A selected base model and explicit license/usage review.
- An approved framework and pinned dependency versions.
- GPU/CPU/memory/time budgets and cancellation behavior.
- Dataset consent, provenance, retention, and deletion controls.
- Train/validation/test splits with leakage checks.
- Baseline metrics and held-out evaluation before promotion.
- Checkpoint integrity, model artifact versioning, rollback, and access control.
- Human review before a trained artifact becomes the active model.
- Monitoring for regressions, memorization, privacy leakage, and unsafe outputs.

A completed run means the registered adapter returned successfully and its metrics were stored. It does not automatically promote a model, prove quality, or guarantee truthful outputs.

## Current implementation boundary

Implemented in the core repository:

- SQLite dataset, example, and run persistence.
- Owner isolation and bounded validation.
- Explicit approval and trusted trainer registry.
- Authenticated dataset/run API.
- Sanitized failure records and bounded numeric metrics.
- Runtime composition and tests.

Not yet provisioned by the repository alone:

- A concrete Hugging Face/PyTorch/other framework trainer.
- GPU infrastructure or cloud training credentials.
- Model artifact storage, evaluation gates, and production model promotion.
- A long-running distributed training worker.

Those pieces depend on the deployment's model choice, hardware, budget, and provider access. The adapter boundary is intentionally explicit so AJUSTA does not pretend to train weights when no trainer is configured.
