"""OpenAI — sends a prompt to OpenAI GPT models and returns the response.

Supports:
- Basic chat completions
- Database queries via MCP tools (Postgres, MongoDB, Pinecone)
- Dynamic tool calling (function calling)
"""

from __future__ import annotations
from typing import Any, Dict
import json
import logging
import os

from nodes.base import BaseNode, NodeDefinition, NodeParameter, NodeOutputField, ParameterType, NodeExecutionError, SelectOption

logger = logging.getLogger(__name__)


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

        prompt = str(config["prompt"])
        system_prompt = config.get("system_prompt", "You are a helpful assistant with access to databases.")
        model = config.get("model", "gpt-4.1-mini")
        temperature = float(config.get("temperature", 0.7))
        max_tokens = int(config.get("max_tokens", 1000))
        enable_tools = config.get("enable_tools", True)
        api_key = self._api_key(config, context)
        url = f"{self._base_url(config)}/chat/completions"

        try:
            import httpx

            # Build tools if enabled
            tools = []
            if enable_tools:
                mcp_client = context.get_mcp_client()
                if mcp_client:
                    tools = mcp_client.get_available_tools()
                    logger.info("🛠️  OpenAI: Registering %d MCP tools", len(tools))

            # Initial request to OpenAI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            request_body = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if tools:
                request_body["tools"] = tools
                request_body["tool_choice"] = "auto"  # Let OpenAI decide whether to use tools

            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                )
                data = response.json()

            if "error" in data:
                err = data["error"]
                msg = err.get("message", "Unknown error") if isinstance(err, dict) else str(err)
                raise NodeExecutionError(
                    f"{self.definition.display_name} API error: {msg}",
                    self.definition.type,
                )

            choice = data["choices"][0]
            finish_reason = choice.get("finish_reason", "")
            tool_calls_made = []
            database_results = {}

            # Handle tool calls if the model chose to use them
            if finish_reason == "tool_calls" and "tool_calls" in choice.get("message", {}):
                tool_calls = choice["message"]["tool_calls"]
                logger.info("🔧 OpenAI calling %d tools", len(tool_calls))

                mcp_client = context.get_mcp_client()
                if not mcp_client:
                    raise NodeExecutionError(
                        "Tool calling requested but MCP client not available",
                        self.definition.type,
                    )

                # Execute each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    arguments = tool_call["function"]["arguments"]

                    try:
                        if isinstance(arguments, str):
                            arguments = json.loads(arguments)
                        logger.info("▶ Executing tool: %s with args: %s", tool_name, arguments)
                        result = await mcp_client.call_tool(tool_name, arguments)
                    except json.JSONDecodeError:
                        logger.error("Failed to parse tool arguments: %s", arguments)
                        result = {"error": "Invalid tool arguments"}
                    database_results[tool_name] = result

                    # Every tool_call in the assistant message needs a matching tool reply
                    tool_calls_made.append({
                        "id": tool_call.get("id"),
                        "name": tool_name,
                        "arguments": arguments,
                        "result": result,
                    })

                # If tools were called, do another request with the results
                if tool_calls_made:
                    messages.append(choice["message"])
                    for tool_call_info in tool_calls_made:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_info["id"],
                            "content": json.dumps(tool_call_info["result"], default=str),
                        })

                    # Request follow-up response with the tool results
                    async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                        response = await client.post(
                            url,
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": model,
                                "messages": messages,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                            },
                        )
                        data = response.json()

                    if "error" in data:
                        logger.error("OpenAI follow-up request failed: %s", data["error"])
                    else:
                        choice = data["choices"][0]
                        finish_reason = choice.get("finish_reason", "")

            usage = data.get("usage", {})
            response_text = choice.get("message", {}).get("content", "")

            return {
                "response": response_text,
                "model": data.get("model", model),
                "tokens_used": usage.get("total_tokens", 0),
                "finish_reason": finish_reason,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "tool_calls": tool_calls_made,
                "database_results": database_results,
            }

        except NodeExecutionError:
            raise
        except Exception as exc:
            logger.exception("%s execution failed", self.definition.type)
            raise NodeExecutionError(
                f"{self.definition.display_name} request failed: {exc!r}", self.definition.type
            )

    # ------------------------------------------------------------------
    # Provider hooks — overridden by OpenAI-compatible providers below
    # ------------------------------------------------------------------

    TIMEOUT = 60

    def _base_url(self, config: Dict[str, Any]) -> str:
        return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

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
        ],
        outputs=OpenAI.definition.outputs,
    )

    TIMEOUT = 300  # CPU-only servers can take minutes for long answers

    async def execute(self, config: Dict[str, Any], input_data: Dict[str, Any], context: Any) -> Dict[str, Any]:
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
