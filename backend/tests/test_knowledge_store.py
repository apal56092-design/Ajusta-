import pytest

from ajusta_core.knowledge_store import SQLiteKnowledgeStore


def test_full_text_search_returns_relevant_records_for_owner_only(tmp_path):
    store = SQLiteKnowledgeStore(tmp_path / "knowledge.sqlite3")
    first = store.create("user-one", "Solar research", "Photovoltaic energy converts sunlight.")
    store.create("user-one", "Cooking notes", "A recipe for vegetable soup.")
    store.create("user-two", "Solar project", "Solar panels and photovoltaic cells.")

    results = store.search_for_user("user-one", "photovoltaic solar")

    assert [item.id for item in results] == [first.id]
    assert results[0].title == "Solar research"


def test_full_text_search_rejects_empty_and_limits_results(tmp_path):
    store = SQLiteKnowledgeStore(tmp_path / "knowledge.sqlite3")
    store.create("user-one", "Alpha", "shared phrase alpha")
    store.create("user-one", "Beta", "shared phrase beta")

    with pytest.raises(ValueError, match="query"):
        store.search_for_user("user-one", " !!! ")

    assert len(store.search_for_user("user-one", "shared phrase", limit=1)) == 1


def test_full_text_index_tracks_deletes(tmp_path):
    store = SQLiteKnowledgeStore(tmp_path / "knowledge.sqlite3")
    item = store.create("user-one", "Temporary", "unique searchable phrase")
    assert len(store.search_for_user("user-one", "searchable")) == 1

    assert store.delete("user-one", item.id)
    assert store.search_for_user("user-one", "searchable") == ()


def test_knowledge_records_preserve_learning_provenance_and_confidence(tmp_path):
    store = SQLiteKnowledgeStore(tmp_path / "knowledge.sqlite3")

    item = store.create(
        "user-one",
        "Solar efficiency note",
        "The supplied report estimates panel efficiency at 22 percent.",
        source="https://example.org/solar-report",
        confidence=0.72,
    )

    assert item.source == "https://example.org/solar-report"
    assert item.confidence == 0.72
    assert item.user_id == "user-one"


@pytest.mark.parametrize("confidence", [-0.01, 1.01, True, "high"])
def test_knowledge_records_reject_invalid_confidence(tmp_path, confidence):
    store = SQLiteKnowledgeStore(tmp_path / "knowledge.sqlite3")

    with pytest.raises(ValueError, match="confidence"):
        store.create("user-one", "Note", "Content", confidence=confidence)


def test_knowledge_records_reject_oversized_provenance(tmp_path):
    store = SQLiteKnowledgeStore(tmp_path / "knowledge.sqlite3")

    with pytest.raises(ValueError, match="source"):
        store.create("user-one", "Note", "Content", source="s" * 501)


def test_existing_knowledge_database_is_migrated_with_provenance_columns(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    legacy = SQLiteKnowledgeStore(database)
    original = legacy.create("user-one", "Legacy", "Existing saved memory")

    reopened = SQLiteKnowledgeStore(database)
    migrated = reopened.list_for_user("user-one")[0]

    assert migrated.id == original.id
    assert migrated.source is None
    assert migrated.confidence is None
