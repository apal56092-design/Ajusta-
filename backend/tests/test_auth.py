import pytest

from ajusta_core.auth import AuthenticationError, SQLiteAuthStore


def test_register_and_authenticate_user(tmp_path):
    auth = SQLiteAuthStore(tmp_path / "auth.sqlite3")
    user = auth.register_user("Person@Example.com", "a-long-test-password")
    assert user.email == "person@example.com"
    authenticated = auth.authenticate("PERSON@example.com", "a-long-test-password")
    assert authenticated.user_id == user.user_id


def test_duplicate_email_is_rejected_case_insensitively(tmp_path):
    auth = SQLiteAuthStore(tmp_path / "auth.sqlite3")
    auth.register_user("person@example.com", "a-long-test-password")
    with pytest.raises(ValueError, match="already registered"):
        auth.register_user("PERSON@example.com", "another-long-password")


def test_wrong_password_is_rejected(tmp_path):
    auth = SQLiteAuthStore(tmp_path / "auth.sqlite3")
    auth.register_user("person@example.com", "a-long-test-password")
    with pytest.raises(AuthenticationError):
        auth.authenticate("person@example.com", "incorrect-password")


def test_session_is_opaque_resolvable_and_revocable(tmp_path):
    auth = SQLiteAuthStore(tmp_path / "auth.sqlite3")
    user = auth.register_user("person@example.com", "a-long-test-password")
    token = auth.create_session(user.user_id, ttl_seconds=600)
    assert len(token) >= 40
    assert auth.resolve_session(token).user_id == user.user_id
    assert auth.revoke_session(token) is True
    with pytest.raises(AuthenticationError):
        auth.resolve_session(token)


def test_expired_session_is_rejected(tmp_path, monkeypatch):
    import ajusta_core.auth as auth_module

    clock = [1_000]
    monkeypatch.setattr(auth_module.time, "time", lambda: clock[0])
    auth = SQLiteAuthStore(tmp_path / "auth.sqlite3")
    user = auth.register_user("person@example.com", "a-long-test-password")
    token = auth.create_session(user.user_id, ttl_seconds=1)
    clock[0] = 1_002
    with pytest.raises(AuthenticationError):
        auth.resolve_session(token)


def test_invalid_registration_inputs_are_rejected(tmp_path):
    auth = SQLiteAuthStore(tmp_path / "auth.sqlite3")
    with pytest.raises(ValueError):
        auth.register_user("not-an-email", "a-long-test-password")
    with pytest.raises(ValueError):
        auth.register_user("person@example.com", "short")
