"""
Module 09 - error handling: classification of failures, retry policy, per-step fallbacks and time limits,
failure notifications. No network, no database.

Run from backend/:  python -m pytest tests/test_error_handling.py -q
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from executor.errors import RETRYABLE_CATEGORIES, UNKNOWN, classify_error  # noqa: E402


# Messages the platform's own nodes and the services behind them really produce.
@pytest.mark.parametrize("message,category,retryable", [
    ("OpenAI API key is required. Set it in the node config or in Credentials.", "config", False),
    ("PostgreSQL connection details are required: a connection string, or host, database and username.", "config", False),
    ("json_string is required", "config", False),
    ("Webhook URL must start with https://hooks.slack.com/", "config", False),
    ("The openai API rejected the server's API key.", "auth", False),
    ("Slack API error: invalid_auth", "auth", False),
    ("Failed to send email: (535, b'5.7.8 Username and Password not accepted')", "auth", False),
    ("The AI model returned an error (401): Incorrect API key provided", "auth", False),
    ("The openai API is rate-limiting requests — try again in a moment.", "rate_limit", True),
    ("rate limited", "rate_limit", True),
    ("HTTP request failed: 429 Too Many Requests", "rate_limit", True),
    ("Request to https://x.example timed out after 30s", "timeout", True),
    ("The AI model did not answer within 90s. A smaller model may be faster.", "timeout", True),
    ("Can't reach the AI model server at http://localhost:11434/v1. Start Ollama with `ollama serve`.", "network", True),
    ("Failed to send email: [Errno 111] Connect call failed ('127.0.0.1', 2525)", "network", True),
    ("HTTP request failed: [Errno -2] Name or service not known", "network", True),
    ("Slack API error: channel_not_found", "not_found", False),
    ("The local model 'qwen2.5:7b' is not installed. Install it with: ollama pull qwen2.5:7b", "not_found", False),
    ("The AI model returned an error (503): upstream overloaded", "server", True),
    ("Slack webhook error (400): invalid_payload", "bad_request", False),
    ("Invalid JSON: Expecting value: line 1 column 1 (char 0)", "data", False),
    ("kaboom", "unknown", False),
    ("", "unknown", False),
    (None, "unknown", False),
])
def test_real_error_messages_are_classified(message, category, retryable):
    info = classify_error(message)
    assert (info.category, info.retryable) == (category, retryable), message
    assert info.title and info.explanation and info.suggestion


def test_a_port_or_a_count_is_not_mistaken_for_a_status_code():
    assert classify_error("Failed to connect to PostgreSQL on port 5432 for user 500").category != "server"
    assert classify_error("processed 404 rows then stopped").category == "unknown"


def test_ai_steps_get_provider_specific_advice():
    generic = classify_error("The openai API rejected the server's API key.")
    ai = classify_error("The openai API rejected the server's API key.", "OpenAI")
    assert generic.category == ai.category == "auth" and "AI provider" in ai.suggestion and "AI provider" not in generic.suggestion


def test_only_transient_categories_are_retryable():
    assert RETRYABLE_CATEGORIES == {"rate_limit", "timeout", "network", "server"}
    assert UNKNOWN.retryable is False and UNKNOWN.category == "unknown"


def test_to_dict_is_json_friendly():
    import json
    d = classify_error("rate limited").to_dict()
    assert set(d) == {"category", "retryable", "title", "explanation", "suggestion"}
    json.dumps(d)


# ---------------------------------------------------------------------------
# Engine behaviour
# ---------------------------------------------------------------------------

from executor.context import ExecutionContext  # noqa: E402
from executor.engine import WorkflowConnection, WorkflowDefinition, WorkflowEngine, WorkflowNode  # noqa: E402
from nodes.base import BaseNode, NodeDefinition, NodeExecutionError  # noqa: E402
from nodes.registry import NodeRegistry  # noqa: E402


def _def(type_, trigger=False):
    return NodeDefinition(type=type_, display_name=type_, description="", category="Test", icon="", color="#000",
                          is_trigger=trigger, parameters=[], outputs=[])


class Start(BaseNode):
    definition = _def("Start", trigger=True)

    async def execute(self, config, input_data, context):
        return {"items": [1, 2, 3]}


class Failing(BaseNode):
    """Fails with whatever message the test gives it, counting its calls."""
    definition = _def("Failing")
    calls = 0

    async def execute(self, config, input_data, context):
        Failing.calls += 1
        raise NodeExecutionError(config.get("message", "kaboom"), "Failing")


class Slow(BaseNode):
    definition = _def("Slow")

    async def execute(self, config, input_data, context):
        await asyncio.sleep(config.get("seconds", 5))
        return {"done": True}


class Seen(BaseNode):
    """Records what it was configured with, once per call."""
    definition = _def("Seen")
    got = []

    async def execute(self, config, input_data, context):
        Seen.got.append(dict(config))
        return {"ok": True}


class LoopNode(BaseNode):
    definition = _def("Loop")

    async def execute(self, config, input_data, context):
        return {"items": [1, 2, 3], "total": 3}


def _run(nodes, edges, retries=0):
    import executor.engine as engine_mod
    engine_mod.RETRY_BACKOFF_SECONDS = 0
    Failing.calls = 0
    Seen.got = []
    registry = NodeRegistry()
    for cls in (Start, Failing, Slow, Seen, LoopNode):
        registry.register(cls)
    wf = WorkflowDefinition(nodes=[WorkflowNode(id=i, type=t, config=c) for i, t, c in nodes],
                            connections=[WorkflowConnection.from_dict(e) for e in edges])
    ctx = ExecutionContext(execution_id="e", workflow_id="w", user_id="u", retry_attempts=retries)
    return asyncio.run(WorkflowEngine(registry).execute(wf, {}, ctx)), ctx


def _chain(failing_config, after=True):
    nodes = [("t", "Start", {}), ("f", "Failing", failing_config)]
    edges = [{"from": "t", "to": "f"}]
    if after:
        nodes.append(("a", "Seen", {"v": "{{$node.f.result}}"}))
        edges.append({"from": "f", "to": "a"})
    return nodes, edges


def test_every_failed_step_carries_a_plain_language_explanation():
    result, _ = _run(*_chain({"message": "Slack API error: invalid_auth"}, after=False))
    log = result.logs[-1]
    assert result.status == "failed" and log.error_info["category"] == "auth"
    assert log.error_info["title"] and log.error_info["suggestion"] and log.error_info["retryable"] is False


def test_the_workspace_retry_only_retries_errors_that_can_be_temporary():
    _run(*_chain({"message": "HTTP request failed: 429 Too Many Requests"}, after=False), retries=2)
    assert Failing.calls == 3                                  # rate limited: tried again
    _run(*_chain({"message": "OpenAI API key is required"}, after=False), retries=2)
    assert Failing.calls == 1                                  # a missing key will not fix itself: not retried


def test_a_node_that_asks_for_retries_gets_them_for_any_error():
    result, _ = _run(*_chain({"message": "OpenAI API key is required", "_settings": {"retry_on_fail": True, "max_tries": 3, "wait_ms": 0}}, after=False))
    assert Failing.calls == 3 and result.logs[-1].attempts == 3


def test_attempts_report_what_really_happened_when_retrying_stops_early():
    result, _ = _run(*_chain({"message": "json_string is required"}, after=False), retries=4)
    assert result.logs[-1].attempts == 1


def test_fallback_value_is_handed_on_and_the_run_completes():
    result, ctx = _run(*_chain({"message": "rate limited", "_settings": {"on_error": "fallback", "fallback_value": '{"price": 0}'}}))
    assert result.status == "completed"
    out = ctx.node_outputs["f"]
    assert out["fallback"] is True and out["failed"] is True and out["result"] == {"price": 0} and out["error_category"] == "rate_limit"
    assert Seen.got == [{"v": {"price": 0}}]                                           # the next step read {{$node.f.result}}
    failed = [log for log in result.logs if log.node_id == "f"][0]
    assert failed.status.value == "failed" and failed.fallback_used is True             # still on record as a failure


@pytest.mark.parametrize("text,expected", [("plain text", "plain text"), ("42", 42), ("true", True), ('["a", 1]', ["a", 1]), ("", ""), ("{broken", "{broken")])
def test_fallback_values_keep_their_type(text, expected):
    _, ctx = _run(*_chain({"_settings": {"on_error": "fallback", "fallback_value": text}}))
    assert ctx.node_outputs["f"]["result"] == expected


def test_a_step_time_limit_stops_a_slow_step_with_a_clear_message():
    nodes = [("t", "Start", {}), ("s", "Slow", {"seconds": 5, "_settings": {"timeout_s": 1}})]
    result, _ = _run(nodes, [{"from": "t", "to": "s"}])
    assert result.status == "failed" and "timed out after 1s" in result.error
    assert result.logs[-1].error_info["category"] == "timeout" and result.logs[-1].duration_ms < 3000


def test_a_step_inside_a_loop_can_carry_on_too():
    nodes = [("t", "Start", {}), ("l", "Loop", {}), ("f", "Failing", {"message": "kaboom", "_settings": {"on_error": "continue"}}),
             ("a", "Seen", {"n": "{{$node.l.index}}"})]
    edges = [{"from": "t", "to": "l"}, {"from": "l", "to": "f"}, {"from": "f", "to": "a"}]
    result, _ = _run(nodes, edges)
    assert result.status == "completed"
    assert Failing.calls == 3 and [g["n"] for g in Seen.got] == [0, 1, 2]              # every item went through the whole body


def test_a_step_inside_a_loop_still_stops_the_run_by_default():
    nodes = [("t", "Start", {}), ("l", "Loop", {}), ("f", "Failing", {"message": "kaboom"})]
    result, _ = _run(nodes, [{"from": "t", "to": "l"}, {"from": "l", "to": "f"}])
    assert result.status == "failed" and Failing.calls == 1
