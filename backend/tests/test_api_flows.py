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
    def __init__(self, store, doc_id, db=None, path=""):
        self.store, self.id, self.db, self.path = store, doc_id, db, path

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

    def collection(self, name):  # sub-collection, e.g. users/{uid}/mcp_servers
        return self.db.collection(f"{self.path}/{self.id}/{name}")


class Collection:
    def __init__(self, store, filters=(), db=None, path=""):
        self.store, self.filters, self.db, self.path = store, filters, db, path

    def document(self, doc_id=None):
        return DocRef(self.store, doc_id or uuid.uuid4().hex, self.db, self.path)

    OPS = {"==": lambda a, b: a == b, ">=": lambda a, b: a is not None and a >= b,
           "<=": lambda a, b: a is not None and a <= b}

    def where(self, field, op, value):
        assert op in self.OPS, f"fake Firestore does not support {op}"
        return Collection(self.store, self.filters + ((field, op, value),), self.db, self.path)

    def stream(self):
        return [Doc(i, d) for i, d in list(self.store.items())
                if all(self.OPS[op](d.get(f), v) for f, op, v in self.filters)]


class FakeDB:
    def __init__(self):
        self.data = {}

    def collection(self, name):
        return Collection(self.data.setdefault(name, {}), (), self, name)


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
    import app.api.v1.mcp as mcp_api
    monkeypatch.setattr(admin_api, "firebase_service", fake_fb)
    monkeypatch.setattr(mcp_api, "firebase_service", fake_fb)
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


# ---------------------------------------------------------------------------
# Workflow variables
# ---------------------------------------------------------------------------

def test_workflow_variables_are_used_by_a_manual_run(env):
    env.database.data["workflows"]["vars1"] = {
        "name": "Vars flow", "userId": "u-user", "variables": {"customer": "Acme", "rows": 25},
        "nodes": [{"id": "t", "type": "ManualTrigger", "name": "Start", "config": {}},
                  {"id": "l", "type": "Logger", "name": "Log",
                   "config": {"level": "info", "message": "Hello {{$vars.customer}}, {{$vars.rows}} rows"}}],
        "edges": [{"source": "t", "target": "l"}],
    }
    run = env.as_("user").post("/api/v1/workflows/vars1/execute", json={}).json()
    record = env.database.data["executions"][run["summary"]["execution_id"]]
    assert record["status"] == "completed"
    assert record["nodeLogs"][1]["output"]["message"] == "Hello Acme, 25 rows"


def test_typed_workflow_variables_reach_the_steps_as_plain_values(env):
    env.database.data["workflows"]["vars2"] = {
        "name": "Typed vars", "userId": "u-user",
        "variables": {"customer": {"type": "string", "value": "Acme"}, "rows": {"type": "number", "value": 25},
                      "limits": {"type": "json", "value": '{"max": 3}'}},
        "nodes": [{"id": "t", "type": "ManualTrigger", "name": "Start", "config": {}},
                  {"id": "l", "type": "Logger", "name": "Log",
                   "config": {"level": "info", "message": "{{$vars.customer}} {{$vars.rows}} {{$vars.limits.max}}"}}],
        "edges": [{"source": "t", "target": "l"}],
    }
    run = env.as_("user").post("/api/v1/workflows/vars2/execute", json={}).json()
    record = env.database.data["executions"][run["summary"]["execution_id"]]
    assert record["status"] == "completed"
    assert record["nodeLogs"][1]["output"]["message"] == "Acme 25 3"


# ---------------------------------------------------------------------------
# Module 09 - what a failed run leaves behind
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=False)
def refused(monkeypatch):
    """Every outgoing HTTP call is refused, so a 'broken' workflow fails the same way on every machine."""
    import httpx

    async def refuse(self, *a, **k):
        raise httpx.ConnectError("All connection attempts failed")

    monkeypatch.setattr(httpx.AsyncClient, "request", refuse)


def _broken_workflow(env, wid, settings=None):
    cfg = {"url": "http://127.0.0.1:1/unreachable", "timeout": 2}
    if settings:
        cfg["_settings"] = settings
    env.database.data["workflows"][wid] = {
        "name": "Broken flow", "userId": "u-user",
        "nodes": [{"id": "t", "type": "ManualTrigger", "name": "Start", "config": {}},
                  {"id": "h", "type": "HttpRequest", "name": "Fetch prices", "config": cfg}],
        "edges": [{"source": "t", "target": "h"}],
    }


@pytest.fixture
def notices(monkeypatch):
    """Captures notification-centre items instead of writing them, and starts each test with no cool-down."""
    from app.services import notification_service as ns
    sent = []

    async def capture(request, *a, **k):
        sent.append(request)
        return "n1"

    monkeypatch.setattr(ns.notification_service, "create_notification", capture)
    wf_api._last_failure_notice.clear()
    return sent


def test_a_failed_run_stores_a_plain_language_explanation(env, notices, refused):
    _broken_workflow(env, "bad1")
    run = env.as_("user").post("/api/v1/workflows/bad1/execute", json={}).json()
    record = env.database.data["executions"][run["summary"]["execution_id"]]
    assert record["status"] == "failed"
    assert record["errorInfo"]["category"] == "network" and record["errorInfo"]["retryable"] is True
    assert record["errorInfo"]["title"] and record["errorInfo"]["suggestion"]
    failed = [log for log in record["nodeLogs"] if log["status"] == "failed"][0]
    assert failed["errorInfo"] == record["errorInfo"] and record["failedSteps"] == 1


def test_a_failed_run_raises_an_alert_with_advice_and_one_notification(env, notices, refused):
    _broken_workflow(env, "bad2")
    client = env.as_("user")
    first = client.post("/api/v1/workflows/bad2/execute", json={}).json()["summary"]["execution_id"]
    client.post("/api/v1/workflows/bad2/execute", json={})
    alerts = [a for a in env.database.data.get("analytics_alerts", {}).values() if a.get("workflowId") == "bad2"]
    assert len(alerts) == 2 and alerts[0]["hint"] and alerts[0]["errorCategory"] == "network"     # every failure is an alert
    assert len(notices) == 1                                                                       # but the inbox is told once per cool-down
    note = notices[0]
    assert note.user_id == "u-user" and note.notification_type.value == "workflow_failed" and note.priority.value == "high"
    assert "Broken flow" in note.title and note.action_url == f"/workflows/execution/{first}"
    assert note.metadata["category"] == "network" and note.metadata["execution_id"] == first


def test_a_step_with_a_fallback_keeps_the_run_green_but_on_record(env, notices, refused):
    _broken_workflow(env, "bad3", {"on_error": "fallback", "fallback_value": "no data"})
    run = env.as_("user").post("/api/v1/workflows/bad3/execute", json={}).json()
    record = env.database.data["executions"][run["summary"]["execution_id"]]
    assert record["status"] == "completed" and record["errorInfo"] is None
    assert record["failedSteps"] == 1 and record["nodeLogs"][1]["fallbackUsed"] is True
    assert notices == [] and not [a for a in env.database.data.get("analytics_alerts", {}).values() if a.get("workflowId") == "bad3"]


def test_a_notification_failure_never_breaks_the_run(env, monkeypatch, refused):
    from app.services import notification_service as ns

    async def boom(*a, **k):
        raise RuntimeError("notification store down")

    monkeypatch.setattr(ns.notification_service, "create_notification", boom)
    wf_api._last_failure_notice.clear()
    _broken_workflow(env, "bad4")
    resp = env.as_("user").post("/api/v1/workflows/bad4/execute", json={})
    assert resp.status_code == 200
    assert env.database.data["executions"][resp.json()["summary"]["execution_id"]]["status"] == "failed"
