from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import telegram


class _FakeResult:
    def __init__(self, users):
        self._users = list(users)

    def scalars(self):
        return self

    def first(self):
        if not self._users:
            return None
        return self._users[0]


class _FakeDB:
    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    async def execute(self, _query):
        self.calls += 1
        if not self._results:
            return _FakeResult([])
        return self._results.pop(0)


@pytest.mark.asyncio
async def test_resolve_acting_admin_uses_first_active_admin_when_multiple(monkeypatch):
    monkeypatch.setattr(telegram.settings, "TELEGRAM_ACTING_ADMIN_EMAIL", None)

    first_admin = SimpleNamespace(id="admin-1")
    second_admin = SimpleNamespace(id="admin-2")
    db = _FakeDB([_FakeResult([first_admin, second_admin])])

    resolved = await telegram._resolve_acting_admin(db)

    assert resolved is first_admin
    assert db.calls == 1


@pytest.mark.asyncio
async def test_resolve_acting_admin_falls_back_when_configured_email_not_found(monkeypatch):
    monkeypatch.setattr(telegram.settings, "TELEGRAM_ACTING_ADMIN_EMAIL", "missing@example.com")

    fallback_admin = SimpleNamespace(id="admin-fallback")
    db = _FakeDB(
        [
            _FakeResult([]),  # Preferred email lookup
            _FakeResult([fallback_admin]),  # Generic fallback lookup
        ]
    )

    resolved = await telegram._resolve_acting_admin(db)

    assert resolved is fallback_admin
    assert db.calls == 2


@pytest.mark.asyncio
async def test_resolve_acting_admin_raises_when_no_admin_available(monkeypatch):
    monkeypatch.setattr(telegram.settings, "TELEGRAM_ACTING_ADMIN_EMAIL", None)
    db = _FakeDB([_FakeResult([])])

    with pytest.raises(HTTPException) as exc:
        await telegram._resolve_acting_admin(db)

    assert exc.value.status_code == 500
    assert "No active admin/staff user available" in str(exc.value.detail)
