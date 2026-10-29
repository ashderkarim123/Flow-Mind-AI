"""OpenAI — sends a prompt to OpenAI GPT models and returns the response.

Supports:
- Basic chat completions
- Database queries via MCP tools (Postgres, MongoDB, Pinecone)
- Dynamic tool calling (function calling)
"""

from __future__ import annotations
from typing import Any, Dict, List
import asyncio
import logging
import os
import re

import httpx

from ai.chat_loop import chat_with_tools, tool_message_content
from ai.mcp import remote
from ai.mcp.remote import McpError
from app.core.netguard import UnsafeURL, assert_safe_url

from nodes.base import BaseNode, NodeDefinition, NodeParameter, NodeOutputField, ParameterType, NodeExecutionError, SelectOption

logger = logging.getLogger(__name__)

MAX_TOOLS = 40  # small local models get confused by very long tool lists


def _names(value: Any) -> List[str]:
    """MCP server names from a list or a comma-separated string."""
    if isinstance(value, str):
        value = value.split(",")
    return [str(v).strip() for v in (value or []) if str(v).strip()]


def _function_name(server_slug: str, tool: str, taken: Dict[str, Any]) -> str:
    """Function name the model sees: server__tool, restricted to [A-Za-z0-9_-] and 64 chars, unique."""
    base = re.sub(r"[^A-Za-z0-9_-]", "_", f"{server_slug}__{tool}")[:64]
    name, n = base, 2
    while name in taken:
        name, n = f"{base[:60]}_{n}", n + 1
    return name


class OpenAI(BaseNode):
    definition = NodeDefinition(
        type="OpenAI",
        display_name="OpenAI",
        description=(
            "Send a prompt to OpenAI GPT models with optional database access via MCP tools. "
            "Models can query PostgreSQL, MongoDB, or Pinecone and use the results to generate responses."
        ),
        category="AI",
        icon="🤖",
        color="#10A37F",
        is_trigger=False,
        required_credentials=["openai_api_key"],
        parameters=[
            NodeParameter(
                name="prompt",
                display_name="Prompt",
                type=ParameterType.EXPRESSION,
                required=True,
                description="The prompt to send to the model. Supports {{$node.x.y}} expressions.",
                placeholder="Summarize the following: {{$node.n1.response_body}}",
            ),
            NodeParameter(
                name="system_prompt",
                display_name="System Prompt",
                type=ParameterType.STRING,
                required=False,
                default="You are a helpful assistant with access to databases. Use available tools to query data when needed.",
                description="Instructions that define the model's behavior.",
            ),
            NodeParameter(
                name="model",
                display_name="Model",
                type=ParameterType.OPTIONS,
                required=False,
                default="gpt-4.1-mini",
                options=[
                    SelectOption(value="gpt-4.1", label="GPT-4.1 (latest)"),
                    SelectOption(value="gpt-4.1-mini", label="GPT-4.1 Mini (recommended)"),
                    SelectOption(value="gpt-4.1-nano", label="GPT-4.1 Nano (fastest)"),
                    SelectOption(value="gpt-4o", label="GPT-4o"),
                    SelectOption(value="gpt-4o-mini", label="GPT-4o Mini"),
                    SelectOption(value="o4-mini", label="o4-mini (reasoning)"),
                    SelectOption(value="o3", label="o3 (advanced reasoning)"),
                ],
            ),
            NodeParameter(
                name="temperature",
                display_name="Temperature",
                type=ParameterType.NUMBER,
                required=False,
                default=0.7,
                min_value=0,
                max_value=2,
                description="Controls randomness. 0 = deterministic, 2 = very random.",
            ),
            NodeParameter(
                name="max_tokens",
                display_name="Max Tokens",
                type=ParameterType.NUMBER,
                required=False,
                default=1000,
                min_value=1,
                max_value=16000,
            ),
            NodeParameter(
                name="enable_tools",
                display_name="Enable Database Tools",
                type=ParameterType.BOOLEAN,
                required=False,
                default=True,
                description="Allow the model to query databases using MCP tools",
            ),
            NodeParameter(
                name="mcp_servers",
                display_name="MCP tools",
                type=ParameterType.STRING,
                required=False,
                description="Names of connected MCP servers whose tools the AI may use (Connections page). Comma-separated.",
            ),
            NodeParameter(
                name="api_key",
                display_name="API Key",
                type=ParameterType.CREDENTIAL,
                required=False,
                description="OpenAI API key. Leave blank to use the key from Credentials.",
                is_private=True,
            ),
        ],
        outputs=[
            NodeOutputField(name="response", display_name="Response Text", type="string"),
            NodeOutputField(name="model", display_name="Model Used", type="string"),
            NodeOutputField(name="tokens_used", display_name="Tokens Used", type="number"),
            NodeOutputField(name="finish_reason", display_name="Finish Reason", type="string"),
            NodeOutputField(name="prompt_tokens", display_name="Prompt Tokens", type="number"),
            NodeOutputField(name="completion_tokens", display_name="Completion Tokens", type="number"),
            NodeOutputField(name="tool_calls", display_name="Tool Calls Made", type="array", 
                          description="List of tools called by the model"),
            NodeOutputField(name="database_results", display_name="Database Results", type="object",
                          description="Results from database queries"),
        ],
    )

    async def execute(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any],
        context: Any,
    ) -> Dict[str, Any]:
        self._require(config, "prompt")

        model = config.get("model", "gpt-4.1-mini")
        api_key = self._api_key(config, context)
        url = f"{self._base_url(config)}/chat/completions"
        tools, call_tool, db_tool_names = await self._tools(config, context)
        messages = [
            {"role": "system", "content": config.get("system_prompt", "You are a helpful assistant with access to databases.")},
            {"role": "user", "content": str(config["prompt"])},
        ]

        try:
            out = await chat_with_tools(
                url=url, api_key=api_key, model=model, messages=messages,
                temperature=float(config.get("temperature", 0.7)), max_tokens=int(config.get("max_tokens", 1000)),
                timeout=self.TIMEOUT, tools=tools, call_tool=call_tool, label=self.definition.display_name,
            )
        except NodeExecutionError as exc:
            raise NodeExecutionError(self._explain(str(exc), model), self.definition.type)
        except httpx.ConnectError:
            raise NodeExecutionError(self._unreachable(url), self.definition.type)
        except httpx.TimeoutException:
            raise NodeExecutionError(
                f"{self.definition.display_name} did not answer within {self.TIMEOUT:.0f}s.", self.definition.type
            )
        except Exception as exc:
            logger.exception("%s execution failed", self.definition.type)
            raise NodeExecutionError(f"{self.definition.display_name} request failed: {exc!r}", self.definition.type)

        return {
            "response": out["response"],
            "model": out["model"],
            "tokens_used": out["prompt_tokens"] + out["completion_tokens"],
            "finish_reason": out["finish_reason"],
            "prompt_tokens": out["prompt_tokens"],
            "completion_tokens": out["completion_tokens"],
            "tool_calls": out["tool_calls"],
            "database_results": {c["name"]: c["result"] for c in out["tool_calls"] if c["name"] in db_tool_names},
        }

    # ------------------------------------------------------------------
    # Tools: database tools (built in) + tools of connected MCP servers
    # ------------------------------------------------------------------

    async def _tools(self, config: Dict[str, Any], context: Any):
        tools: List[Dict[str, Any]] = []
        db_names: set = set()
        routes: Dict[str, tuple] = {}   # function name shown to the model → (server, real tool name)

        if config.get("enable_tools", True):
            db_client = context.get_mcp_client()
            if db_client:
                db_tools = db_client.get_available_tools()
                tools += db_tools
                db_names = {t["function"]["name"] for t in db_tools}

        for server_name in _names(config.get("mcp_servers")):
            server = getattr(context, "mcp_servers", {}).get(server_name)
            if server is None:
                raise NodeExecutionError(
                    f"MCP server '{server_name}' is not connected. Add it on the Connections page.", self.definition.type
                )
            try:
                server_tools = await remote.list_tools(server)
            except McpError as exc:
                raise NodeExecutionError(str(exc), self.definition.type)
            for tool in server_tools:
                fn = _function_name(remote.slug(server_name), tool["name"], routes)
                routes[fn] = (server, tool["name"])
                tools.append({"type": "function", "function": {
                    "name": fn,
                    "description": (tool["description"] or tool["name"])[:1000],
                    "parameters": tool["inputSchema"] or {"type": "object", "properties": {}},
                }})
            if len(tools) > MAX_TOOLS:
                logger.warning("%d tools offered to the model; small models work best with fewer", len(tools))

        async def call_tool(name: str, args: Dict[str, Any]) -> Any:
            if name in routes:
                server, tool_name = routes[name]
                result = await remote.call_tool(server, tool_name, args)
                text = result["text"] or tool_message_content(result["data"])
                return f"Error: {text}" if result["is_error"] else text
            db_client = context.get_mcp_client()
            if not db_client:
                raise NodeExecutionError("The model asked for a tool that is not available.", self.definition.type)
            return await db_client.call_tool(name, args)

        return tools, call_tool, db_names

    # ------------------------------------------------------------------
    # Provider hooks — overridden by OpenAI-compatible providers below
    # ------------------------------------------------------------------

    TIMEOUT = 60

    def _base_url(self, config: Dict[str, Any]) -> str:
        return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    def _explain(self, message: str, model: str) -> str:
        """Hook: add provider-specific advice to an API error."""
        return message

    def _unreachable(self, url: str) -> str:
        return f"Could not reach {self.definition.display_name} at {url}. Check the network connection."

    def _api_key(self, config: Dict[str, Any], context: Any) -> str:
        api_key = config.get("api_key") or context.get_credential("openai_api_key", "api_key", "")
        if not api_key:
            raise NodeExecutionError(
                "OpenAI API key is required. Set it in the node config, in Credentials, "
                "or as OPENAI_API_KEY on the server.",
                self.definition.type,
            )
        return api_key


class LocalLLM(OpenAI):
    """Self-hosted model through any OpenAI-compatible server (Ollama, LM Studio, vLLM).

    No API key or internet access to an AI provider is needed — point
    LOCAL_LLM_BASE_URL at the machine running the model.
    """

    definition = NodeDefinition(
        type="LocalLLM",
        display_name="Local LLM (Ollama)",
        description=(
            "Run a self-hosted open model (Llama, Qwen, Mistral, Gemma…) through Ollama or any "
            "OpenAI-compatible server. No API key or paid provider needed."
        ),
        category="AI",
        icon="🦙",
        color="#111827",
        is_trigger=False,
        required_credentials=[],
        parameters=[
            NodeParameter(
                name="prompt",
                display_name="Prompt",
                type=ParameterType.EXPRESSION,
                required=True,
                placeholder="Summarize the following: {{$node.n1.response_body}}",
            ),
            NodeParameter(
                name="system_prompt",
                display_name="System Prompt",
                type=ParameterType.STRING,
                required=False,
                default="You are a helpful assistant.",
            ),
            NodeParameter(
                name="model",
                display_name="Model",
                type=ParameterType.STRING,
                required=False,
                default=os.getenv("LOCAL_LLM_MODEL", "llama3.2"),
                description="Model name as pulled on the server, e.g. `ollama pull llama3.2`.",
            ),
            NodeParameter(
                name="base_url",
                display_name="Server URL",
                type=ParameterType.STRING,
                required=False,
                default="",
                placeholder="http://localhost:11434/v1",
                description="Leave blank to use LOCAL_LLM_BASE_URL from the server environment.",
            ),
            NodeParameter(name="temperature", display_name="Temperature", type=ParameterType.NUMBER,
                          required=False, default=0.7, min_value=0, max_value=2),
            NodeParameter(name="max_tokens", display_name="Max Tokens", type=ParameterType.NUMBER,
                          required=False, default=1000, min_value=1, max_value=16000),
            NodeParameter(
                name="mcp_servers",
                display_name="MCP tools",
                type=ParameterType.STRING,
                required=False,
                description="Names of connected MCP servers whose tools the AI may use (Connections page). "
                            "Needs a model with tool support, e.g. qwen2.5/qwen3, llama3.1+, mistral-nemo.",
            ),
        ],
        outputs=OpenAI.definition.outputs,
    )

    TIMEOUT = 300  # CPU-only servers can take minutes for long answers

    async def execute(self, config: Dict[str, Any], input_data: Dict[str, Any], context: Any) -> Dict[str, Any]:
        custom = (config.get("base_url") or "").strip()
        if custom and custom.rstrip("/") != os.getenv("LOCAL_LLM_BASE_URL", "").rstrip("/"):
            # A URL typed into the node (not the operator-configured one) must pass the SSRF guard
            try:
                await asyncio.to_thread(assert_safe_url, custom)
            except UnsafeURL as exc:
                raise NodeExecutionError(str(exc), self.definition.type)
        return await super().execute({
            **config,
            "model": config.get("model") or os.getenv("LOCAL_LLM_MODEL", "llama3.2"),
            # Small local models handle tool calling poorly — keep it opt-in
            "enable_tools": config.get("enable_tools", False),
        }, input_data, context)

    def _base_url(self, config: Dict[str, Any]) -> str:
        return (config.get("base_url") or os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")).rstrip("/")

    def _api_key(self, config: Dict[str, Any], context: Any) -> str:
        return config.get("api_key") or os.getenv("LOCAL_LLM_API_KEY", "ollama")  # Ollama ignores the key

    def _unreachable(self, url: str) -> str:
        return (f"Can't reach the local AI server at {url}. Make sure Ollama is running "
                f"(start it with `ollama serve`) and that the address is right.")

    def _explain(self, message: str, model: str) -> str:
        if "not found" in message.lower():
            return f"{message} — install the model first with `ollama pull {model}`."
        if "does not support tools" in message.lower():
            return f"{message} — pick a model with tool support (e.g. qwen2.5, qwen3, llama3.1) or remove the MCP tools."
        return message
