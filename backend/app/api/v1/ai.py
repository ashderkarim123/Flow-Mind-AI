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
from app.core.auth_dependency import has_permission, require_permission
from app.core.netguard import UnsafeURL, assert_safe_url
from app.core.security import rate_limit
from app.services import llm_service, workflow_digest, workflow_generator
from executor.context import ExecutionContext, plain_variables
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
                      [("openai", "OPENAI_API_KEY"), ("openrouter", "OPENROUTER_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY"),
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
    current_state: Optional[Dict[str, Any]] = None       # the canvas: {nodes, connections}
    variables: Optional[Dict[str, Any]] = None           # the workflow's variables
    last_run: Optional[Dict[str, Any]] = None            # the editor's last run: status, error, errorInfo, nodeLogs
    history: Optional[List[Dict[str, str]]] = None       # earlier turns: [{"role": "user"|"assistant", "content": "..."}]
    execution_id: Optional[str] = None                   # explain a past run (from the Executions page) instead of the canvas


GUIDE = (
    "You are the FlowMind AI workflow assistant for non-technical users. Answer briefly and in plain language, with short steps. "
    "Refer to steps by the names the user sees. When you mention a node, use its exact name from the catalog. "
    "To use data from an earlier step write {{$node.<id>.<output name>}} using only output names listed in the catalog; "
    "workflow variables are written {{$vars.<name>}}.\n"
    "You can see the user's workflow below. Secrets are hidden as ••••: never ask for or repeat a key or password. "
    "To explain a workflow, say what it does in order, in plain words, and point out anything risky or unfinished. "
    "To troubleshoot, start from 'Last run' and 'Possible problems', say what went wrong and why, and name the exact setting to change. "
    "The platform has safety nets you can recommend where they fit: retry if a step fails, a time limit for a step, carrying on after a "
    "failure, and a fallback value; failed runs also show on the dashboard alerts and the Executions page. "
    "If you are not sure, say so; do not invent settings or steps."
)


def _db():
    from app.services.firebase_service import firebase_service
    return firebase_service.db


def _load_execution(execution_id: str, user: dict) -> Dict[str, Any]:
    """A past run and its workflow, for 'explain this failure'. Someone else's run is a 404, as on the Executions page."""
    record = _db().collection("executions").document(execution_id).get()
    data = record.to_dict() if getattr(record, "exists", False) else None
    if not data or (data.get("userId") != user.get("uid") and not has_permission(user, "analytics:platform")):
        raise HTTPException(status_code=404, detail="Execution not found")
    workflow = _db().collection("workflows").document(data.get("workflowId") or "").get()
    wf = (workflow.to_dict() if getattr(workflow, "exists", False) else None) or {}
    logs = [{k: log.get(k) for k in ("nodeId", "nodeName", "nodeType", "status", "error", "errorInfo", "attempts", "executionTimeMs", "fallbackUsed")}
            for log in (data.get("nodeLogs") or [])]
    return {
        "state": {"name": wf.get("name") or data.get("workflowName"), "nodes": wf.get("nodes") or [], "edges": wf.get("edges") or []},
        "variables": plain_variables(wf.get("variables")),
        "last_run": {"status": data.get("status"), "error": data.get("error"), "errorInfo": data.get("errorInfo"), "nodeLogs": logs},
    }


def _history(turns: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
    valid = [{"role": t["role"], "content": str(t["content"])[:1500]} for t in (turns or [])
             if isinstance(t, dict) and t.get("role") in ("user", "assistant") and str(t.get("content") or "").strip()]
    return valid[-8:]


@router.post("/assist")
@rate_limit(requests_per_minute=20)
async def assist(request: Request, body: AssistRequest, user: dict = Depends(require_permission("ai:use"))):
    """Explain or troubleshoot a workflow: aware of the node catalog, the canvas, its variables and the last run."""
    state, variables, last_run = body.current_state, body.variables, body.last_run
    if body.execution_id:
        loaded = _load_execution(body.execution_id, user)
        state, variables, last_run = loaded["state"], loaded["variables"], loaded["last_run"]
    digest = workflow_digest.describe_workflow(state, get_registry(), variables, last_run) if (state or last_run) else None

    system = (GUIDE + "\n\nNODE CATALOG:\n" + workflow_generator.catalog_text(get_registry())
              + "\n\nTHE USER'S WORKFLOW:\n" + (digest["text"] if digest else "(no workflow is open)"))
    messages = [{"role": "system", "content": system}, *_history(body.history), {"role": "user", "content": body.question}]
    try:
        answer = await llm_service.chat(messages, temperature=0.4, max_tokens=1024)
        source = "model"
    except llm_service.LLMUnavailable as exc:
        if not digest:
            raise HTTPException(status_code=503, detail=str(exc))
        # No model reachable: still tell the user what we know, which needs no model
        answer = (workflow_digest.plain_explanation(digest, last_run)
                  + "\n\n(The AI model is not available right now, so this is a plain summary. " + str(exc) + ")")
        source = "summary"
    return {"answer": answer or "I couldn't come up with an answer — please rephrase the question.", "sources": [],
            "problems": digest["problems"] if digest else [], "source": source}
