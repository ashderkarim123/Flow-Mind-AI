"""
Node configuration options: email providers and security, HTTP authentication, Slack webhooks, Postgres connection
details and workflow variables. Everything runs against small local fake servers - no network, no accounts.

Run from backend/:  python -m pytest tests/test_node_configs.py -q
"""

import asyncio
import base64
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from executor.context import ExecutionContext  # noqa: E402
from executor.engine import WorkflowConnection, WorkflowDefinition, WorkflowEngine, WorkflowNode  # noqa: E402
from nodes.actions import slack_message  # noqa: E402
from nodes.actions.http_request import HttpRequest  # noqa: E402
from nodes.actions.send_email import EMAIL_PROVIDERS, SendEmail, smtp_settings  # noqa: E402
from nodes.actions.slack_message import SlackMessage  # noqa: E402
from nodes.base import BaseNode, NodeDefinition, NodeExecutionError  # noqa: E402
from nodes.databases.postgres import postgres_connection_string  # noqa: E402
from nodes.registry import NodeRegistry  # noqa: E402


def _ctx(**kw) -> ExecutionContext:
    return ExecutionContext(execution_id="e", workflow_id="w", user_id="u", **kw)


def run(node: BaseNode, config: dict, ctx=None):
    return asyncio.run(node.execute(config, {}, ctx or _ctx()))


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("provider,host,port,security", [
    ("gmail", "smtp.gmail.com", 587, "starttls"),
    ("outlook", "smtp.office365.com", 587, "starttls"),
    ("yahoo", "smtp.mail.yahoo.com", 465, "ssl"),
    ("zoho", "smtp.zoho.com", 465, "ssl"),
    ("icloud", "smtp.mail.me.com", 587, "starttls"),
])
def test_provider_presets_fill_in_the_server(provider, host, port, security):
    assert smtp_settings({"provider": provider}) == {"host": host, "port": port, "security": security}


def test_typed_values_beat_the_preset():
    s = smtp_settings({"provider": "gmail", "smtp_host": "relay.corp.test", "smtp_port": "2525", "smtp_security": "none"})
    assert s == {"host": "relay.corp.test", "port": 2525, "security": "none"}


def test_custom_smtp_infers_security_from_the_port():
    assert smtp_settings({"smtp_host": "h", "smtp_port": 465})["security"] == "ssl"       # was always STARTTLS before: broke 465
    assert smtp_settings({"smtp_host": "h", "smtp_port": 587})["security"] == "starttls"
    assert smtp_settings({"smtp_host": "h"})["port"] == 587


def test_bad_port_or_security_is_explained():
    with pytest.raises(NodeExecutionError, match="port must be a number"):
        smtp_settings({"smtp_host": "h", "smtp_port": "abc"})
    with pytest.raises(NodeExecutionError, match="Connection security"):
        smtp_settings({"smtp_host": "h", "smtp_security": "magic"})


def test_every_provider_in_the_node_definition_has_a_preset():
    options = {o.value for p in SendEmail.definition.parameters if p.name == "provider" for o in p.options}
    assert options == set(EMAIL_PROVIDERS) | {"custom"}


class FakeSMTP:
    """A minimal SMTP server (EHLO, AUTH PLAIN, MAIL, RCPT, DATA) that records what it was sent."""

    def __init__(self):
        self.auth = None
        self.mail_from = None
        self.rcpts = []
        self.data = ""
        self.port = None
        self._ready = threading.Event()

    async def _client(self, reader, writer):
        async def say(line):
            writer.write((line + "\r\n").encode())
            await writer.drain()

        await say("220 fake ESMTP")
        while True:
            raw = await reader.readline()
            if not raw:
                break
            line = raw.decode().rstrip("\r\n")
            upper = line.upper()
            if upper.startswith("EHLO") or upper.startswith("HELO"):
                writer.write(b"250-fake\r\n250 AUTH PLAIN\r\n")
                await writer.drain()
            elif upper.startswith("AUTH PLAIN"):
                _, user, pw = base64.b64decode(line.split()[2]).decode().split("\x00")
                self.auth = (user, pw)
                await say("235 ok")
            elif upper.startswith("MAIL FROM"):
                self.mail_from = line.split(":", 1)[1].strip(" <>")
                await say("250 ok")
            elif upper.startswith("RCPT TO"):
                self.rcpts.append(line.split(":", 1)[1].strip(" <>"))
                await say("250 ok")
            elif upper == "DATA":
                await say("354 go")
                chunks = []
                while True:
                    part = (await reader.readline()).decode()
                    if part in (".\r\n", ".\n"):
                        break
                    chunks.append(part)
                self.data = "".join(chunks)
                await say("250 queued")
            elif upper == "QUIT":
                await say("221 bye")
                break
            else:
                await say("250 ok")
        writer.close()

    def __enter__(self):
        def serve():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            server = loop.run_until_complete(asyncio.start_server(self._client, "127.0.0.1", 0))
            self.port = server.sockets[0].getsockname()[1]
            self._loop, self._server = loop, server
            self._ready.set()
            loop.run_forever()

        self._thread = threading.Thread(target=serve, daemon=True)
        self._thread.start()
        self._ready.wait(5)
        return self

    def __exit__(self, *exc):
        self._loop.call_soon_threadsafe(self._loop.stop)


def _email_config(port, **extra):
    return {"to": "ann@example.com, Bob <bob@example.com>", "subject": "Hi\r\nBcc: evil@example.com", "body": "Hello",
            "smtp_host": "127.0.0.1", "smtp_port": port, "smtp_security": "none",
            "smtp_user": "me@example.com", "smtp_pass": "secret", "from_name": "FlowMind", **extra}


def test_email_is_delivered_with_cc_bcc_and_reply_to():
    with FakeSMTP() as smtp:
        out = run(SendEmail(), _email_config(smtp.port, cc="carol@example.com", bcc="dave@example.com", reply_to="help@example.com"))
    assert out["sent"] is True and out["to"] == "ann@example.com, bob@example.com"
    assert smtp.auth == ("me@example.com", "secret") and smtp.mail_from == "me@example.com"
    assert smtp.rcpts == ["ann@example.com", "bob@example.com", "carol@example.com", "dave@example.com"]
    assert "Cc: carol@example.com" in smtp.data and "Reply-To: help@example.com" in smtp.data
    assert "dave@example.com" not in smtp.data                 # a Bcc must never appear in the message itself
    assert not any(line.lower().startswith("bcc:") for line in smtp.data.splitlines())


def test_a_line_break_in_the_subject_cannot_inject_headers():
    with FakeSMTP() as smtp:
        run(SendEmail(), _email_config(smtp.port))
    headers = smtp.data.split("\n\n")[0] if "\n\n" in smtp.data else smtp.data.split("\r\n\r\n")[0]
    assert [l for l in headers.splitlines() if l.lower().startswith("bcc:")] == []


def test_html_flag_and_default_sender():
    with FakeSMTP() as smtp:
        run(SendEmail(), _email_config(smtp.port, is_html=True, body="<b>Hi</b>"))
    assert "Content-Type: text/html" in smtp.data and smtp.mail_from == "me@example.com"


@pytest.mark.parametrize("patch,message", [
    ({"to": "not-an-address"}, "invalid email address"),
    ({"cc": "ok@example.com, nope"}, "Cc has an invalid"),
    ({"to": " , "}, "at least one email address"),
    ({"smtp_host": "", "provider": "custom"}, "Pick your email service"),
    ({"smtp_pass": ""}, "Username and Password are required"),
])
def test_email_mistakes_are_explained(patch, message):
    with pytest.raises(NodeExecutionError, match=message):
        run(SendEmail(), {**_email_config(1), **patch})


def test_an_unreachable_server_is_reported_not_raised_raw():
    with pytest.raises(NodeExecutionError, match="Failed to send email"):
        run(SendEmail(), _email_config(1))                       # nothing listens on port 1


# ---------------------------------------------------------------------------
# HTTP request authentication
# ---------------------------------------------------------------------------

class Echo(BaseHTTPRequestHandler):
    """Answers every request with the headers and path it received."""

    def _answer(self):
        body = json.dumps({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = _answer

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def echo_server():
    server = HTTPServer(("127.0.0.1", 0), Echo)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def _http(url, **cfg):
    return run(HttpRequest(), {"url": url, **cfg})["response_body"]


def test_no_auth_sends_no_authorization_header(echo_server):
    assert "authorization" not in _http(echo_server)["headers"]


def test_bearer_token(echo_server):
    got = _http(echo_server, auth_type="bearer", auth_token="abc123")
    assert got["headers"]["authorization"] == "Bearer abc123"


def test_basic_auth(echo_server):
    got = _http(echo_server, auth_type="basic", auth_username="ann", auth_password="pw")
    assert got["headers"]["authorization"] == "Basic " + base64.b64encode(b"ann:pw").decode()


def test_api_key_in_a_header_and_in_the_url(echo_server):
    assert _http(echo_server, auth_type="api_key_header", auth_key_name="X-API-Key", auth_key_value="k1")["headers"]["x-api-key"] == "k1"
    got = _http(echo_server, auth_type="api_key_query", auth_key_name="api_key", auth_key_value="k2", query_params={"page": "2"})
    assert "api_key=k2" in got["path"] and "page=2" in got["path"]


def test_auth_is_added_to_headers_the_user_set(echo_server):
    got = _http(echo_server, auth_type="bearer", auth_token="t", headers={"X-Trace": "1"})
    assert got["headers"]["x-trace"] == "1" and got["headers"]["authorization"] == "Bearer t"


def test_headers_typed_as_json_text_are_accepted(echo_server):
    assert _http(echo_server, headers='{"X-From": "text"}')["headers"]["x-from"] == "text"


@pytest.mark.parametrize("cfg,message", [
    ({"auth_type": "bearer"}, "Token is required"),
    ({"auth_type": "basic", "auth_password": "x"}, "Username is required"),
    ({"auth_type": "api_key_header", "auth_key_name": "X"}, "Key value is required"),
    ({"auth_type": "magic"}, "Unknown authentication type"),
    ({"headers": "not json"}, "Headers must be a JSON object"),
    ({"headers": "[1, 2]"}, "Headers must be a JSON object"),
])
def test_http_mistakes_are_explained(echo_server, cfg, message):
    with pytest.raises(NodeExecutionError, match=message):
        run(HttpRequest(), {"url": echo_server, **cfg})


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

class FakeSlackWebhook(BaseHTTPRequestHandler):
    received = []
    reply = (200, b"ok")

    def do_POST(self):
        FakeSlackWebhook.received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        status, text = FakeSlackWebhook.reply
        self.send_response(status)
        self.send_header("Content-Length", str(len(text)))
        self.end_headers()
        self.wfile.write(text)

    def log_message(self, *a):
        pass


@pytest.fixture
def slack_hook(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), FakeSlackWebhook)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    FakeSlackWebhook.received, FakeSlackWebhook.reply = [], (200, b"ok")
    base = f"http://127.0.0.1:{server.server_port}/"
    monkeypatch.setattr(slack_message, "SLACK_WEBHOOK_PREFIX", base)
    yield base
    server.shutdown()


def test_slack_webhook_posts_the_message(slack_hook):
    out = run(SlackMessage(), {"mode": "webhook", "webhook_url": slack_hook + "T1/B1/xyz", "message": "Deploy done", "username": "Bot"})
    assert out["sent"] is True
    assert FakeSlackWebhook.received == [{"text": "Deploy done", "username": "Bot"}]


def test_slack_webhook_error_text_is_surfaced(slack_hook):
    FakeSlackWebhook.reply = (400, b"invalid_payload")
    with pytest.raises(NodeExecutionError, match="invalid_payload"):
        run(SlackMessage(), {"mode": "webhook", "webhook_url": slack_hook + "x", "message": "hi"})


def test_slack_webhook_refuses_other_addresses():
    with pytest.raises(NodeExecutionError, match="must start with https://hooks.slack.com/"):
        run(SlackMessage(), {"mode": "webhook", "webhook_url": "http://169.254.169.254/latest/meta-data", "message": "hi"})


def test_slack_bot_mode_still_needs_a_channel_and_token():
    with pytest.raises(NodeExecutionError, match="channel"):
        run(SlackMessage(), {"message": "hi", "token": "xoxb-1"})
    with pytest.raises(NodeExecutionError, match="bot token is required"):
        run(SlackMessage(), {"channel": "#general", "message": "hi"})
    with pytest.raises(NodeExecutionError, match="Unknown connection type"):
        run(SlackMessage(), {"mode": "carrier-pigeon", "message": "hi"})


# ---------------------------------------------------------------------------
# Postgres connection details
# ---------------------------------------------------------------------------

def test_a_typed_connection_string_wins():
    assert postgres_connection_string({"connection_string": " postgresql://u:p@h/d ", "host": "other"}) == "postgresql://u:p@h/d"


def test_connection_details_become_a_url_with_the_password_encoded():
    url = postgres_connection_string({"host": "db.example.com", "port": 6543, "database": "app db", "username": "me@corp",
                                      "password": "p@ss/w:rd#1", "ssl_mode": "require"})
    parsed = urlparse(url)
    assert (parsed.hostname, parsed.port, parsed.query) == ("db.example.com", 6543, "sslmode=require")
    assert unquote(parsed.username) == "me@corp" and unquote(parsed.password) == "p@ss/w:rd#1"
    assert unquote(parsed.path) == "/app db"


def test_incomplete_details_give_an_empty_string_and_defaults_apply():
    assert postgres_connection_string({"host": "h", "username": "u"}) == ""                  # no database
    assert postgres_connection_string({"host": "h", "database": "d", "username": "u"}).endswith("@h:5432/d?sslmode=prefer")


def test_bad_port_or_ssl_mode_is_explained():
    base = {"host": "h", "database": "d", "username": "u"}
    with pytest.raises(NodeExecutionError, match="port must be a number"):
        postgres_connection_string({**base, "port": "x"})
    with pytest.raises(NodeExecutionError, match="SSL mode"):
        postgres_connection_string({**base, "ssl_mode": "sometimes"})


# ---------------------------------------------------------------------------
# Workflow variables
# ---------------------------------------------------------------------------

class Capture(BaseNode):
    definition = NodeDefinition(type="Capture", display_name="Capture", description="", category="Test", icon="",
                                color="#000", is_trigger=False, parameters=[], outputs=[])
    seen = {}

    async def execute(self, config, input_data, context):
        Capture.seen = dict(config)
        return {}


class Start(BaseNode):
    definition = NodeDefinition(type="Start", display_name="Start", description="", category="Test", icon="",
                                color="#000", is_trigger=True, parameters=[], outputs=[])

    async def execute(self, config, input_data, context):
        return {}


def test_workflow_variables_are_available_to_every_step_as_vars():
    registry = NodeRegistry()
    for cls in (Start, Capture):
        registry.register(cls)
    wf = WorkflowDefinition(
        nodes=[WorkflowNode(id="t", type="Start"),
               WorkflowNode(id="c", type="Capture", config={"greeting": "Hello {{$vars.customer}}!", "limit": "{{$vars.max_rows}}"})],
        connections=[WorkflowConnection.from_dict({"from": "t", "to": "c"})])
    ctx = _ctx(variables={"customer": "Acme", "max_rows": 25})
    result = asyncio.run(WorkflowEngine(registry).execute(wf, {}, ctx))
    assert result.status == "completed"
    assert Capture.seen == {"greeting": "Hello Acme!", "limit": 25}       # the number keeps its type


# ---------------------------------------------------------------------------
# Whole scenarios through the real engine and the real node registry
# ---------------------------------------------------------------------------

def _real_run(nodes, edges, **ctx):
    from nodes.registry import get_registry
    wf = WorkflowDefinition(nodes=[WorkflowNode(id=i, type=t, config=c) for i, t, c in nodes],
                            connections=[WorkflowConnection.from_dict(e) for e in edges])
    context = _ctx(**ctx)
    return asyncio.run(WorkflowEngine(get_registry()).execute(wf, {}, context)), context


def test_scenario_variables_fill_an_email_sent_through_the_engine():
    with FakeSMTP() as smtp:
        result, _ = _real_run(
            [("t", "ManualTrigger", {}),
             ("m", "SendEmail", {**_email_config(smtp.port), "to": "{{$vars.recipient}}", "subject": "Report for {{$vars.customer}}",
                                 "body": "{{$vars.rows}} rows processed", "provider": "custom"})],
            [{"from": "t", "to": "m"}], variables={"recipient": "ann@example.com", "customer": "Acme", "rows": 25})
    assert result.status == "completed"
    assert smtp.rcpts == ["ann@example.com"] and "Subject: Report for Acme" in smtp.data and "25 rows processed" in smtp.data


def test_scenario_a_failed_email_can_carry_on_and_the_next_step_sees_the_error():
    result, ctx = _real_run(
        [("t", "ManualTrigger", {}),
         ("m", "SendEmail", {**_email_config(1), "_settings": {"on_error": "continue"}}),     # nothing listens on port 1
         ("l", "Logger", {"level": "warning", "message": "email failed: {{$node.m.error}}"})],
        [{"from": "t", "to": "m"}, {"from": "m", "to": "l"}])
    assert result.status == "completed"
    assert [log.status.value for log in result.logs] == ["success", "failed", "success"]
    assert ctx.node_outputs["l"]["message"].startswith("email failed: Failed to send email")


def test_scenario_http_bearer_then_if_branch_on_the_status(echo_server):
    result, ctx = _real_run(
        [("t", "ManualTrigger", {}),
         ("h", "HttpRequest", {"url": echo_server, "auth_type": "bearer", "auth_token": "{{$vars.token}}"}),
         ("i", "IfCondition", {"left": "{{$node.h.status_code}}", "operator": "==", "right": "200"}),
         ("ok", "Logger", {"level": "info", "message": "token seen: {{$node.h.response_body.headers.authorization}}"}),
         ("bad", "Logger", {"level": "error", "message": "should not run"})],
        [{"from": "t", "to": "h"}, {"from": "h", "to": "i"},
         {"from": "i", "to": "ok", "condition": "true"}, {"from": "i", "to": "bad", "condition": "false"}],
        variables={"token": "abc123"})
    assert result.status == "completed"
    assert ctx.node_outputs["ok"]["message"] == "token seen: Bearer abc123" and "bad" not in ctx.node_outputs


def test_typed_variables_become_plain_values_for_the_engine():
    from executor.context import plain_variables
    typed = {"customer": {"type": "string", "value": "Acme"}, "rows": {"type": "number", "value": 25},
             "active": {"type": "boolean", "value": False}, "filters": {"type": "json", "value": '{"a": [1]}'},
             "bad_json": {"type": "json", "value": "not json"}, "token": {"type": "secret", "value": None, "secretRef": "TOKEN"}}
    assert plain_variables(typed) == {"customer": "Acme", "rows": 25, "active": False, "filters": {"a": [1]}, "bad_json": "not json"}


def test_plain_variables_pass_through_unchanged():
    from executor.context import plain_variables
    plain = {"a": "x", "b": 3, "nested": {"k": "v"}, "typed_like": {"type": "x", "other": 1}}
    assert plain_variables(plain) == plain
    assert plain_variables(None) == {} and plain_variables({}) == {}


def test_vars_expressions_follow_paths_into_json_variables():
    from executor.resolver import resolve
    ctx = _ctx(variables={"limits": {"max": 3, "tags": ["a", "b"]}, "dotted.name": "flat", "n": 5})
    got = resolve({"a": "{{$vars.limits.max}}", "b": "{{$vars.limits.tags.1}}", "c": "{{$vars.dotted.name}}",
                   "d": "{{$vars.n}}", "e": "{{$vars.limits.nope}}", "f": "{{$vars.n.deeper}}"}, ctx)
    assert got["a"] == 3 and got["b"] == "b" and got["c"] == "flat" and got["d"] == 5
    assert got["e"] == "{{$vars.limits.nope}}" and got["f"] == "{{$vars.n.deeper}}"      # a miss leaves the text, as before
