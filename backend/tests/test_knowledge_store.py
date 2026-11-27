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
