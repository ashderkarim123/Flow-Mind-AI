"""
POST /api/v1/ai/compare — comparative AI responses.

Sends one prompt to several models in parallel and returns each answer with
its latency and token usage. Reuses the workflow AI nodes, so any provider
that works in a workflow (including LocalLLM) works here.
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.v1.credentials import load_user_credentials_sync
from app.core.auth_dependency import require_permission
from executor.context import ExecutionContext
from nodes.base import NodeExecutionError
from nodes.registry import get_registry

router = APIRouter(prefix="/ai", tags=["AI"])

COMPARE_PROVIDERS = {"OpenAI", "ClaudeAI", "Gemini", "Groq", "LocalLLM"}


class CompareModel(BaseModel):
    provider: str = Field(..., description="Node type: OpenAI | ClaudeAI | Gemini | Groq | LocalLLM")
    model: str
    temperature: float = Field(0.7, ge=0, le=2)
    max_tokens: int = Field(1024, ge=1, le=16000)
    system_prompt: Optional[str] = None
    credential: Optional[str] = Field(None, description="Name of a saved credential holding the API key")


class CompareRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=20000)
    models: List[CompareModel] = Field(..., min_length=1, max_length=6)


async def _run_model(m: CompareModel, prompt: str, user_id: str, creds: Dict[str, str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {"provider": m.provider, "model": m.model, "status": "error",
                              "content": "", "tokens": 0, "latency_ms": 0, "error": None}
    registry = get_registry()
    if m.provider not in COMPARE_PROVIDERS or not registry.has(m.provider):
        result["error"] = f"Unsupported provider '{m.provider}'"
        return result

    config: Dict[str, Any] = {"prompt": prompt, "model": m.model, "temperature": m.temperature,
                              "max_tokens": m.max_tokens, "enable_tools": False}
    if m.system_prompt:
        config["system_prompt"] = m.system_prompt
    if m.credential:
        if m.credential not in creds:
            result["error"] = f"Saved credential '{m.credential}' not found"
            return result
        config["api_key"] = creds[m.credential]

    context = ExecutionContext(execution_id=str(uuid.uuid4()), workflow_id="ai-compare",
                               user_id=user_id, user_credentials=creds)
    t0 = time.monotonic()
    try:
        out = await registry.get(m.provider)().execute(config, {}, context)
        result.update(
            status="done",
            content=out.get("response") or "",
            model=out.get("model") or m.model,
            tokens=out.get("tokens_used") or (out.get("prompt_tokens") or 0) + (out.get("completion_tokens") or 0),
        )
    except NodeExecutionError as exc:
        result["error"] = str(exc)
    except Exception as exc:  # one bad provider must not sink the whole comparison
        result["error"] = f"Unexpected error: {exc!r}"
    result["latency_ms"] = round((time.monotonic() - t0) * 1000)
    return result


@router.post("/compare")
async def compare_models(req: CompareRequest, current_user: dict = Depends(require_permission("ai:use"))):
    """Run the same prompt through every requested model concurrently."""
    creds = load_user_credentials_sync(current_user["uid"])
    results = await asyncio.gather(*(_run_model(m, req.prompt, current_user["uid"], creds) for m in req.models))
    return {"prompt": req.prompt, "results": results}
