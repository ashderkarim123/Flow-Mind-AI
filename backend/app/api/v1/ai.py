"""
AI endpoints.

  POST /ai/compare            comparative responses — one prompt, several models in parallel
  GET  /ai/status             which AI is configured/reachable (cloud keys, local Ollama + its models)
  GET  /ai/local-models       models installed on the local server (fills the Local LLM model picker)
  POST /ai/generate-workflow  plain-English description -> a validated workflow draft
  POST /ai/assist             the builder assistant (answers questions about building workflows)

The compare endpoint reuses the workflow AI nodes, so any provider that works in a workflow
(including LocalLLM) works there. The generator and the assistant use the model chosen by the
operator (ASSISTANT_PROVIDER — see app/services/llm_service.py), which can be fully local.
"""

import asyncio
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.v1.credentials import load_user_credentials_sync
from app.core.auth_dependency import require_permission
from app.core.netguard import UnsafeURL, assert_safe_url
from app.core.security import rate_limit
from app.services import llm_service, workflow_generator
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


# ---------------------------------------------------------------------------
# Local model server (Ollama / LM Studio / vLLM)
# ---------------------------------------------------------------------------

async def _local_models(base_url: Optional[str]) -> Dict[str, Any]:
    """Ask the OpenAI-compatible server which models it has (GET /models). Never raises."""
    default = llm_service.local_base_url()
    url = (base_url or default).rstrip("/")
    result: Dict[str, Any] = {"baseUrl": url, "reachable": False, "models": [], "error": None}
    if url != default:   # an address typed by a user must pass the SSRF guard
        try:
            await asyncio.to_thread(assert_safe_url, url)
        except UnsafeURL as exc:
            result["error"] = str(exc)
            return result
    try:
        headers = {"Authorization": f"Bearer {os.getenv('LOCAL_LLM_API_KEY', 'ollama')}"}
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{url}/models", headers=headers)
        response.raise_for_status()
        result["models"] = sorted(m["id"] for m in response.json().get("data", []))
        result["reachable"] = True
    except httpx.ConnectError:
        result["error"] = f"Can't reach a model server at {url}. Start Ollama with `ollama serve`."
    except Exception as exc:
        result["error"] = f"The server at {url} did not answer as expected: {exc}"
    return result


@router.get("/local-models")
async def local_models(base_url: Optional[str] = None, user: dict = Depends(require_permission("workflow:read"))):
    return await _local_models(base_url)


@router.get("/status")
async def ai_status(user: dict = Depends(require_permission("workflow:read"))):
    """Everything the Connections page needs: what AI is available and what is missing."""
    local = await _local_models(None)
    assistant: Dict[str, Any] = {"provider": None, "model": None, "ready": False, "problem": None}
    try:
        ep = llm_service.endpoint()
        assistant.update(provider=ep.provider, model=ep.model, ready=True)
        if ep.is_local:
            installed = {m.split(":")[0] for m in local["models"]} | set(local["models"])
            if not local["reachable"]:
                assistant.update(ready=False, problem=local["error"])
            elif ep.model not in installed and ep.model.split(":")[0] not in installed:
                assistant.update(ready=False, problem=f"The model '{ep.model}' is not installed. Run: ollama pull {ep.model}")
    except llm_service.LLMUnavailable as exc:
        assistant["problem"] = str(exc)

    from ai.mcp import remote
    return {
        "assistant": assistant,
        "local": local,
        "cloudKeys": {name: bool(os.getenv(env)) for name, env in
                      [("openai", "OPENAI_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY"),
                       ("gemini", "GEMINI_API_KEY"), ("groq", "GROQ_API_KEY")]},
        "mcp": {"stdioEnabled": remote.stdio_allowed()},
    }


# ---------------------------------------------------------------------------
# Workflow generator + builder assistant
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=workflow_generator.MAX_PROMPT_CHARS + 500)


@router.post("/generate-workflow")
@rate_limit(requests_per_minute=10)
async def generate_workflow(request: Request, body: GenerateRequest, user: dict = Depends(require_permission("ai:use"))):
    """Describe an automation in plain English → a draft workflow (not saved) + what is left to fill in."""
    try:
        return await workflow_generator.generate(body.prompt, get_registry())
    except workflow_generator.GenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except llm_service.LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


class AssistRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    current_state: Optional[Dict[str, Any]] = None


@router.post("/assist")
@rate_limit(requests_per_minute=20)
async def assist(request: Request, body: AssistRequest, user: dict = Depends(require_permission("ai:use"))):
    """Answer a question about building workflows, aware of the real node catalog and the open canvas."""
    state = ""
    if body.current_state:
        state = "\n\nThe user's current workflow on the canvas:\n" + json.dumps(body.current_state, default=str)[:6000]
    system = (
        "You are the FlowMind AI workflow assistant for non-technical users. Answer briefly and in plain language, "
        "with short steps. When you mention a node, use its exact name from the catalog. To use data from an earlier "
        "step write {{$node.<id>.<output name>}} using only output names listed in the catalog.\n\nNODE CATALOG:\n"
        + workflow_generator.catalog_text(get_registry()) + state
    )
    try:
        answer = await llm_service.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": body.question}],
            temperature=0.4, max_tokens=1024,
        )
    except llm_service.LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"answer": answer or "I couldn't come up with an answer — please rephrase the question.", "sources": []}
