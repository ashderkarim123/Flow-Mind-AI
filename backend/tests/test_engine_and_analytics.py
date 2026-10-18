"""
Offline tests for the execution engine and analytics maths — no Firebase, no network.

Run from backend/:  python -m pytest tests/test_engine_and_analytics.py -q
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# analytics_db creates a Firestore client at import time — stub it out
import firebase_admin.firestore as _fs  # noqa: E402
_fs.client = lambda *a, **k: None

# firebase_service initialises the Admin SDK on import — replace it with an empty stub
import types  # noqa: E402
_stub = types.ModuleType("app.services.firebase_service")
_stub.firebase_service = None
sys.modules["app.services.firebase_service"] = _stub

from executor.context import ExecutionContext  # noqa: E402
from executor.engine import WorkflowConnection, WorkflowDefinition, WorkflowEngine, WorkflowNode  # noqa: E402
from nodes.base import BaseNode, NodeDefinition, NodeExecutionError  # noqa: E402
from nodes.registry import NodeRegistry  # noqa: E402
from app.db.analytics_db import bottlenecks, percentile, summarize, timeline, to_ms  # noqa: E402


# ---------------------------------------------------------------------------
# Tiny test nodes
# ---------------------------------------------------------------------------

def _definition(type_: str, trigger: bool = False) -> NodeDefinition:
    return NodeDefinition(type=type_, display_name=type_, description="", category="Test", icon="",
                          color="#000", is_trigger=trigger, parameters=[], outputs=[])


class Trigger(BaseNode):
    definition = _definition("T", trigger=True)

    async def execute(self, config, input_data, context):
        return {"started": True}


class Step(BaseNode):
    """Records the order nodes ran in and what they saw from upstream."""
    definition = _definition("Step")

    async def execute(self, config, input_data, context):
        context.variables.setdefault("order", []).append(config["name"])
        return {"name": config["name"], "seen": sorted(context.node_outputs)}


class Branch(BaseNode):
    definition = _definition("Branch")

    async def execute(self, config, input_data, context):
        return {"branch": config["go"]}


class Boom(BaseNode):
    definition = _definition("Boom")

    async def execute(self, config, input_data, context):
        raise NodeExecutionError("kaboom", "Boom")


def _engine() -> WorkflowEngine:
    registry = NodeRegistry()
    for cls in (Trigger, Step, Branch, Boom):
        registry.register(cls)
    return WorkflowEngine(registry)


def _run(nodes, edges):
    wf = WorkflowDefinition(
        id="wf", name="test",
        nodes=[WorkflowNode(id=i, type=t, config=c) for i, t, c in nodes],
        connections=[WorkflowConnection.from_dict(e) for e in edges],
    )
    ctx = ExecutionContext(execution_id="e1", workflow_id="wf", user_id="u1")
    result = asyncio.run(_engine().execute(wf, {}, ctx))
    return result, ctx


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def test_merge_node_waits_for_every_branch():
    # t → a → c ; t → b1 → b2 → c   (c must run after BOTH a and b2)
    result, ctx = _run(
        [("c", "Step", {"name": "c"}), ("t", "T", {}), ("a", "Step", {"name": "a"}),
         ("b1", "Step", {"name": "b1"}), ("b2", "Step", {"name": "b2"})],
        [{"from": "t", "to": "a"}, {"from": "t", "to": "b1"}, {"from": "b1", "to": "b2"},
         {"from": "a", "to": "c"}, {"from": "b2", "to": "c"}],
    )
    assert result.status == "completed"
    assert ctx.variables["order"] == ["a", "b1", "b2", "c"]
    assert {"a", "b2"} <= set(ctx.node_outputs["c"]["seen"])


def test_trigger_is_start_node_even_when_listed_later():
    result, ctx = _run(
        [("x", "Step", {"name": "orphan"}), ("t", "T", {}), ("a", "Step", {"name": "a"})],
        [{"from": "t", "to": "a"}],
    )
    assert result.logs[0].node_id == "t"
    assert ctx.variables["order"] == ["a"]


def test_dangling_connection_is_ignored():
    result, _ = _run([("t", "T", {}), ("a", "Step", {"name": "a"})],
                     [{"from": "t", "to": "a"}, {"from": "a", "to": "deleted-node"}])
    assert result.status == "completed"


def test_if_branch_routes_only_matching_side():
    result, ctx = _run(
        [("t", "T", {}), ("if", "Branch", {"go": "false"}),
         ("yes", "Step", {"name": "yes"}), ("no", "Step", {"name": "no"})],
        [{"from": "t", "to": "if"}, {"from": "if", "to": "yes", "condition": "true"},
         {"from": "if", "to": "no", "condition": "false"}],
    )
    assert ctx.variables["order"] == ["no"]


def test_failure_stops_run_and_reports_error():
    result, ctx = _run(
        [("t", "T", {}), ("x", "Boom", {}), ("after", "Step", {"name": "after"})],
        [{"from": "t", "to": "x"}, {"from": "x", "to": "after"}],
    )
    assert result.status == "failed" and result.error == "kaboom"
    assert "order" not in ctx.variables


def test_cycle_does_not_hang():
    result, _ = _run([("t", "T", {}), ("a", "Step", {"name": "a"}), ("b", "Step", {"name": "b"})],
                     [{"from": "t", "to": "a"}, {"from": "a", "to": "b"}, {"from": "b", "to": "a"}])
    assert result.status == "completed"


class Flaky(BaseNode):
    """Fails on the first call, succeeds afterwards (simulates a transient API error)."""
    definition = _definition("Flaky")
    calls = 0

    async def execute(self, config, input_data, context):
        Flaky.calls += 1
        if Flaky.calls == 1:
            raise NodeExecutionError("rate limited", "Flaky")
        return {"ok": True}


def _run_flaky(retries):
    import executor.engine as engine_mod
    engine_mod.RETRY_BACKOFF_SECONDS = 0
    Flaky.calls = 0
    registry = NodeRegistry()
    for cls in (Trigger, Flaky):
        registry.register(cls)
    wf = WorkflowDefinition(nodes=[WorkflowNode(id="t", type="T"), WorkflowNode(id="f", type="Flaky")],
                            connections=[WorkflowConnection.from_dict({"from": "t", "to": "f"})])
    ctx = ExecutionContext(execution_id="e", workflow_id="w", user_id="u", retry_attempts=retries)
    return asyncio.run(WorkflowEngine(registry).execute(wf, {}, ctx))


def test_retry_recovers_from_transient_failure():
    result = _run_flaky(retries=2)
    assert result.status == "completed"
    assert result.logs[-1].attempts == 2


def test_no_retry_by_default():
    result = _run_flaky(retries=0)
    assert result.status == "failed" and result.logs[-1].attempts == 1


def test_rbac_permission_matrix(monkeypatch):
    from app.core.auth_dependency import has_permission, role_of
    monkeypatch.setenv("ADMIN_EMAILS", "boss@flowmind.ai")
    viewer, user, manager = {"role": "viewer"}, {"role": "user"}, {"role": "manager"}
    admin = {"role": "admin"}

    assert has_permission(viewer, "workflow:read") and not has_permission(viewer, "workflow:write")
    assert not has_permission(viewer, "workflow:execute") and not has_permission(viewer, "ai:use")
    assert has_permission(user, "workflow:write") and has_permission(user, "workflow:execute")
    assert not has_permission(user, "analytics:platform") and not has_permission(user, "admin:read")
    assert has_permission(manager, "analytics:platform") and has_permission(manager, "admin:read")
    assert not has_permission(manager, "admin:write")  # moderation stays admin-only
    assert has_permission(admin, "admin:write")
    assert role_of({"role": "something-else"}) == "user"           # unknown role falls back safely
    assert role_of({"email": "Boss@FlowMind.ai"}) == "admin"        # ADMIN_EMAILS, case-insensitive


def test_credential_env_fallback(monkeypatch):
    ctx = ExecutionContext(execution_id="e", workflow_id="w", user_id="u")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    assert ctx.get_credential("openai_api_key", "api_key") == "sk-env"
    ctx.credentials = {"openai_api_key": {"api_key": "sk-user"}}
    assert ctx.get_credential("openai_api_key", "api_key") == "sk-user"


# ---------------------------------------------------------------------------
# Analytics maths
# ---------------------------------------------------------------------------

NOW = datetime(2026, 10, 14, 12, 0)


def _exec(status, minutes_ago, duration, tokens=0, logs=None, wf="w1"):
    return {"status": status, "startTime": to_ms(NOW - timedelta(minutes=minutes_ago)),
            "duration": duration, "metadata": {"tokensUsed": tokens}, "nodeLogs": logs or [],
            "workflowId": wf, "workflowName": wf}


def test_summarize_counts_rates_and_tokens():
    rows = [_exec("completed", 5, 100, 10), _exec("completed", 6, 300, 5), _exec("failed", 7, 200)]
    s = summarize(rows)
    assert (s["total"], s["successful"], s["failed"]) == (3, 2, 1)
    assert round(s["successRate"], 1) == 66.7
    assert s["avgDuration"] == 200 and s["tokens"] == 15


def test_summarize_ignores_stale_running_records():
    s = summarize([_exec("running", 600, 0)])  # 10h old "running" = crashed mid-run
    assert s["running"] == 0 and s["total"] == 0


def test_timeline_fills_empty_buckets():
    rows = [_exec("completed", 0, 1), _exec("completed", 0, 1), _exec("completed", 120, 1)]
    points = timeline(rows, NOW - timedelta(hours=3), NOW, "hour")
    assert [p["count"] for p in points] == [0, 1, 0, 2]


def test_percentile():
    assert percentile([], 95) == 0.0
    assert percentile(list(range(1, 101)), 50) == 51.0


def test_bottlenecks_flags_failing_and_slow_steps():
    slow = {"nodeId": "ai", "nodeType": "OpenAI", "nodeName": "Summarise", "status": "success", "executionTimeMs": 900}
    fast = {"nodeId": "t", "nodeType": "ManualTrigger", "status": "success", "executionTimeMs": 100}
    broken = {"nodeId": "h", "nodeType": "HTTPRequest", "status": "failed", "executionTimeMs": 50}
    result = bottlenecks([_exec("completed", 1, 1000, logs=[fast, slow]),
                          _exec("failed", 2, 50, logs=[broken], wf="w2")])
    assert result[0]["stepName"] == "HTTPRequest" and result[0]["failureRate"] == 100
    ai = next(b for b in result if b["stepName"] == "Summarise")
    assert ai["percentageOfTotalTime"] == 90 and "model" in ai["recommendedAction"]
