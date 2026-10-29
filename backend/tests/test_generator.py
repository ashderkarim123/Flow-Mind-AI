"""
Plain-English → workflow: parsing a model's reply, repairing its mistakes, and proving the result
is a workflow the real engine can run. The LLM is replaced by canned replies.

Run from backend/:  python -m pytest tests/test_generator.py -q
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import llm_service, workflow_generator as gen  # noqa: E402
from app.services.llm_service import extract_json  # noqa: E402
from executor.context import ExecutionContext  # noqa: E402
from executor.engine import WorkflowConnection, WorkflowDefinition, WorkflowEngine, WorkflowNode  # noqa: E402
from nodes.registry import get_registry  # noqa: E402

REGISTRY = get_registry()


def build(draft):
    return gen.build_workflow(draft, REGISTRY, "LocalLLM")


GOOD = {
    "name": "Summarise and post", "description": "Summarises incoming text.",
    "nodes": [
        {"id": "n1", "type": "Webhook", "name": "Receive text", "config": {}},
        {"id": "n2", "type": "LocalLLM", "name": "Summarise", "config": {"prompt": "Summarise: {{$trigger.body}}"}},
        {"id": "n3", "type": "SlackMessage", "name": "Post", "config": {"channel": "", "message": "{{$node.n2.response}}"}},
    ],
    "edges": [{"source": "n1", "target": "n2"}, {"source": "n2", "target": "n3"}],
}


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

def test_extract_json_handles_fences_chatter_and_braces_in_strings():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! Here you go:\n{"a": {"b": [1, 2]}}\nHope that helps') == {"a": {"b": [1, 2]}}
    assert extract_json('noise {"msg": "a } brace and \\"quote\\" {", "n": 2} tail') == {"msg": 'a } brace and "quote" {', "n": 2}
    for bad in ("no json here", '{"unterminated": ', "[1, 2]"):
        with pytest.raises(ValueError):
            extract_json(bad)


# ---------------------------------------------------------------------------
# Repair + validate
# ---------------------------------------------------------------------------

def test_good_draft_becomes_a_complete_editor_ready_workflow():
    wf = build(GOOD)
    assert [n["type"] for n in wf["nodes"]] == ["Webhook", "LocalLLM", "SlackMessage"]
    assert [n["category"] for n in wf["nodes"]] == ["trigger", "ai_ml", "action"]
    xs = [n["position"]["x"] for n in wf["nodes"]]
    assert xs == sorted(xs) and len(set(xs)) == 3                       # laid out left to right
    assert wf["edges"][0] == {"id": "e_n1_n2", "source": "n1", "target": "n2", "sourceHandle": "output",
                              "targetHandle": "input", "condition": None, "enabled": True}
    assert wf["nodes"][1]["config"]["model"]                             # defaults filled in for the editor
    assert wf["warnings"] == []
    assert [s["name"] for s in wf["steps"]] == ["Receive text", "Summarise", "Post"]


def test_todo_lists_required_fields_the_ai_could_not_know():
    todo = {(t["nodeName"], t["field"]) for t in build(GOOD)["todo"]}
    assert todo == {("Post", "channel")}                                  # empty channel; prompt/message were given


def test_unknown_nodes_are_dropped_with_a_warning_and_their_edges_too():
    draft = {"nodes": [{"id": "a", "type": "Webhook"}, {"id": "b", "type": "TeleportToMars", "name": "Beam"},
                       {"id": "c", "type": "Logger"}],
             "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}, {"source": "a", "target": "c"}]}
    wf = build(draft)
    assert [n["id"] for n in wf["nodes"]] == ["a", "c"]
    assert [(e["source"], e["target"]) for e in wf["edges"]] == [("a", "c")]
    assert any("Beam" in w and "removed" in w for w in wf["warnings"])


def test_sloppy_node_names_are_matched_to_real_types():
    wf = build({"nodes": [{"id": "1", "type": "manual trigger"}, {"id": "2", "type": "http_request"},
                          {"id": "3", "type": "If Condition"}, {"id": "4", "type": "SLACKMESSAGE"}]})
    assert [n["type"] for n in wf["nodes"]] == ["ManualTrigger", "HttpRequest", "IfCondition", "SlackMessage"]


def test_missing_trigger_and_missing_edges_are_repaired():
    wf = build({"nodes": [{"id": "a", "type": "HttpRequest", "config": {"url": "https://x.example"}},
                          {"id": "b", "type": "Logger"}]})
    assert wf["nodes"][0]["type"] == "ManualTrigger"
    assert [(e["source"], e["target"]) for e in wf["edges"]] == [("trigger", "a"), ("a", "b")]
    assert len(wf["warnings"]) == 2


def test_only_one_trigger_is_kept():
    wf = build({"nodes": [{"id": "a", "type": "Webhook"}, {"id": "b", "type": "Schedule", "config": {"cron": "0 9 * * *"}},
                          {"id": "c", "type": "Logger"}], "edges": [{"source": "a", "target": "c"}]})
    assert [n["id"] for n in wf["nodes"]] == ["a", "c"] and any("one trigger" in w for w in wf["warnings"])


def test_invalid_schedule_falls_back_to_a_safe_default():
    wf = build({"nodes": [{"id": "a", "type": "Schedule", "config": {"cron": "every morning"}}, {"id": "b", "type": "Logger"}]})
    assert wf["nodes"][0]["config"]["cron"] == "0 9 * * *" and any("schedule" in w.lower() for w in wf["warnings"])
    ok = build({"nodes": [{"id": "a", "type": "Schedule", "config": {"cron": "*/15 * * * *"}}]})
    assert ok["nodes"][0]["config"]["cron"] == "*/15 * * * *"


def test_duplicate_ids_are_renamed_and_references_follow():
    wf = build({"nodes": [{"id": "n1", "type": "Webhook"}, {"id": "n1", "type": "Logger", "config": {"message": "{{$node.n1.body}}"}}],
                "edges": [{"source": "n1", "target": "n1"}]})
    assert [n["id"] for n in wf["nodes"]] == ["n1", "n1_2"]
    assert len(wf["edges"]) == 1                                         # self-loop dropped, then chained


def test_references_to_missing_steps_and_fields_are_flagged():
    wf = build({"nodes": [{"id": "a", "type": "Webhook"},
                          {"id": "b", "type": "Logger", "config": {"message": "{{$node.ghost.x}} {{$node.a.nonexistent}}"}}],
                "edges": [{"source": "a", "target": "b"}]})
    text = " ".join(wf["warnings"])
    assert "does not exist" in text and "may not provide" in text


def test_numbers_and_booleans_are_coerced_and_unknown_keys_dropped():
    wf = build({"nodes": [{"id": "a", "type": "Webhook"},
                          {"id": "b", "type": "LocalLLM", "config": {"prompt": "x", "temperature": "0.3", "bogus": "?"}}],
                "edges": [{"source": "a", "target": "b"}]})
    config = wf["nodes"][1]["config"]
    assert config["temperature"] == 0.3 and "bogus" not in config


def test_if_branches_keep_their_condition():
    wf = build({"nodes": [{"id": "t", "type": "ManualTrigger"}, {"id": "i", "type": "IfCondition", "config": {"left": "1", "operator": "==", "right": "1"}},
                          {"id": "y", "type": "Logger"}, {"id": "n", "type": "Logger"}],
                "edges": [{"source": "t", "target": "i"}, {"source": "i", "target": "y", "condition": "true"},
                          {"source": "i", "target": "n", "condition": "false"}]})
    branches = {e["target"]: (e["condition"], e["sourceHandle"]) for e in wf["edges"] if e["source"] == "i"}
    assert branches == {"y": ("true", "true"), "n": ("false", "false")}


def test_a_draft_with_no_usable_steps_is_rejected():
    with pytest.raises(ValueError):
        build({"nodes": [{"id": "x", "type": "Nonsense"}]})
    with pytest.raises(ValueError):
        build({})


def test_layout_has_no_overlapping_nodes():
    draft = {"nodes": [{"id": "t", "type": "ManualTrigger"}] + [{"id": f"x{i}", "type": "Logger"} for i in range(5)],
             "edges": [{"source": "t", "target": f"x{i}"} for i in range(5)]}
    spots = [(n["position"]["x"], n["position"]["y"]) for n in build(draft)["nodes"]]
    assert len(set(spots)) == len(spots)


# ---------------------------------------------------------------------------
# generate(): retry, errors, and the result actually runs
# ---------------------------------------------------------------------------

LOCAL = llm_service.Endpoint("local", "http://x/v1", "k", "qwen2.5:7b")


def run_generate(monkeypatch, replies, prompt="when a webhook arrives, summarise it and post to Slack"):
    calls = []

    async def fake_chat(messages, **kw):
        calls.append(messages)
        return replies[len(calls) - 1]

    monkeypatch.setattr(llm_service, "chat", fake_chat)
    return asyncio.run(gen.generate(prompt, REGISTRY, LOCAL)), calls


def test_generate_retries_once_when_the_first_reply_is_not_json(monkeypatch):
    result, calls = run_generate(monkeypatch, ["Sorry, I can't do that", json.dumps(GOOD)])
    assert len(calls) == 2 and "not usable" in calls[1][-1]["content"]
    assert result["provider"] == "local" and result["model"] == "qwen2.5:7b" and len(result["nodes"]) == 3


def test_generate_prompt_uses_the_catalog_and_the_preferred_ai_node(monkeypatch):
    _, calls = run_generate(monkeypatch, [json.dumps(GOOD)])
    system = calls[0][0]["content"]
    assert '"LocalLLM"' in system and "- Webhook [Triggers] TRIGGER" in system and "MCPTool" in system


def test_generate_gives_up_with_a_helpful_message(monkeypatch):
    with pytest.raises(gen.GenerationError, match="could not turn that into a workflow"):
        run_generate(monkeypatch, ["nope", "still nope"])


def test_generate_rejects_empty_and_huge_prompts(monkeypatch):
    for prompt in ("", "hi", "x" * 5000):
        with pytest.raises(gen.GenerationError):
            run_generate(monkeypatch, ["{}"], prompt=prompt)


def test_catalog_is_small_enough_for_a_local_model():
    assert len(gen.catalog_text(REGISTRY)) < 9000          # ≈ 2k tokens — fits Ollama's default context


def test_a_generated_workflow_runs_on_the_real_engine(monkeypatch):
    draft = {"name": "Greeting flow", "nodes": [
        {"id": "t", "type": "ManualTrigger", "name": "Start"},
        {"id": "v", "type": "SetVariable", "name": "Remember", "config": {"variable_name": "greeting", "value": "hello"}},
        {"id": "l", "type": "Logger", "name": "Say it", "config": {"message": "{{$node.v.value}} world"}}],
        "edges": [{"source": "t", "target": "v"}, {"source": "v", "target": "l"}]}
    result, _ = run_generate(monkeypatch, [json.dumps(draft)])

    definition = WorkflowDefinition(
        id="gen", name=result["name"],
        nodes=[WorkflowNode(id=n["id"], type=n["type"], name=n["name"], config=n["config"]) for n in result["nodes"]],
        connections=[WorkflowConnection.from_dict(e) for e in result["edges"]])
    context = ExecutionContext(execution_id="e", workflow_id="gen", user_id="u")
    run = asyncio.run(WorkflowEngine(REGISTRY).execute(definition, {}, context))

    assert run.status == "completed", run.error
    assert [log.node_id for log in run.logs] == ["t", "v", "l"]
    assert context.node_outputs["l"]["message"] == "hello world"
