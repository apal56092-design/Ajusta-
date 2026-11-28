import pytest

from ajusta_core.training import (
    TrainingEngine,
    TrainingRunStatus,
    SQLiteTrainingStore,
)


def _dataset(store, owner="user-one"):
    dataset = store.create_dataset(owner, "Reasoning examples", "Reviewed examples")
    store.add_example(owner, dataset.id, "Question: 2+2?", "Answer: 4", source="curated")
    store.add_example(owner, dataset.id, "Question: 3+3?", "Answer: 6", source="curated")
    return dataset


def test_training_datasets_are_owner_scoped_and_keep_source(tmp_path):
    store = SQLiteTrainingStore(tmp_path / "training.sqlite3")
    dataset = _dataset(store)

    assert len(store.list_examples("user-one", dataset.id)) == 2
    assert store.list_datasets("user-two") == ()
    assert store.list_examples("user-two", dataset.id) == ()
    assert store.list_examples("user-one", dataset.id)[0].source == "curated"


def test_dataset_rejects_invalid_and_oversized_examples(tmp_path):
    store = SQLiteTrainingStore(tmp_path / "training.sqlite3")
    dataset = store.create_dataset("user-one", "Dataset")

    with pytest.raises(ValueError, match="input"):
        store.add_example("user-one", dataset.id, " ", "target")
    with pytest.raises(ValueError, match="source"):
        store.add_example("user-one", dataset.id, "input", "target", source="x" * 501)


def test_dataset_owner_cannot_read_or_mutate_another_users_dataset(tmp_path):
    store = SQLiteTrainingStore(tmp_path / "training.sqlite3")
    dataset = _dataset(store)

    with pytest.raises(KeyError):
        store.add_example("user-two", dataset.id, "input", "target")


def test_training_requires_explicit_approval_and_registered_trainer(tmp_path):
    store = SQLiteTrainingStore(tmp_path / "training.sqlite3")
    dataset = _dataset(store)
    engine = TrainingEngine(store)

    with pytest.raises(PermissionError):
        engine.run("user-one", dataset.id, trainer_name="local_sft", approved=False)
    with pytest.raises(KeyError):
        engine.run("user-one", dataset.id, trainer_name="unregistered", approved=True)


def test_training_engine_runs_only_host_registered_trainer_and_records_metrics(tmp_path):
    store = SQLiteTrainingStore(tmp_path / "training.sqlite3")
    dataset = _dataset(store)
    engine = TrainingEngine(store)
    engine.register_trainer(
        "test_trainer",
        lambda examples, config: {"examples_seen": len(examples), "loss": 0.25},
    )

    run = engine.run(
        "user-one", dataset.id, trainer_name="test_trainer",
        config={"epochs": 2}, approved=True,
    )

    assert run.status is TrainingRunStatus.COMPLETED
    assert run.metrics == {"examples_seen": 2, "loss": 0.25}
    assert run.completed_at is not None


def test_training_failure_is_recorded_without_leaking_exception_message(tmp_path):
    store = SQLiteTrainingStore(tmp_path / "training.sqlite3")
    dataset = _dataset(store)
    engine = TrainingEngine(store)

    def failing_trainer(examples, config):
        raise RuntimeError("secret token must not be persisted")

    engine.register_trainer("failing", failing_trainer)
    run = engine.run("user-one", dataset.id, trainer_name="failing", approved=True)

    assert run.status is TrainingRunStatus.FAILED
    assert run.error_code == "trainer_failed"
    assert "secret token" not in repr(run)


def test_training_run_cannot_be_read_by_another_owner(tmp_path):
    store = SQLiteTrainingStore(tmp_path / "training.sqlite3")
    dataset = _dataset(store)
    engine = TrainingEngine(store)
    engine.register_trainer("test", lambda examples, config: {"loss": 0.1})
    run = engine.run("user-one", dataset.id, trainer_name="test", approved=True)

    with pytest.raises(KeyError):
        store.get_run("user-two", run.id)
