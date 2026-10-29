"""
Real Model Context Protocol (MCP) client — talks to external MCP servers.

Transports
  http   a remote MCP server (streamable HTTP) with optional auth headers
  stdio  a local command the backend spawns (npx / uvx / python …). Running a command is
         remote-code-execution by design, so it is OFF unless MCP_ALLOW_STDIO=true, and only
         administrators can register such a server (see app/api/v1/mcp.py). The child process
         gets a minimal environment — never the backend's secrets — plus the server's own `env`.

Every call opens a short-lived session (connect → initialize → work → close). That is simple and
robust; pool sessions if latency ever matters.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List

from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from app.core.netguard import UnsafeURL, assert_safe_url

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = float(os.getenv("MCP_TIMEOUT_SECONDS", "60"))
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,39}$")


class McpError(Exception):
    """A problem with an MCP server, worded for the person who configured it."""


@dataclass
class McpServer:
    id: str
    name: str
    transport: str                      # "http" | "stdio"
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)


def stdio_allowed() -> bool:
    return os.getenv("MCP_ALLOW_STDIO", "").strip().lower() in {"1", "true", "yes", "on"}


def slug(name: str) -> str:
    """Name → identifier safe inside an LLM function name."""
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower() or "server"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

async def validate(server: McpServer) -> None:
    """Raise McpError if this server definition must not be saved or used."""
    if not NAME_RE.match(server.name or ""):
        raise McpError("Give the server a short name using letters, numbers, spaces, '-', '_' or '.'.")
    if server.transport == "http":
        try:
            await asyncio.to_thread(assert_safe_url, server.url)
        except UnsafeURL as exc:
            raise McpError(str(exc)) from exc
    elif server.transport == "stdio":
        if not stdio_allowed():
            raise McpError(
                "Local (command) MCP servers are disabled on this server. Use a remote server URL, "
                "or ask the administrator to set MCP_ALLOW_STDIO=true."
            )
        if not server.command.strip() or len(server.args) > 20:
            raise McpError("A local MCP server needs a command (and at most 20 arguments).")
    else:
        raise McpError("Transport must be 'http' or 'stdio'.")


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _session(server: McpServer):
    await validate(server)   # re-checked on every use: env flags / DNS may have changed since saving
    if server.transport == "http":
        client = create_mcp_http_client(headers=server.headers or None)
        async with client:
            async with streamable_http_client(server.url, http_client=client) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    yield session
    else:
        params = StdioServerParameters(command=server.command, args=server.args, env=server.env or None)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


def _friendly(exc: BaseException, server: McpServer) -> McpError:
    """Turn transport/SDK exceptions (often wrapped in ExceptionGroups) into a readable message."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    where = server.url if server.transport == "http" else f"'{server.command}'"
    if isinstance(exc, McpError):
        return exc
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return McpError(f"'{server.name}' did not answer within {TIMEOUT_SECONDS:.0f}s ({where}).")
    if isinstance(exc, FileNotFoundError):
        return McpError(
            f"Could not start '{server.command}' — it is not installed on the server "
            f"(npx needs Node.js, uvx needs uv)."
        )
    text = str(exc) or type(exc).__name__
    if "401" in text or "403" in text:
        return McpError(f"'{server.name}' rejected the credentials (check the API key / token header).")
    if "404" in text:
        return McpError(f"'{server.name}' was not found at {where} (check the URL — many servers use a path like /mcp).")
    if any(k in text.lower() for k in ("connect", "refused", "unreachable", "name or service", "getaddrinfo")):
        return McpError(f"Could not connect to {where}. Is the MCP server running and reachable from this server?")
    return McpError(f"'{server.name}' failed: {text[:300]}")


async def _run(server: McpServer, work):
    """Open a session, run `work(session)`, apply the timeout and normalise errors."""
    async def go():
        async with _session(server) as session:
            return await work(session)
    try:
        return await asyncio.wait_for(go(), timeout=TIMEOUT_SECONDS)
    except McpError:
        raise
    except BaseException as exc:  # includes ExceptionGroup from anyio task groups
        if isinstance(exc, (KeyboardInterrupt, SystemExit, asyncio.CancelledError)):
            raise
        logger.warning("MCP call to %s failed: %r", server.name, exc)
        raise _friendly(exc, server) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def list_tools(server: McpServer) -> List[Dict[str, Any]]:
    """[{name, description, inputSchema}] — # ponytail: first page only (servers with >100 tools are rare)."""
    async def work(session: ClientSession):
        result = await session.list_tools()
        return [
            {"name": t.name, "description": t.description or "", "inputSchema": t.input_schema or {"type": "object"}}
            for t in result.tools
        ]
    return await _run(server, work)


async def call_tool(server: McpServer, tool: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Run a tool → {text, data, is_error}. A tool-level failure is returned, not raised."""
    async def work(session: ClientSession):
        return await session.call_tool(tool, arguments or {})
    result = await _run(server, work)

    # Non-text blocks (images, files) become a "[type]" placeholder; an empty text block stays empty
    parts = [
        block.text if getattr(block, "text", None) is not None else f"[{getattr(block, 'type', 'content')}]"
        for block in result.content
    ]
    text = "\n".join(parts)
    data = result.structured_content
    if data is None and text:
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            data = None
    return {"text": text, "data": data, "is_error": bool(result.is_error)}
