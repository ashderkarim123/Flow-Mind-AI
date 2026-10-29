"""
The platform's own AI helper (workflow generator + builder assistant).

Which model it uses is an operator decision, set in the environment — so a fully offline install
just uses Ollama and never touches a cloud API:

  ASSISTANT_PROVIDER = auto (default) | local | openai | groq | gemini | custom
  ASSISTANT_MODEL    overrides the provider's default model
  ASSISTANT_BASE_URL / ASSISTANT_API_KEY   for provider=custom (any OpenAI-compatible API)

`auto` picks the first cloud provider that has an API key (OPENAI_API_KEY, GROQ_API_KEY,
GEMINI_API_KEY) and otherwise the local Ollama server (LOCAL_LLM_BASE_URL).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx


class LLMUnavailable(Exception):
    """The assistant model cannot be used right now; the message says what to do about it."""


@dataclass
class Endpoint:
    provider: str
    base_url: str
    api_key: str
    model: str

    @property
    def is_local(self) -> bool:
        return self.provider == "local"


_CLOUD = {   # provider → (base url, key env var, default model)
    "openai": (os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"), "OPENAI_API_KEY", "gpt-4.1-mini"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "llama-3.3-70b-versatile"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "gemini-2.0-flash"),
}


def local_base_url() -> str:
    return os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")


def endpoint() -> Endpoint:
    provider = os.getenv("ASSISTANT_PROVIDER", "auto").strip().lower()
    if provider == "auto":
        provider = next((p for p, (_, key_env, _) in _CLOUD.items() if os.getenv(key_env)), "local")
    model_override = os.getenv("ASSISTANT_MODEL", "").strip()

    if provider in _CLOUD:
        base, key_env, default_model = _CLOUD[provider]
        key = os.getenv(key_env, "")
        if not key:
            raise LLMUnavailable(f"The AI assistant is set to '{provider}' but {key_env} is not configured on the server.")
        return Endpoint(provider, base.rstrip("/"), key, model_override or default_model)
    if provider == "custom":
        base = os.getenv("ASSISTANT_BASE_URL", "").rstrip("/")
        if not base:
            raise LLMUnavailable("ASSISTANT_PROVIDER=custom needs ASSISTANT_BASE_URL.")
        return Endpoint("custom", base, os.getenv("ASSISTANT_API_KEY", "none"), model_override or os.getenv("LOCAL_LLM_MODEL", "llama3.2"))
    if provider != "local":
        raise LLMUnavailable(f"Unknown ASSISTANT_PROVIDER '{provider}'.")
    return Endpoint("local", local_base_url(), os.getenv("LOCAL_LLM_API_KEY", "ollama"),
                    model_override or os.getenv("LOCAL_LLM_MODEL", "llama3.2"))


def _explain_http_error(ep: Endpoint, status: int, body: str) -> str:
    try:
        message = json.loads(body)["error"]
        message = message.get("message", body) if isinstance(message, dict) else str(message)
    except (ValueError, KeyError, TypeError):
        message = body[:200]
    if ep.is_local and "not found" in message.lower():
        return f"The local model '{ep.model}' is not installed. Install it with: ollama pull {ep.model}"
    if status in (401, 403):
        return f"The {ep.provider} API rejected the server's API key."
    if status == 429:
        return f"The {ep.provider} API is rate-limiting requests — try again in a moment."
    return f"The AI model returned an error ({status}): {message}"


async def chat(messages: List[Dict[str, str]], *, json_mode: bool = False, temperature: float = 0.2,
               max_tokens: int = 3000, ep: Optional[Endpoint] = None) -> str:
    """One chat completion → the assistant's text."""
    ep = ep or endpoint()
    body: Dict[str, Any] = {"model": ep.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {ep.api_key}", "Content-Type": "application/json"}
    url = f"{ep.base_url}/chat/completions"
    timeout = 300 if ep.is_local else 90   # CPU-only local models can take minutes

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=body)
            if json_mode and response.status_code == 400:   # a server without JSON mode: ask in plain text
                body.pop("response_format")
                response = await client.post(url, headers=headers, json=body)
    except httpx.ConnectError:
        hint = " Start Ollama with `ollama serve`." if ep.is_local else ""
        raise LLMUnavailable(f"Can't reach the AI model server at {ep.base_url}.{hint}")
    except httpx.TimeoutException:
        raise LLMUnavailable(f"The AI model did not answer within {timeout}s. A smaller model may be faster.")

    if response.status_code >= 400:
        raise LLMUnavailable(_explain_http_error(ep, response.status_code, response.text))
    try:
        return response.json()["choices"][0]["message"]["content"] or ""
    except (ValueError, KeyError, IndexError, TypeError):
        raise LLMUnavailable("The AI model returned an answer in an unexpected format.")


def extract_json(text: str) -> Dict[str, Any]:
    """Pull a JSON object out of a model reply (handles ```json fences and chatter around it)."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    try:
        value = json.loads(text)
    except ValueError:
        start = text.find("{")
        if start < 0:
            raise ValueError("no JSON object in the reply")
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    value = json.loads(text[start:i + 1])
                    break
        else:
            raise ValueError("the JSON object in the reply is incomplete")
    if not isinstance(value, dict):
        raise ValueError("the reply is not a JSON object")
    return value
