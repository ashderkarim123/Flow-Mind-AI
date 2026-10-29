"""
The AI agent loop and the MCP-facing nodes, end to end:

  Local LLM node ──HTTP──▶ fake OpenAI-compatible server (what Ollama looks like on the wire)
        │ tool calls
        └──MCP (stdio)──▶ real MCP server (tests/fake_mcp_server.py)

Run from backend/:  python -m pytest tests/test_ai_agent.py -q
"""

import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from ai.chat_loop import MAX_TOOL_ROUNDS  # noqa: E402
from ai.mcp.remote import McpServer  # noqa: E402
from executor.context import ExecutionContext  # noqa: E402
from nodes.ai.openai_chat import LocalLLM, _function_name, _names  # noqa: E402
from nodes.base import NodeExecutionError  # noqa: E402
from nodes.integrations.mcp_tool import MCPTool  # noqa: E402

FAKE_MCP = str(BACKEND / "tests" / "fake_mcp_server.py")
MCP_SERVER = McpServer(id="1", name="Fake tools", transport="stdio", command=sys.executable, args=[FAKE_MCP])


# ---------------------------------------------------------------------------
# Fake OpenAI-compatible server
# ---------------------------------------------------------------------------

class FakeLLM:
    """Scriptable chat-completions server. `script(request_json, n)` returns the JSON reply."""

    def __init__(self, script):
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                payload = json.dumps(script(body, len(outer.requests))).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


def reply(content=None, tool_calls=None, usage=(10, 5), model="qwen2.5:7b"):
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"model": model, "choices": [{"message": message, "finish_reason": "tool_calls" if tool_calls else "stop"}],
            "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1]}}


def call(name, args, call_id="call_1"):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


@pytest.fixture
def llm():
    servers = []

    def make(script):
        fake = FakeLLM(script)
        servers.append(fake)
        return fake

    yield make
    for fake in servers:
        fake.close()


@pytest.fixture(autouse=True)
def allow_local(monkeypatch):
    monkeypatch.setenv("ALLOW_PRIVATE_HOSTS", "true")
    monkeypatch.setenv("MCP_ALLOW_STDIO", "true")
    monkeypatch.delenv("LOCAL_LLM_BASE_URL", raising=False)


def context(**kw):
    return ExecutionContext(execution_id="e", workflow_id="w", user_id="u", mcp_servers={"Fake tools": MCP_SERVER}, **kw)


def run_local(config, ctx=None):
    return asyncio.run(LocalLLM().execute(config, {}, ctx or context()))


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def test_model_calls_an_mcp_tool_and_uses_the_result(llm):
    def script(request, n):
        if n == 1:
            return reply(tool_calls=[call("fake_tools__add", {"a": 2, "b": 3})], usage=(10, 5))
        return reply("The sum is 5.", usage=(20, 8))

    fake = llm(script)
    out = run_local({"prompt": "what is 2+3?", "model": "qwen2.5:7b", "base_url": fake.url, "mcp_servers": ["Fake tools"]})

    assert out["response"] == "The sum is 5."
    assert out["tool_calls"][0]["name"] == "fake_tools__add" and out["tool_calls"][0]["result"] == "5"
    # first request offered the MCP tools (with their schemas); second carried the tool result back
    offered = {t["function"]["name"] for t in fake.requests[0]["tools"]}
    assert {"fake_tools__add", "fake_tools__shout"} <= offered
    assert fake.requests[1]["messages"][-1] == {"role": "tool", "tool_call_id": "call_1", "content": "5"}
    # usage is summed over both rounds (the old code only counted the last one)
    assert (out["prompt_tokens"], out["completion_tokens"], out["tokens_used"]) == (30, 13, 43)


def test_no_tools_are_offered_when_none_are_selected(llm):
    fake = llm(lambda r, n: reply("hi"))
    out = run_local({"prompt": "hello", "base_url": fake.url})
    assert out["response"] == "hi" and "tools" not in fake.requests[0]


def test_a_failing_tool_is_reported_to_the_model_not_fatal(llm):
    def script(request, n):
        return reply(tool_calls=[call("fake_tools__boom", {})]) if n == 1 else reply("The tool failed, sorry.")

    fake = llm(script)
    out = run_local({"prompt": "x", "base_url": fake.url, "mcp_servers": "Fake tools"})   # comma-string form
    assert out["response"] == "The tool failed, sorry."
    assert fake.requests[1]["messages"][-1]["content"].startswith("Error:")


def test_runaway_tool_loops_are_cut_off_with_a_final_answer(llm):
    # the model keeps asking for tools as long as they are offered
    fake = llm(lambda r, n: reply(tool_calls=[call("fake_tools__add", {"a": 1, "b": 1}, f"c{n}")]) if "tools" in r
               else reply("Giving up and answering."))
    out = run_local({"prompt": "x", "base_url": fake.url, "mcp_servers": ["Fake tools"]})
    assert out["response"] == "Giving up and answering."
    assert len(fake.requests) == MAX_TOOL_ROUNDS + 1 and "tools" not in fake.requests[-1]


def test_unknown_mcp_server_is_a_clear_error(llm):
    fake = llm(lambda r, n: reply("hi"))
    with pytest.raises(NodeExecutionError, match="not connected"):
        run_local({"prompt": "x", "base_url": fake.url, "mcp_servers": ["Nope"]})


# ---------------------------------------------------------------------------
# Local-model friendliness + safety
# ---------------------------------------------------------------------------

def test_server_not_running_explains_how_to_start_ollama():
    with pytest.raises(NodeExecutionError, match="ollama serve"):
        run_local({"prompt": "x", "base_url": "http://127.0.0.1:9/v1"})


def test_model_not_installed_tells_you_to_pull_it(llm):
    fake = llm(lambda r, n: {"error": {"message": 'model "qwen9" not found, try pulling it first'}})
    with pytest.raises(NodeExecutionError, match="ollama pull qwen9"):
        run_local({"prompt": "x", "model": "qwen9", "base_url": fake.url})


def test_custom_server_url_is_checked_for_ssrf(monkeypatch):
    monkeypatch.delenv("ALLOW_PRIVATE_HOSTS", raising=False)
    with pytest.raises(NodeExecutionError, match="private"):
        run_local({"prompt": "x", "base_url": "http://169.254.169.254/v1"})


def test_operator_configured_local_url_is_trusted(llm, monkeypatch):
    fake = llm(lambda r, n: reply("ok"))
    monkeypatch.delenv("ALLOW_PRIVATE_HOSTS", raising=False)
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", fake.url)         # set by the operator, so localhost is fine
    assert run_local({"prompt": "x"})["response"] == "ok"


# ---------------------------------------------------------------------------
# MCP Tool node
# ---------------------------------------------------------------------------

def run_tool(config):
    return asyncio.run(MCPTool().execute(config, {}, context()))


def test_mcp_tool_node_converts_form_text_to_the_schema_types():
    out = run_tool({"server": "Fake tools", "tool": "add", "arguments": {"a": "2", "b": "40"},
                    "argTypes": {"a": "integer", "b": "integer"}})
    assert out == {"result": "42", "data": {"result": 42}, "tool": "add"}


def test_mcp_tool_node_accepts_json_text_arguments():
    out = run_tool({"server": "Fake tools", "tool": "shout", "arguments": '{"text": "hey", "times": 2}'})
    assert out["result"] == "HEY HEY"


def test_mcp_tool_node_failures_are_readable():
    with pytest.raises(NodeExecutionError, match="reported an error"):
        run_tool({"server": "Fake tools", "tool": "boom"})
    with pytest.raises(NodeExecutionError, match="not connected"):
        run_tool({"server": "Missing", "tool": "add"})
    with pytest.raises(NodeExecutionError, match="valid JSON"):
        run_tool({"server": "Fake tools", "tool": "add", "arguments": "{oops"})


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def test_function_names_are_safe_and_unique():
    taken = {}
    first = _function_name("github", "create issue!", taken)
    taken[first] = 1
    assert first == "github__create_issue_"
    assert _function_name("github", "create issue!", taken) != first
    assert len(_function_name("s" * 80, "t" * 80, {})) <= 64


def test_server_name_lists_accept_lists_and_comma_strings():
    assert _names(["A", " B "]) == ["A", "B"] and _names("A, B,,") == ["A", "B"] and _names(None) == []
