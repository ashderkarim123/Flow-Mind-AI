"""
MCP servers — connect external Model Context Protocol servers so workflows and AI nodes can use
their tools (web search, files, GitHub, databases, …).

Storage: users/{uid}/mcp_servers/{id}. Auth headers and env values are encrypted with the same
Fernet key as credentials and are never returned to the browser (only their *names* are).

Security model (see ai/mcp/remote.py): remote servers must pass the SSRF guard; local "command"
servers run arbitrary programs, so they need MCP_ALLOW_STDIO=true *and* an administrator.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ai.mcp import remote
from ai.mcp.remote import McpError, McpServer
from app.api.v1.credentials import _decrypt, _encrypt
from app.core.auth_dependency import is_admin, require_permission
from app.services.firebase_service import firebase_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])

MAX_SERVERS_PER_USER = 20

# Popular servers, one click to prefill the form. Command servers need Node.js (npx) or uv (uvx)
# installed on the machine running the backend.
CATALOG: List[Dict[str, Any]] = [
    {"key": "fetch", "name": "Web Fetch", "description": "Let the AI read any web page as clean text.",
     "transport": "stdio", "command": "uvx", "args": ["mcp-server-fetch"], "requires": "uv"},
    {"key": "time", "name": "Time & Dates", "description": "Current time and time-zone conversion.",
     "transport": "stdio", "command": "uvx", "args": ["mcp-server-time"], "requires": "uv"},
    {"key": "filesystem", "name": "Files", "description": "Read and write files inside one folder.",
     "transport": "stdio", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/data"],
     "requires": "Node.js", "hint": "Change the last argument to the folder the AI may access."},
    {"key": "memory", "name": "Memory", "description": "A small knowledge store the AI can save notes to.",
     "transport": "stdio", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"],
     "requires": "Node.js"},
    {"key": "remote", "name": "Remote MCP server", "description": "Any MCP server reachable by URL (many SaaS tools offer one).",
     "transport": "http", "url": "https://", "requires": None, "hint": "Paste the server URL and, if needed, its API key."},
]


class ServerIn(BaseModel):
    name: str
    transport: Literal["http", "stdio"] = "http"
    url: str = ""
    headers: Dict[str, str] = Field(default_factory=dict)    # e.g. {"Authorization": "Bearer …"}
    command: str = ""
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)


def _col(uid: str):
    return firebase_service.db.collection("users").document(uid).collection("mcp_servers")


def _public(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    created = data.get("createdAt")
    return {
        "id": doc_id,
        "name": data.get("name"),
        "transport": data.get("transport"),
        "url": data.get("url", ""),
        "command": data.get("command", ""),
        "args": data.get("args", []),
        "headerNames": data.get("headerNames", []),
        "envNames": data.get("envNames", []),
        "createdAt": created.isoformat() if hasattr(created, "isoformat") else created,
    }


def _to_server(doc_id: str, data: Dict[str, Any]) -> McpServer:
    secrets = json.loads(_decrypt(data["secrets"])) if data.get("secrets") else {}
    return McpServer(
        id=doc_id, name=data["name"], transport=data["transport"], url=data.get("url", ""),
        headers=secrets.get("headers", {}), command=data.get("command", ""),
        args=data.get("args", []), env=secrets.get("env", {}),
    )


def load_user_mcp_servers_sync(uid: str) -> Dict[str, McpServer]:
    """All of a user's servers keyed by name (secrets decrypted) — loaded once per workflow run."""
    servers: Dict[str, McpServer] = {}
    for doc in _col(uid).stream():
        try:
            servers[(doc.to_dict() or {})["name"]] = _to_server(doc.id, doc.to_dict())
        except Exception as exc:
            logger.warning("Skipping unreadable MCP server %s: %s", doc.id, exc)
    return servers


def _get_server(uid: str, server_id: str) -> McpServer:
    doc = _col(uid).document(server_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return _to_server(doc.id, doc.to_dict())


def _bad_gateway(exc: McpError) -> HTTPException:
    return HTTPException(status_code=502, detail=str(exc))


# ---------------------------------------------------------------------------

@router.get("/catalog")
async def catalog(user: dict = Depends(require_permission("workflow:read"))):
    return {"servers": CATALOG, "stdioEnabled": remote.stdio_allowed(), "canAddStdio": remote.stdio_allowed() and is_admin(user)}


@router.get("/servers")
async def list_servers(user: dict = Depends(require_permission("workflow:read"))):
    rows = [_public(d.id, d.to_dict()) for d in _col(user["uid"]).stream()]
    rows.sort(key=lambda r: str(r["createdAt"] or ""))
    return {"servers": rows}


@router.post("/servers", status_code=201)
async def add_server(body: ServerIn, user: dict = Depends(require_permission("workflow:write"))):
    uid = user["uid"]
    server = McpServer(id="", name=body.name.strip(), transport=body.transport, url=body.url.strip(),
                       headers=body.headers, command=body.command.strip(), args=body.args, env=body.env)
    if server.transport == "stdio" and not is_admin(user):
        raise HTTPException(status_code=403, detail="Only administrators can add local (command) MCP servers.")
    try:
        await remote.validate(server)
    except McpError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    existing = [d.to_dict().get("name", "").lower() for d in _col(uid).stream()]
    if server.name.lower() in existing:
        raise HTTPException(status_code=409, detail=f"You already have a server named '{server.name}'.")
    if len(existing) >= MAX_SERVERS_PER_USER:
        raise HTTPException(status_code=400, detail=f"You can connect at most {MAX_SERVERS_PER_USER} MCP servers.")

    doc_id = uuid.uuid4().hex
    data = {
        "name": server.name, "transport": server.transport, "url": server.url,
        "command": server.command, "args": server.args,
        "headerNames": sorted(server.headers), "envNames": sorted(server.env),
        "secrets": _encrypt(json.dumps({"headers": server.headers, "env": server.env})) if (server.headers or server.env) else "",
        "createdAt": datetime.now(timezone.utc),
    }
    _col(uid).document(doc_id).set(data)
    return _public(doc_id, data)


@router.delete("/servers/{server_id}")
async def delete_server(server_id: str, user: dict = Depends(require_permission("workflow:write"))):
    ref = _col(user["uid"]).document(server_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="MCP server not found")
    ref.delete()
    return {"success": True}


@router.get("/servers/{server_id}/tools")
async def server_tools(server_id: str, user: dict = Depends(require_permission("workflow:read"))):
    """Tools the server offers, with their input schemas (drives the 'MCP Tool' node's form)."""
    try:
        return {"tools": await remote.list_tools(_get_server(user["uid"], server_id))}
    except McpError as exc:
        raise _bad_gateway(exc)


@router.post("/servers/{server_id}/test")
async def test_server(server_id: str, user: dict = Depends(require_permission("workflow:read"))):
    """Connect, list tools — the 'Test connection' button. Always 200; `ok` says how it went."""
    try:
        tools = await remote.list_tools(_get_server(user["uid"], server_id))
        return {"ok": True, "toolCount": len(tools), "tools": [t["name"] for t in tools], "error": None}
    except McpError as exc:
        return {"ok": False, "toolCount": 0, "tools": [], "error": str(exc)}
