"""
HTTP-level tests: real requests through the FastAPI app against an in-memory fake Firestore.
No network, no Firebase credentials.

Run from backend/:  python -m pytest tests/test_api_flows.py -q
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import firebase_admin  # noqa: E402
import firebase_admin.credentials as _cr  # noqa: E402
import firebase_admin.firestore as _fs  # noqa: E402

# Importing the app initialises Firebase — replace the SDK entry points before that happens
_fs.client = lambda *a, **k: MagicMock()
firebase_admin.initialize_app = lambda *a, **k: None
_cr.Certificate = lambda *a, **k: object()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
import app.api.v1.workflows as wf_api  # noqa: E402
from app.core.auth_dependency import get_current_user  # noqa: E402
from app.db.analytics_db import analytics_db  # noqa: E402


# ---------------------------------------------------------------------------
# Minimal in-memory Firestore (collection / document / where ==,>=,<= / stream)
# ---------------------------------------------------------------------------

class Doc:
    def __init__(self, doc_id, data):
        self.id, self._data = doc_id, data

    exists = property(lambda self: self._data is not None)

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


def _resolve(data):
    """Like the real server, replace SERVER_TIMESTAMP markers with an actual timestamp."""
    now = datetime.now(timezone.utc)
    return {k: (now if v is _fs.SERVER_TIMESTAMP else v) for k, v in data.items()}


class DocRef:
    def __init__(self, store, doc_id):
        self.store, self.id = store, doc_id

    def set(self, data, merge=False):
        data = _resolve(data)
        self.store[self.id] = {**self.store.get(self.id, {}), **data} if merge else dict(data)

    def update(self, data):
        doc = self.store.setdefault(self.id, {})
        for key, value in _resolve(data).items():
            *parents, leaf = key.split(".")
            target = doc
            for p in parents:
                target = target.setdefault(p, {})
            target[leaf] = value

    def get(self):
        return Doc(self.id, self.store.get(self.id))

    def delete(self):
        self.store.pop(self.id, None)

    def collection(self, name):  # subcollections (users/{uid}/credentials) — always empty here
        return Collection({})


class Collection:
    def __init__(self, store, filters=()):
        self.store, self.filters = store, filters

    def document(self, doc_id=None):
        return DocRef(self.store, doc_id or uuid.uuid4().hex)

    OPS = {"==": lambda a, b: a == b, ">=": lambda a, b: a is not None and a >= b,
           "<=": lambda a, b: a is not None and a <= b}

    def where(self, field, op, value):
        assert op in self.OPS, f"fake Firestore does not support {op}"
        return Collection(self.store, self.filters + ((field, op, value),))

    def stream(self):
        return [Doc(i, d) for i, d in list(self.store.items())
                if all(self.OPS[op](d.get(f), v) for f, op, v in self.filters)]


class FakeDB:
    def __init__(self):
        self.data = {}

    def collection(self, name):
        return Collection(self.data.setdefault(name, {}))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORKFLOW = {
    "name": "Hello flow", "userId": "u-user", "nodes": [
        {"id": "t", "type": "ManualTrigger", "name": "Start", "config": {}},
        {"id": "v", "type": "SetVariable", "name": "Set", "config": {"variable_name": "greeting", "value": "hi"}},
    ],
    "edges": [{"source": "t", "target": "v"}],
}
WEBHOOK_WORKFLOW = {
    "name": "Hook flow", "userId": "u-user", "nodes": [
        {"id": "w", "type": "Webhook", "name": "Hook", "config": {"secret": "s3cret", "allowed_methods": "POST"}},
    ],
    "edges": [],
}
USERS = {
    "viewer": {"uid": "u-viewer", "email": "v@x.io", "role": "viewer"},
    "user": {"uid": "u-user", "email": "u@x.io", "role": "user"},
    "manager": {"uid": "u-mgr", "email": "m@x.io", "role": "manager"},
    "admin": {"uid": "u-admin", "email": "a@x.io", "role": "admin"},
}


@pytest.fixture
def env(monkeypatch):
    db = FakeDB()
    db.data["workflows"] = {"wf1": dict(WORKFLOW), "hook1": dict(WEBHOOK_WORKFLOW)}
    db.data["users"] = {u["uid"]: {"email": u["email"]} for u in USERS.values()}
    db.data["workflow_templates"] = {"tpl1": {"name": "Starter", "isActive": True, "isFeatured": False,
                                              "nodes": [], "usageCount": 3}}

    class FakeWorkflowService:
        async def get_workflow_by_id(self, workflow_id, user_id=None):
            wf = db.data["workflows"].get(workflow_id)
            return dict(wf) if wf else None

        async def increment_execution_count(self, workflow_id):
            db.data["workflows"][workflow_id]["executionCount"] = \
                db.data["workflows"][workflow_id].get("executionCount", 0) + 1

    fake_fb = MagicMock(db=db)
    monkeypatch.setattr(wf_api, "firebase_service", fake_fb)
    monkeypatch.setattr(wf_api, "workflow_service", FakeWorkflowService())
    monkeypatch.setattr(wf_api, "load_user_credentials_sync", lambda uid: {})
    monkeypatch.setattr(analytics_db, "db", db)
    import app.api.v1.admin as admin_api
    monkeypatch.setattr(admin_api, "firebase_service", fake_fb)
    monkeypatch.setattr(admin_api.audit_service, "log_event", _async_noop)

    class Env:
        client = TestClient(app, base_url="http://localhost", raise_server_exceptions=False)  # host must pass TrustedHostMiddleware
        database = db

        @staticmethod
        def as_(role):
            app.dependency_overrides[get_current_user] = lambda: dict(USERS[role])
            return Env.client

    yield Env
    app.dependency_overrides.clear()


async def _async_noop(*a, **k):
    return {"success": True}


# ---------------------------------------------------------------------------
# RBAC over HTTP
# ---------------------------------------------------------------------------

def test_viewer_cannot_execute_but_user_can(env):
    assert env.as_("viewer").post("/api/v1/workflows/wf1/execute", json={}).status_code == 403
    resp = env.as_("user").post("/api/v1/workflows/wf1/execute", json={})
    assert resp.status_code == 200 and resp.json()["status"] == "completed"


def test_viewer_cannot_use_ai_compare(env):
    body = {"prompt": "hi", "models": [{"provider": "OpenAI", "model": "gpt-4.1-mini"}]}
    assert env.as_("viewer").post("/api/v1/ai/compare", json=body).status_code == 403


def test_admin_panel_access_by_role(env):
    assert env.as_("user").get("/api/v1/admin/workflows").status_code == 403
    assert env.as_("manager").get("/api/v1/admin/workflows").status_code == 200   # read-only
    assert env.as_("manager").patch("/api/v1/admin/workflows/wf1", json={"disabled": True}).status_code == 403
    assert env.as_("admin").patch("/api/v1/admin/workflows/wf1", json={"disabled": True}).status_code == 200


def test_whoami_reports_role_and_admin_panel_access(env):
    assert env.as_("manager").get("/api/v1/admin/whoami").json()["canAccessAdmin"] is True
    assert env.as_("user").get("/api/v1/admin/whoami").json()["canAccessAdmin"] is False


# ---------------------------------------------------------------------------
# Execution is recorded, and analytics reads it back
# ---------------------------------------------------------------------------

def test_run_is_recorded_and_visible_in_executions_and_analytics(env):
    client = env.as_("user")
    run = client.post("/api/v1/workflows/wf1/execute", json={}).json()
    exec_id = run["summary"]["execution_id"]

    record = env.database.data["executions"][exec_id]
    assert record["status"] == "completed" and record["trigger"] == "manual"
    assert record["userId"] == "u-user" and record["stepsCompleted"] == 2
    assert [log["nodeId"] for log in record["nodeLogs"]] == ["t", "v"]

    listing = client.get("/api/v1/workflows/executions/all").json()
    assert listing["total"] == 1 and listing["executions"][0]["id"] == exec_id
    assert client.get(f"/api/v1/workflows/executions/{exec_id}").status_code == 200

    overview = client.get("/api/v1/analytics/workflows/overview").json()["overview"]
    assert overview["totalExecutions"] == 1 and overview["successRate"] == 100.0

    # Someone else's execution is invisible (404, not 403 — don't confirm it exists)
    assert env.as_("viewer").get(f"/api/v1/workflows/executions/{exec_id}").status_code == 404


def test_analytics_are_scoped_per_user_but_managers_see_everything(env):
    env.as_("user").post("/api/v1/workflows/wf1/execute", json={})
    assert env.as_("viewer").get("/api/v1/analytics/workflows/overview").json()["overview"]["totalExecutions"] == 0
    assert env.as_("manager").get("/api/v1/analytics/workflows/overview").json()["overview"]["totalExecutions"] == 1
    assert env.as_("user").get("/api/v1/analytics/system/health").status_code == 403


def test_disabled_workflow_is_blocked_on_every_trigger(env):
    env.as_("admin").patch("/api/v1/admin/workflows/wf1", json={"disabled": True, "reason": "abuse"})
    resp = env.as_("user").post("/api/v1/workflows/wf1/execute", json={})
    assert resp.status_code == 403 and "abuse" in resp.json()["message"]


def test_workspace_node_limit_is_enforced(env):
    env.database.data["users"]["u-user"]["workspace"] = {"maxWorkflowNodes": 1}
    resp = env.as_("user").post("/api/v1/workflows/wf1/execute", json={})
    assert resp.status_code == 400 and "limit" in resp.json()["message"]


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

def test_webhook_requires_the_secret(env):
    url = "/api/v1/workflows/hook1/webhook"
    assert env.client.post(url, json={"a": 1}).status_code == 401
    assert env.client.post(url, json={"a": 1}, headers={"X-Webhook-Secret": "wrong"}).status_code == 401
    ok = env.client.post(url, json={"a": 1}, headers={"X-Webhook-Secret": "s3cret"})
    assert ok.status_code == 200 and ok.json()["status"] == "completed"
    assert env.client.post(url + "?secret=s3cret", json={}).status_code == 200   # query-param form


def test_webhook_respects_allowed_methods_and_is_recorded(env):
    url = "/api/v1/workflows/hook1/webhook"
    assert env.client.get(url, headers={"X-Webhook-Secret": "s3cret"}).status_code == 405
    env.client.post(url, json={}, headers={"X-Webhook-Secret": "s3cret"})
    runs = list(env.database.data["executions"].values())
    assert len(runs) == 1 and runs[0]["trigger"] == "webhook"
    # the secret must not leak into the stored request input
    assert "x-webhook-secret" not in str(runs[0]["input"]).lower()


# ---------------------------------------------------------------------------
# Admin moderation writes real state
# ---------------------------------------------------------------------------

def test_admin_template_moderation(env):
    admin = env.as_("admin")
    assert admin.patch("/api/v1/admin/templates/tpl1", json={"isFeatured": True}).status_code == 200
    assert env.database.data["workflow_templates"]["tpl1"]["isFeatured"] is True
    assert admin.patch("/api/v1/admin/templates/missing", json={"isActive": False}).status_code == 404
    assert admin.patch("/api/v1/admin/templates/tpl1", json={}).status_code == 400
    assert admin.delete("/api/v1/admin/templates/tpl1").status_code == 200
    assert "tpl1" not in env.database.data["workflow_templates"]
