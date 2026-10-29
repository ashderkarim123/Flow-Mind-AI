"""
Regressions for bugs found by running all 12 modules end to end against the Firebase emulators.

  * routes that a "/{id}" route declared earlier used to shadow (/notifications/stats, /integrations/connections, ...)
  * /auth/signup re-"registering" an existing account and rewriting its profile
  * one shared rate-limit counter for every endpoint
  * publishing a template saved it but answered 500 (placeholder timestamps in the response)
  * the Loop node treating a typed JSON array as a single item
  * the auth router's admin check only accepting one hard-coded e-mail
  * stopping a running schedule deadlocked the scheduler (Stop hung, later starts blocked)

Run from backend/:  python -m pytest tests/test_regressions.py -q
"""

import asyncio
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_api_flows import env  # noqa: E402,F401  (importing it also stubs the Firebase SDK before the app loads)

import firebase_admin.firestore as _fs  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import _static_paths_first, app  # noqa: E402


# ---------------------------------------------------------------------------
# Route order
# ---------------------------------------------------------------------------

def _leaf_routers(router):
    """Every APIRouter reachable from the app, FastAPI-version independent."""
    seen, stack = [], [router]
    while stack:
        r = stack.pop()
        seen.append(r)
        stack.extend(c for c in (getattr(x, "original_router", None) for x in r.routes) if c is not None)
    return seen


def test_static_paths_are_declared_before_dynamic_siblings():
    """No route may be unreachable because an earlier '/{id}' route swallows it."""
    shadowed = []
    for router in _leaf_routers(app.router):
        api = [r for r in router.routes if isinstance(r, APIRoute)]
        for i, dyn in enumerate(api):
            if "{" not in dyn.path:
                continue
            pattern = re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", dyn.path) + "$")
            for stat in api[i + 1:]:
                if "{" not in stat.path and pattern.match(stat.path) and set(stat.methods) & set(dyn.methods):
                    shadowed.append(f"{sorted(stat.methods)} {stat.path} hidden by {dyn.path}")
    assert not shadowed, "\n".join(shadowed)


def test_helper_puts_static_routes_first():
    toy = FastAPI()
    from fastapi import APIRouter
    router = APIRouter(prefix="/things")

    @router.get("/{thing_id}")
    def one(thing_id: str):
        return {"route": "one"}

    @router.get("/stats")
    def stats():
        return {"route": "stats"}

    toy.include_router(router)
    _static_paths_first(toy.router)
    assert TestClient(toy).get("/things/stats").json() == {"route": "stats"}
    assert TestClient(toy).get("/things/42").json() == {"route": "one"}


# ---------------------------------------------------------------------------
# Signup must not rewrite an existing account
# ---------------------------------------------------------------------------

class FakeProfileDB:
    def __init__(self, existing_uids):
        self.written = []
        self.existing = set(existing_uids)

    def collection(self, name):
        db = self

        class Col:
            def document(self, uid):
                class Ref:
                    def get(self):
                        return MagicMock(exists=uid in db.existing)

                    def set(self, data, merge=False):
                        db.written.append(uid)

                return Ref()

        return Col()


def _signup(monkeypatch, *, auth_user_exists, profile_exists):
    from firebase_admin import auth
    from app.services import firebase_service as fs_mod

    svc = fs_mod.FirebaseService.__new__(fs_mod.FirebaseService)
    svc.db = FakeProfileDB({"u1"} if profile_exists else set())
    user = MagicMock(uid="u1", email="a@b.io", display_name="A", email_verified=False)

    def create_user(**kwargs):
        if auth_user_exists:
            raise auth.EmailAlreadyExistsError("exists", None, None)
        return user

    monkeypatch.setattr(auth, "create_user", create_user)
    monkeypatch.setattr(auth, "get_user_by_email", lambda email: user)
    monkeypatch.setattr(fs_mod.settings, "DEBUG", True)
    monkeypatch.setattr(fs_mod.settings, "ENVIRONMENT", "development")
    return svc, asyncio.run(svc.create_user("a@b.io", "pw123456", "A"))


def test_signup_for_an_existing_account_with_a_profile_is_refused(monkeypatch):
    svc, result = _signup(monkeypatch, auth_user_exists=True, profile_exists=True)
    assert result["success"] is False and "already exists" in result["error"]
    assert svc.db.written == []                       # the victim's profile (plan, usage, 2FA flag) is untouched


def test_signup_still_creates_the_profile_for_an_account_the_web_app_just_made(monkeypatch):
    svc, result = _signup(monkeypatch, auth_user_exists=True, profile_exists=False)
    assert result["success"] is True and svc.db.written == ["u1"]


def test_signup_for_a_new_account_works(monkeypatch):
    svc, result = _signup(monkeypatch, auth_user_exists=False, profile_exists=False)
    assert result["success"] is True and svc.db.written == ["u1"]


# ---------------------------------------------------------------------------
# Rate limit: one counter per endpoint
# ---------------------------------------------------------------------------

def _request():
    return Request({"type": "http", "method": "GET", "path": "/", "headers": [], "client": ("1.2.3.4", 1), "query_string": b""})


def test_rate_limits_are_counted_per_endpoint():
    from fastapi import HTTPException
    from app.core import security

    security.rate_limit_store.clear()

    @security.rate_limit(requests_per_minute=2)
    async def strict(request: Request):
        return "strict"

    @security.rate_limit(requests_per_minute=50)
    async def busy(request: Request):
        return "busy"

    async def scenario():
        req = _request()
        for _ in range(10):
            assert await busy(req) == "busy"          # ten calls elsewhere...
        assert await strict(req) == "strict"          # ...must not use up the strict endpoint's budget
        assert await strict(req) == "strict"
        with pytest.raises(HTTPException) as err:
            await strict(req)
        assert err.value.status_code == 429

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Template create returns the stored document
# ---------------------------------------------------------------------------

def test_create_template_returns_real_timestamps_not_the_server_placeholder():
    from app.db.template_db import TemplateDB

    stored = {}

    class Ref:
        id = "t1"

        def set(self, data):
            stored.update({k: (datetime.now(timezone.utc) if v is _fs.SERVER_TIMESTAMP else v) for k, v in data.items()})

        def get(self):
            return MagicMock(to_dict=lambda: dict(stored))

    class Col:
        def document(self):
            return Ref()

    db = TemplateDB()
    db.db = MagicMock(collection=lambda name: Col())
    result = asyncio.run(db.create_template({"name": "x"}))
    assert result["success"] and isinstance(result["data"]["createdAt"], datetime) and isinstance(result["data"]["updatedAt"], datetime)


# ---------------------------------------------------------------------------
# Loop node input
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("typed, expected", [
    ('["a", "b", "c"]', ["a", "b", "c"]),          # what the editor's placeholder suggests
    ("red\ngreen\n", ["red", "green"]),            # one per line
    ("just one", ["just one"]),
    ([1, 2], [1, 2]),
])
def test_loop_turns_typed_text_into_items(typed, expected):
    from nodes.logic.loop import Loop

    out = asyncio.run(Loop().execute({"items": typed}, {}, None))
    assert out["items"] == expected and out["total"] == len(expected) and out["current_item"] == expected[0]


# ---------------------------------------------------------------------------
# Admin guard of the auth router
# ---------------------------------------------------------------------------

def test_auth_router_admin_routes_use_the_shared_admin_rule(env):
    from app.api.v1 import auth as auth_api
    from app.core.auth_dependency import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"uid": "u1", "email": "boss@corp.io", "role": "admin"}
    try:
        assert asyncio.run(auth_api._require_admin(current_user={"uid": "u1", "email": "boss@corp.io", "role": "admin"}))["uid"] == "u1"
        with pytest.raises(Exception) as err:
            asyncio.run(auth_api._require_admin(current_user={"uid": "u2", "email": "user@corp.io", "role": "user"}))
        assert getattr(err.value, "status_code", None) == 403
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Scheduler: stopping a running job used to deadlock
# ---------------------------------------------------------------------------

def test_stopping_a_running_schedule_does_not_deadlock():
    from services.scheduler import SchedulerStatus, WorkflowScheduler

    async def executor(*args, **kwargs):
        return {"status": "completed"}

    class WatchedLock(asyncio.Lock):
        """Remembers who had to queue for the lock."""

        def __init__(self):
            super().__init__()
            self.queued = []

        async def acquire(self):
            if self.locked():
                self.queued.append(asyncio.current_task().get_name())
            return await super().acquire()

    async def scenario():
        scheduler = WorkflowScheduler()
        scheduler._lock = WatchedLock()
        job_id = scheduler.register_job("wf1", {"id": "wf1", "name": "x", "nodes": [], "connections": []},
                                        "* * * * *", executor_func=executor)
        await scheduler.start_scheduler(job_id)
        await asyncio.sleep(0.1)                                          # let the loop reach its wait
        await asyncio.wait_for(scheduler.stop_scheduler(job_id), timeout=3)
        assert scheduler.jobs[job_id].status == SchedulerStatus.STOPPED
        # The cancelled loop's cleanup takes the scheduler lock. If stop_scheduler still holds it while it
        # waits for that cleanup, the two wait for each other - the live server hung on exactly this.
        assert scheduler._lock.queued == []
        await asyncio.wait_for(scheduler.start_scheduler(job_id), timeout=3)   # and the scheduler stays usable
        await asyncio.wait_for(scheduler.stop_scheduler(job_id), timeout=3)

    asyncio.run(scenario())
