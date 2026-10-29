"""
HTTP tests for the AI/MCP features: status + local models, workflow generation, the assistant,
and the MCP server connections API (including how secrets are stored and hidden).

Run from backend/:  python -m pytest tests/test_ai_features_api.py -q
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))          # fixtures live in sibling test modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_api_flows import env  # noqa: E402,F401  (pytest fixture: app + fake Firestore + role switcher)
from test_mcp import FAKE, http_server  # noqa: E402,F401  (real MCP server over HTTP)

from app.api.v1.mcp import load_user_mcp_servers_sync  # noqa: E402
from app.services import llm_service  # noqa: E402

DRAFT = {"name": "Hello", "nodes": [{"id": "t", "type": "ManualTrigger"}, {"id": "l", "type": "Logger", "config": {"message": "hi"}}],
         "edges": [{"source": "t", "target": "l"}]}


class FakeOllama:
    """Answers GET /v1/models like Ollama does."""

    def __init__(self, models):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                payload = json.dumps({"data": [{"id": m} for m in models]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *a):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


@pytest.fixture
def ollama(monkeypatch):
    servers = []

    def start(models):
        server = FakeOllama(models)
        servers.append(server)
        monkeypatch.setenv("LOCAL_LLM_BASE_URL", server.url)
        monkeypatch.setenv("ASSISTANT_PROVIDER", "local")
        return server

    yield start
    for server in servers:
        server.close()


# ---------------------------------------------------------------------------
# status + local models
# ---------------------------------------------------------------------------

def test_status_reports_installed_models_and_a_ready_assistant(env, ollama, monkeypatch):
    ollama(["qwen2.5:7b", "llama3.2:latest"])
    monkeypatch.setenv("LOCAL_LLM_MODEL", "qwen2.5:7b")
    status = env.as_("user").get("/api/v1/ai/status").json()
    assert status["local"]["reachable"] and status["local"]["models"] == ["llama3.2:latest", "qwen2.5:7b"]
    assert status["assistant"] == {"provider": "local", "model": "qwen2.5:7b", "ready": True, "problem": None}


def test_status_tells_you_to_pull_a_missing_model(env, ollama, monkeypatch):
    ollama(["llama3.2:latest"])
    monkeypatch.setenv("LOCAL_LLM_MODEL", "qwen2.5:7b")
    assistant = env.as_("user").get("/api/v1/ai/status").json()["assistant"]
    assert assistant["ready"] is False and "ollama pull qwen2.5:7b" in assistant["problem"]


def test_status_when_ollama_is_not_running(env, monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("ASSISTANT_PROVIDER", "local")
    status = env.as_("user").get("/api/v1/ai/status").json()
    assert status["local"]["reachable"] is False and "ollama serve" in status["local"]["error"]
    assert status["assistant"]["ready"] is False


def test_status_never_leaks_api_key_values(env, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")
    text = env.as_("user").get("/api/v1/ai/status").text
    assert "sk-secret-value" not in text and '"openai":true' in text.replace(" ", "")


def test_local_models_custom_address_goes_through_the_ssrf_guard(env, monkeypatch):
    monkeypatch.delenv("ALLOW_PRIVATE_HOSTS", raising=False)
    result = env.as_("user").get("/api/v1/ai/local-models", params={"base_url": "http://169.254.169.254/v1"}).json()
    assert result["reachable"] is False and "private" in result["error"]


# ---------------------------------------------------------------------------
# generate + assist
# ---------------------------------------------------------------------------

def stub_chat(monkeypatch, reply=None, error=None):
    async def fake_chat(messages, **kw):
        if error:
            raise error
        return reply

    monkeypatch.setattr(llm_service, "chat", fake_chat)
    monkeypatch.setenv("ASSISTANT_PROVIDER", "local")


def test_generate_returns_a_draft_for_users_but_not_viewers(env, monkeypatch):
    stub_chat(monkeypatch, json.dumps(DRAFT))
    body = {"prompt": "log a greeting when I press run"}
    ok = env.as_("user").post("/api/v1/ai/generate-workflow", json=body)
    assert ok.status_code == 200 and [n["type"] for n in ok.json()["nodes"]] == ["ManualTrigger", "Logger"]
    assert env.as_("viewer").post("/api/v1/ai/generate-workflow", json=body).status_code == 403
    assert env.database.data["workflows"].keys() == {"wf1", "hook1"}      # a draft is never saved by this call


def test_generate_maps_problems_to_useful_statuses(env, monkeypatch):
    client = env.as_("user")
    assert client.post("/api/v1/ai/generate-workflow", json={"prompt": "hi"}).status_code == 422
    stub_chat(monkeypatch, error=llm_service.LLMUnavailable("Can't reach the AI model server. Start Ollama."))
    down = client.post("/api/v1/ai/generate-workflow", json={"prompt": "log a greeting when I press run"})
    assert down.status_code == 503 and "Start Ollama" in down.json()["message"]
    stub_chat(monkeypatch, "I am a teapot")
    assert client.post("/api/v1/ai/generate-workflow", json={"prompt": "log a greeting when I press run"}).status_code == 422


def test_assistant_answers_with_the_node_catalog_in_its_prompt(env, monkeypatch):
    seen = {}

    async def fake_chat(messages, **kw):
        seen["system"] = messages[0]["content"]
        return "Use the Webhook node."

    monkeypatch.setattr(llm_service, "chat", fake_chat)
    reply = env.as_("user").post("/api/v1/ai/assist", json={"question": "how do I start a flow from a form?",
                                                              "current_state": {"nodes": []}})
    assert reply.json()["answer"] == "Use the Webhook node."
    assert "- Webhook [Triggers] TRIGGER" in seen["system"] and "current workflow" in seen["system"]


# ---------------------------------------------------------------------------
# MCP connections API
# ---------------------------------------------------------------------------

def add_http(client, server, **extra):
    return client.post("/api/v1/mcp/servers", json={"name": "Docs search", "transport": "http", "url": server.url, **extra})


def test_connect_a_remote_server_then_list_test_and_use_its_tools(env, http_server):
    client = env.as_("user")
    created = add_http(client, http_server)
    assert created.status_code == 201
    server_id = created.json()["id"]

    assert [s["name"] for s in client.get("/api/v1/mcp/servers").json()["servers"]] == ["Docs search"]
    tools = client.get(f"/api/v1/mcp/servers/{server_id}/tools").json()["tools"]
    assert "add" in {t["name"] for t in tools} and next(t for t in tools if t["name"] == "add")["inputSchema"]["required"] == ["a", "b"]
    test = client.post(f"/api/v1/mcp/servers/{server_id}/test").json()
    assert test["ok"] is True and test["toolCount"] >= 4 and test["error"] is None

    assert load_user_mcp_servers_sync("u-user")["Docs search"].url == http_server.url        # what a workflow run loads
    assert client.delete(f"/api/v1/mcp/servers/{server_id}").status_code == 200
    assert client.get("/api/v1/mcp/servers").json()["servers"] == []


def test_secret_headers_are_encrypted_at_rest_and_never_returned(env, http_server):
    client = env.as_("user")
    created = add_http(client, http_server, headers={"Authorization": "Bearer sk-very-secret"}).json()
    assert created["headerNames"] == ["Authorization"]
    assert "sk-very-secret" not in json.dumps(created) and "sk-very-secret" not in client.get("/api/v1/mcp/servers").text
    stored = next(iter(env.database.data["users/u-user/mcp_servers"].values()))
    assert "sk-very-secret" not in json.dumps(stored, default=str)                          # ciphertext only
    assert load_user_mcp_servers_sync("u-user")["Docs search"].headers == {"Authorization": "Bearer sk-very-secret"}


def test_servers_are_private_to_their_owner(env, http_server):
    server_id = add_http(env.as_("user"), http_server).json()["id"]
    other = env.as_("admin")
    assert other.get("/api/v1/mcp/servers").json()["servers"] == []
    assert other.get(f"/api/v1/mcp/servers/{server_id}/tools").status_code == 404
    assert other.delete(f"/api/v1/mcp/servers/{server_id}").status_code == 404


def test_viewers_cannot_connect_servers(env, http_server):
    assert add_http(env.as_("viewer"), http_server).status_code == 403


def test_duplicate_names_and_bad_addresses_are_rejected_with_reasons(env, http_server, monkeypatch):
    client = env.as_("user")
    assert add_http(client, http_server).status_code == 201
    dup = add_http(client, http_server)
    assert dup.status_code == 409 and "already have" in dup.json()["message"]
    monkeypatch.delenv("ALLOW_PRIVATE_HOSTS")
    private = client.post("/api/v1/mcp/servers", json={"name": "Local", "transport": "http", "url": "http://127.0.0.1:8000/mcp"})
    assert private.status_code == 400 and "private" in private.json()["message"]


def test_command_servers_need_the_flag_and_an_admin(env, monkeypatch):
    body = {"name": "Local fake", "transport": "stdio", "command": sys.executable, "args": [FAKE]}
    monkeypatch.delenv("MCP_ALLOW_STDIO", raising=False)
    assert env.as_("admin").post("/api/v1/mcp/servers", json=body).status_code == 400            # flag off
    monkeypatch.setenv("MCP_ALLOW_STDIO", "true")
    forbidden = env.as_("user").post("/api/v1/mcp/servers", json=body)
    assert forbidden.status_code == 403 and "administrators" in forbidden.json()["message"]
    assert env.as_("admin").post("/api/v1/mcp/servers", json=body).status_code == 201


def test_unreachable_server_reports_a_readable_error_on_test(env, http_server):
    client = env.as_("user")
    server_id = add_http(client, http_server).json()["id"]
    env.database.data["users/u-user/mcp_servers"][server_id]["url"] = "http://127.0.0.1:9/mcp"   # server went away
    result = client.post(f"/api/v1/mcp/servers/{server_id}/test").json()
    assert result["ok"] is False and "Could not connect" in result["error"]
    assert client.get(f"/api/v1/mcp/servers/{server_id}/tools").status_code == 502


def test_catalog_flags_whether_command_servers_can_be_added(env, monkeypatch):
    monkeypatch.delenv("MCP_ALLOW_STDIO", raising=False)
    assert env.as_("admin").get("/api/v1/mcp/catalog").json()["canAddStdio"] is False
    monkeypatch.setenv("MCP_ALLOW_STDIO", "true")
    catalog = env.as_("admin").get("/api/v1/mcp/catalog").json()
    assert catalog["canAddStdio"] is True and {"fetch", "filesystem", "remote"} <= {s["key"] for s in catalog["servers"]}
    assert env.as_("user").get("/api/v1/mcp/catalog").json()["canAddStdio"] is False
