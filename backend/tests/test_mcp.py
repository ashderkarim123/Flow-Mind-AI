"""
MCP client tests against a real MCP server (tests/fake_mcp_server.py) over both transports,
plus the SSRF guard. No network beyond localhost.

Run from backend/:  python -m pytest tests/test_mcp.py -q
"""

import asyncio
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from ai.mcp import remote  # noqa: E402
from ai.mcp.remote import McpError, McpServer  # noqa: E402
from app.core.netguard import UnsafeURL, assert_safe_url  # noqa: E402

FAKE = str(BACKEND / "tests" / "fake_mcp_server.py")


def stdio_server(**kw):
    return McpServer(id="s1", name="Fake tools", transport="stdio", command=sys.executable, args=[FAKE], **kw)


@pytest.fixture
def stdio_on(monkeypatch):
    monkeypatch.setenv("MCP_ALLOW_STDIO", "true")


@pytest.fixture
def http_server(monkeypatch):
    """Start the fake server on a free port and allow localhost for the duration."""
    monkeypatch.setenv("ALLOW_PRIVATE_HOSTS", "true")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    proc = subprocess.Popen([sys.executable, FAKE, "--http", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("fake MCP HTTP server did not start")
        yield McpServer(id="h1", name="Remote fake", transport="http", url=f"http://127.0.0.1:{port}/mcp")
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# stdio
# ---------------------------------------------------------------------------

def test_stdio_lists_tools_with_schemas(stdio_on):
    tools = {t["name"]: t for t in run(remote.list_tools(stdio_server()))}
    assert {"add", "shout", "boom"} <= set(tools)
    assert tools["add"]["inputSchema"]["required"] == ["a", "b"]
    assert tools["add"]["description"] == "Add two numbers."


def test_stdio_call_tool_returns_text_and_data(stdio_on):
    result = run(remote.call_tool(stdio_server(), "add", {"a": 2, "b": 3}))
    assert result == {"text": "5", "data": {"result": 5}, "is_error": False}


def test_tool_failure_is_returned_not_raised(stdio_on):
    result = run(remote.call_tool(stdio_server(), "boom", {}))
    assert result["is_error"] is True and "boom" in result["text"]


def test_stdio_child_does_not_inherit_backend_secrets(stdio_on, monkeypatch):
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "super-secret")
    result = run(remote.call_tool(stdio_server(), "echo_env", {"name": "FIREBASE_PRIVATE_KEY"}))
    assert result["text"] == ""


def test_stdio_server_env_is_passed_through(stdio_on):
    server = stdio_server(env={"MY_TOKEN": "abc123"})
    assert run(remote.call_tool(server, "echo_env", {"name": "MY_TOKEN"}))["text"] == "abc123"


def test_stdio_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("MCP_ALLOW_STDIO", raising=False)
    with pytest.raises(McpError, match="disabled"):
        run(remote.list_tools(stdio_server()))


def test_missing_command_gives_a_readable_error(stdio_on):
    server = McpServer(id="x", name="Broken", transport="stdio", command="definitely-not-a-real-binary-xyz")
    with pytest.raises(McpError, match="not installed"):
        run(remote.list_tools(server))


# ---------------------------------------------------------------------------
# http
# ---------------------------------------------------------------------------

def test_http_transport_round_trip(http_server):
    assert "shout" in {t["name"] for t in run(remote.list_tools(http_server))}
    assert run(remote.call_tool(http_server, "shout", {"text": "hi", "times": 2}))["text"] == "HI HI"


def test_http_unreachable_server_gives_a_readable_error(monkeypatch):
    monkeypatch.setenv("ALLOW_PRIVATE_HOSTS", "true")
    dead = McpServer(id="d", name="Dead", transport="http", url="http://127.0.0.1:9/mcp")
    with pytest.raises(McpError, match="Could not connect"):
        run(remote.list_tools(dead))


# ---------------------------------------------------------------------------
# validation + SSRF guard
# ---------------------------------------------------------------------------

def test_localhost_is_blocked_unless_the_operator_allows_it(monkeypatch):
    monkeypatch.delenv("ALLOW_PRIVATE_HOSTS", raising=False)
    for url in ("http://127.0.0.1:8080/mcp", "http://localhost/mcp", "http://10.0.0.5/mcp", "http://169.254.169.254/"):
        with pytest.raises(UnsafeURL):
            assert_safe_url(url)
    with pytest.raises(UnsafeURL):
        assert_safe_url("file:///etc/passwd")
    monkeypatch.setenv("ALLOW_PRIVATE_HOSTS", "true")
    assert_safe_url("http://127.0.0.1:8080/mcp")


def test_validate_rejects_bad_definitions(monkeypatch):
    monkeypatch.delenv("ALLOW_PRIVATE_HOSTS", raising=False)
    with pytest.raises(McpError, match="short name"):
        run(remote.validate(McpServer(id="1", name="  ", transport="http", url="https://x.example")))
    with pytest.raises(McpError, match="private"):
        run(remote.validate(McpServer(id="1", name="ok", transport="http", url="http://127.0.0.1/mcp")))
    with pytest.raises(McpError, match="Transport"):
        run(remote.validate(McpServer(id="1", name="ok", transport="carrier-pigeon")))


def test_slug_is_safe_for_function_names():
    assert remote.slug("My GitHub (work)!") == "my_github_work"
    assert remote.slug("???") == "server"
