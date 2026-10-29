"""MCP Tool — call one tool of a connected MCP server and pass its result on."""

from __future__ import annotations

import json
from typing import Any, Dict

from ai.mcp import remote
from ai.mcp.remote import McpError
from nodes.base import (
    BaseNode, NodeDefinition, NodeExecutionError, NodeOutputField, NodeParameter, ParameterType,
)


def _coerce(arguments: Dict[str, Any], types: Dict[str, str]) -> Dict[str, Any]:
    """The form stores every typed value as text; convert to the type the tool's schema declares.

    Values that are still `{{…}}` templates have been resolved to text by now, so the same
    conversion applies. Anything that does not parse is passed through unchanged and the tool
    will report the problem.
    """
    out = dict(arguments)
    for key, kind in (types or {}).items():
        value = out.get(key)
        if not isinstance(value, str):
            continue
        try:
            if kind == "integer":
                out[key] = int(float(value))
            elif kind == "number":
                out[key] = float(value)
            elif kind == "boolean":
                out[key] = value.strip().lower() in {"1", "true", "yes", "on"}
            elif kind in ("object", "array"):
                out[key] = json.loads(value)
        except (ValueError, TypeError):
            pass
    return out


class MCPTool(BaseNode):
    definition = NodeDefinition(
        type="MCPTool",
        display_name="MCP Tool",
        description="Use a tool from a connected MCP server (web fetch, files, GitHub, databases, …) without writing code.",
        category="Integrations",
        icon="🧩",
        color="#7C3AED",
        is_trigger=False,
        parameters=[
            NodeParameter(name="server", display_name="MCP server", type=ParameterType.STRING, required=True,
                          description="Name of a server added on the Connections page."),
            NodeParameter(name="tool", display_name="Tool", type=ParameterType.STRING, required=True,
                          description="Which tool of that server to run."),
            NodeParameter(name="arguments", display_name="Inputs", type=ParameterType.COLLECTION, required=False,
                          description="The tool's inputs. Values may use {{$node.x.y}} variables."),
        ],
        outputs=[
            NodeOutputField(name="result", display_name="Result (text)", type="string"),
            NodeOutputField(name="data", display_name="Result (structured)", type="object",
                            description="Parsed JSON result when the tool returns structured data"),
            NodeOutputField(name="tool", display_name="Tool name", type="string"),
        ],
    )

    async def execute(self, config: Dict[str, Any], input_data: Dict[str, Any], context: Any) -> Dict[str, Any]:
        self._require(config, "server", "tool")
        name, tool = str(config["server"]).strip(), str(config["tool"]).strip()

        server = getattr(context, "mcp_servers", {}).get(name)
        if server is None:
            raise NodeExecutionError(
                f"MCP server '{name}' is not connected. Add it on the Connections page.", self.definition.type
            )

        arguments = config.get("arguments") or {}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except ValueError:
                raise NodeExecutionError("The tool inputs are not valid JSON.", self.definition.type)
        if not isinstance(arguments, dict):
            raise NodeExecutionError("The tool inputs must be a set of name/value pairs.", self.definition.type)

        try:
            result = await remote.call_tool(server, tool, _coerce(arguments, config.get("argTypes") or {}))
        except McpError as exc:
            raise NodeExecutionError(str(exc), self.definition.type)
        if result["is_error"]:
            raise NodeExecutionError(f"'{tool}' reported an error: {result['text'] or 'no details'}", self.definition.type)
        return {"result": result["text"], "data": result["data"], "tool": tool}
