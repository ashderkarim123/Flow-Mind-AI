"""
Chat-completions agent loop for OpenAI-compatible APIs (OpenAI, Ollama, LM Studio, vLLM, Groq…).

The model may answer directly or ask to call tools (database tools, MCP server tools). We run the
requested tools, feed the results back and repeat until the model gives a final answer or the
round limit is hit — then it is asked once more *without* tools so a final answer is guaranteed.
Token usage is summed over all rounds.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable, Dict, List

import httpx

from nodes.base import NodeExecutionError

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6

ToolCaller = Callable[[str, Dict[str, Any]], Awaitable[Any]]


def tool_message_content(result: Any) -> str:
    """What the model is shown for a tool result: plain text stays text, structures become JSON."""
    return result if isinstance(result, str) else json.dumps(result, default=str)


async def _post(client: httpx.AsyncClient, url: str, api_key: str, body: Dict[str, Any], label: str) -> Dict[str, Any]:
    response = await client.post(
        url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=body
    )
    try:
        data = response.json()
    except ValueError:
        raise NodeExecutionError(f"{label} returned an unreadable response (HTTP {response.status_code}).", label)
    if "error" in data:
        err = data["error"]
        raise NodeExecutionError(f"{label} API error: {err.get('message', 'Unknown error') if isinstance(err, dict) else err}", label)
    if not data.get("choices"):
        raise NodeExecutionError(f"{label} returned no answer (HTTP {response.status_code}).", label)
    return data


async def chat_with_tools(
    *,
    url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
    timeout: float,
    tools: List[Dict[str, Any]],
    call_tool: ToolCaller,
    label: str,
) -> Dict[str, Any]:
    """Run the conversation to a final answer. `messages` is extended in place."""
    prompt_tokens = completion_tokens = 0
    calls_made: List[Dict[str, Any]] = []
    data: Dict[str, Any] = {}
    choice: Dict[str, Any] = {}

    async with httpx.AsyncClient(timeout=timeout) as client:
        for round_no in range(MAX_TOOL_ROUNDS + 1):
            body: Dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
            if tools and round_no < MAX_TOOL_ROUNDS:
                body["tools"], body["tool_choice"] = tools, "auto"

            data = await _post(client, url, api_key, body, label)
            usage = data.get("usage") or {}
            prompt_tokens += usage.get("prompt_tokens", 0)
            completion_tokens += usage.get("completion_tokens", 0)
            choice = data["choices"][0]
            message = choice.get("message") or {}
            requested = message.get("tool_calls") or []
            if not requested or "tools" not in body:
                break

            logger.info("🔧 %s requested %d tool call(s) (round %d)", label, len(requested), round_no + 1)
            messages.append(message)
            for call in requested:
                name = call["function"]["name"]
                raw_args = call["function"].get("arguments") or "{}"
                args: Dict[str, Any] = {}
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                except (ValueError, TypeError):
                    result: Any = {"error": "The tool arguments were not valid JSON."}
                else:
                    try:
                        result = await call_tool(name, args)
                    except Exception as exc:  # a failing tool is reported to the model, not fatal
                        result = {"error": str(exc)}
                calls_made.append({"id": call.get("id"), "name": name, "arguments": args, "result": result})
                messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": tool_message_content(result)})

    return {
        "response": (choice.get("message") or {}).get("content") or "",
        "model": data.get("model", model),
        "finish_reason": choice.get("finish_reason", ""),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tool_calls": calls_made,
    }
