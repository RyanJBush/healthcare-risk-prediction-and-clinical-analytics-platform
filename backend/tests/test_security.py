import pytest
from fastapi import HTTPException

from app.models import User
from app.security import create_access_token, get_current_user, hash_password, require_roles, verify_password


class _FakeQuery:
    def __init__(self, user: User | None) -> None:
        self._user = user

    def filter(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self

    def first(self) -> User | None:
        return self._user


class _FakeDB:
    def __init__(self, user: User | None) -> None:
        self._user = user

    def query(self, _model):  # noqa: ANN001
        return _FakeQuery(self._user)


def test_hash_password_and_verify_password() -> None:
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_get_current_user_rejects_token_without_subject(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("app.security.jwt.decode", lambda *args, **kwargs: {"role": "clinician"})

    with pytest.raises(HTTPException) as exc:
        get_current_user(token="any", db=_FakeDB(User(username="u", password_hash="h", role="clinician")))

    assert exc.value.status_code == 401


def test_get_current_user_rejects_unknown_user(monkeypatch) -> None:  # noqa: ANN001
    token = create_access_token("missing-user", "clinician")

    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token, db=_FakeDB(None))

    assert exc.value.status_code == 401


def test_require_roles_rejects_non_matching_role() -> None:
    dependency = require_roles("admin")
    with pytest.raises(HTTPException) as exc:
        dependency(current_user=User(username="viewer", password_hash="hash", role="viewer"))
    assert exc.value.status_code == 403
