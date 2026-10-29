"""
Plain-English → workflow.

An LLM drafts the workflow as JSON from a compact catalog of the platform's nodes. Models make
mistakes (invented node types, missing connections, no trigger), so the draft is *repaired and
validated* here against the real node registry before anyone sees it, and the result lists what
the person still has to fill in. The draft is returned, never saved — the user reviews it first.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.services import llm_service
from nodes.base import NodeDefinition, ParameterType

logger = logging.getLogger(__name__)

# registry category → the editor's NodeCategory enum values
CATEGORY_MAP = {"Triggers": "trigger", "Actions": "action", "Logic": "logic", "Data": "data",
                "AI": "ai_ml", "Integrations": "action", "Databases": "action"}

MAX_PROMPT_CHARS = 2000
MAX_NODES = 30
PREFERRED_AI = {"local": "LocalLLM", "custom": "LocalLLM", "openai": "OpenAI", "groq": "Groq", "gemini": "Gemini"}
REF_RE = re.compile(r"\{\{\s*\$node\.([^.}\s]+)\.([^}\s]+?)\s*\}\}")


class GenerationError(Exception):
    """The draft could not be produced; the message is for the person who asked."""


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def catalog_text(registry) -> str:
    """One line per node: type, what it does, its parameters (* = required) and outputs."""
    lines = []
    for d in registry.all_definitions():
        params = []
        for p in d.parameters:
            if p.type == ParameterType.CREDENTIAL:
                continue          # keys come from saved Credentials or the server, never from the draft
            options = ""
            if p.options:
                shown = [o.value for o in p.options][:8]
                options = "(" + "/".join(shown) + ("/…" if len(p.options) > 8 else "") + ")"
            params.append(f"{p.name}{'*' if p.required else ''}{options}")
        lines.append(
            f"- {d.type} [{d.category}]{' TRIGGER' if d.is_trigger else ''}: {d.description.split('. ')[0][:100]}"
            f" | params: {', '.join(params) or 'none'} | outputs: {','.join(o.name for o in d.outputs) or 'none'}"
        )
    return "\n".join(lines)


def system_prompt(registry, preferred_ai: str) -> str:
    return f"""You design automation workflows for a no-code platform. Reply with ONE JSON object and nothing else.

Format:
{{"name": "short title", "description": "one sentence",
 "nodes": [{{"id": "n1", "type": "<node type>", "name": "<short label a non-technical person understands>", "config": {{}}}}],
 "edges": [{{"source": "n1", "target": "n2"}}]}}

Rules:
- Use ONLY node types from the catalog below, spelled exactly. Start with exactly one TRIGGER node.
- For any AI step use the node type "{preferred_ai}" and put the instructions in its "prompt".
- "config" keys must be the parameter names from the catalog (* = required). Leave out anything you cannot know.
  Never invent e-mail addresses, URLs, IDs or secrets — use an empty string "" for them.
- To use data from an earlier step write {{{{$node.<id>.<output name>}}}}, e.g. {{{{$node.n2.response}}}}.
  Data sent to a Webhook trigger is {{{{$trigger.body}}}}. Use only output names listed in the catalog.
- Cron for Schedule has 5 fields, e.g. "0 9 * * *" = every day at 9:00.
- IfCondition has two outgoing edges with "condition": "true" and "condition": "false".
- Keep it as short as the request allows (usually 2-6 nodes).

Example — "when a webhook arrives, summarise the text with AI and post it to Slack #news":
{{"name": "Summarise and post", "description": "Summarises incoming text and posts it to Slack.",
 "nodes": [{{"id": "n1", "type": "Webhook", "name": "Receive text", "config": {{}}}},
           {{"id": "n2", "type": "{preferred_ai}", "name": "Summarise", "config": {{"prompt": "Summarise in two sentences: {{{{$trigger.body}}}}"}}}},
           {{"id": "n3", "type": "SlackMessage", "name": "Post to Slack", "config": {{"channel": "#news", "message": "{{{{$node.n2.response}}}}"}}}}],
 "edges": [{{"source": "n1", "target": "n2"}}, {{"source": "n2", "target": "n3"}}]}}

CATALOG:
{catalog_text(registry)}"""


# ---------------------------------------------------------------------------
# Repair + validate
# ---------------------------------------------------------------------------

def _coerce(value: Any, kind: ParameterType) -> Any:
    if isinstance(value, str) and kind in (ParameterType.NUMBER, ParameterType.BOOLEAN):
        try:
            if kind == ParameterType.NUMBER:
                number = float(value)
                return int(number) if number.is_integer() else number
            return value.strip().lower() in {"1", "true", "yes", "on"}
        except ValueError:
            return value
    return value


def _valid_cron(expr: str) -> bool:
    if len(expr.split()) != 5:
        return False
    try:
        from croniter import croniter
        return croniter.is_valid(expr)
    except ImportError:
        return True


def _layout(ids: List[str], edges: List[Tuple[str, str]]) -> Dict[str, Dict[str, int]]:
    """Left-to-right columns by longest path from the start; rows by order within a column."""
    depth = {i: 0 for i in ids}
    for _ in range(len(ids)):              # relax edges; bounded so a cycle cannot loop forever
        changed = False
        for src, dst in edges:
            if depth[dst] < depth[src] + 1 and depth[src] + 1 < len(ids):
                depth[dst], changed = depth[src] + 1, True
        if not changed:
            break
    rows: Dict[int, int] = {}
    positions = {}
    for node_id in ids:
        row = rows.get(depth[node_id], 0)
        rows[depth[node_id]] = row + 1
        positions[node_id] = {"x": 80 + depth[node_id] * 320, "y": 100 + row * 170}
    return positions


def build_workflow(draft: Dict[str, Any], registry, preferred_ai: str = "LocalLLM") -> Dict[str, Any]:
    """Repair a model's draft → {name, description, nodes, edges, steps, warnings, todo}."""
    warnings: List[str] = []
    by_lower = {t.lower(): t for t in registry.all_types()}
    definitions: Dict[str, NodeDefinition] = {}

    # --- nodes ---------------------------------------------------------------------------
    nodes: List[Dict[str, Any]] = []
    id_map: Dict[str, str] = {}
    seen_triggers = 0
    for index, raw in enumerate(draft.get("nodes") or []):
        if not isinstance(raw, dict):
            continue
        raw_type = str(raw.get("type") or "").strip()
        node_type = by_lower.get(raw_type.lower().replace(" ", "").replace("_", ""), by_lower.get(raw_type.lower()))
        if node_type is None:
            warnings.append(f"Step '{raw.get('name') or raw_type or index + 1}' used an unknown action ('{raw_type}') and was removed.")
            continue
        d = definitions.setdefault(node_type, registry.get(node_type).definition)
        if d.is_trigger:
            seen_triggers += 1
            if seen_triggers > 1:
                warnings.append(f"Only one trigger is allowed — '{raw.get('name') or node_type}' was removed.")
                continue
        if len(nodes) >= MAX_NODES:
            warnings.append(f"The workflow was cut off at {MAX_NODES} steps.")
            break

        wanted = str(raw.get("id") or f"n{index + 1}")
        node_id, n = wanted, 2
        while any(x["id"] == node_id for x in nodes):
            node_id, n = f"{wanted}_{n}", n + 1
        id_map[wanted] = node_id

        params = {p.name: p for p in d.parameters}
        given = raw.get("config") if isinstance(raw.get("config"), dict) else {}
        config = {k: _coerce(v, params[k].type) for k, v in given.items() if k in params and v is not None}
        for p in d.parameters:                       # fill sensible defaults so the editor opens fully populated
            if p.name not in config and p.default not in (None, ""):
                config[p.name] = p.default
        if node_type == "Schedule" and not _valid_cron(str(config.get("cron", ""))):
            warnings.append("The schedule was not understood, so it was set to every day at 9:00 — please check it.")
            config["cron"] = "0 9 * * *"
        nodes.append({"id": node_id, "type": node_type, "name": str(raw.get("name") or d.display_name)[:60], "config": config})

    if not nodes:
        raise ValueError("it contained no usable steps")   # a ValueError is retried by generate()

    # --- edges ---------------------------------------------------------------------------
    ids = [n["id"] for n in nodes]
    edges: List[Dict[str, Any]] = []
    for raw in draft.get("edges") or []:
        if not isinstance(raw, dict):
            continue
        src = id_map.get(str(raw.get("source") or raw.get("from") or ""))
        dst = id_map.get(str(raw.get("target") or raw.get("to") or ""))
        if not src or not dst or src == dst or any(e["source"] == src and e["target"] == dst for e in edges):
            continue
        cond = str(raw.get("condition") or "").lower()
        edges.append({"source": src, "target": dst, "condition": cond if cond in ("true", "false") else None})
    if not edges and len(nodes) > 1:                 # models often forget the connections: chain in order
        edges = [{"source": a, "target": b, "condition": None} for a, b in zip(ids, ids[1:])]
        warnings.append("The AI did not connect the steps, so they were chained in order — please check the flow.")

    # --- a workflow must start with a trigger ---------------------------------------------
    if not any(definitions[n["type"]].is_trigger for n in nodes) and registry.has("ManualTrigger"):
        incoming = {e["target"] for e in edges}
        roots = [i for i in ids if i not in incoming] or ids[:1]
        nodes.insert(0, {"id": "trigger", "type": "ManualTrigger", "name": "Start", "config": {}})
        definitions.setdefault("ManualTrigger", registry.get("ManualTrigger").definition)
        edges = [{"source": "trigger", "target": r, "condition": None} for r in roots] + edges
        ids = ["trigger"] + ids
        warnings.append("No trigger was chosen, so a manual 'Start' button was added.")

    # --- references to earlier steps ------------------------------------------------------
    names = {n["id"]: n["name"] for n in nodes}
    for n in nodes:
        for value in _strings(n["config"]):
            for ref_id, field in REF_RE.findall(value):
                ref = next((x for x in nodes if x["id"] == id_map.get(ref_id, ref_id)), None)
                if ref is None:
                    warnings.append(f"'{n['name']}' refers to a step that does not exist ('{ref_id}').")
                elif field.split(".")[0] not in {o.name for o in definitions[ref["type"]].outputs}:
                    warnings.append(f"'{n['name']}' uses '{field}' from '{ref['name']}', which that step may not provide.")
    # models sometimes reference the ids they *wanted*; rewrite them if we had to rename
    renames = {a: b for a, b in id_map.items() if a != b}
    if renames:
        for n in nodes:
            n["config"] = _rewrite(n["config"], renames)

    # --- what the person still has to fill in ---------------------------------------------
    todo = []
    for n in nodes:
        for p in definitions[n["type"]].parameters:
            if p.required and p.type != ParameterType.CREDENTIAL and n["config"].get(p.name) in (None, ""):
                todo.append({"nodeId": n["id"], "nodeName": n["name"], "field": p.name, "label": p.display_name})

    positions = _layout(ids, [(e["source"], e["target"]) for e in edges])
    return {
        "name": (str(draft.get("name") or "").strip() or "My new workflow")[:100].ljust(3, "."),
        "description": str(draft.get("description") or "")[:300],
        "nodes": [{
            "id": n["id"], "type": n["type"], "name": n["name"], "description": definitions[n["type"]].description,
            "config": n["config"], "position": positions[n["id"]], "enabled": True,
            "category": CATEGORY_MAP.get(definitions[n["type"]].category, "action"), "inputs": [], "outputs": [],
        } for n in nodes],
        "edges": [{
            "id": f"e_{e['source']}_{e['target']}", "source": e["source"], "target": e["target"],
            "sourceHandle": e["condition"] or "output", "targetHandle": "input", "condition": e["condition"], "enabled": True,
        } for e in edges],
        "steps": [{"id": i, "name": names[i], "type": next(n["type"] for n in nodes if n["id"] == i)} for i in ids if i in names],
        "warnings": warnings,
        "todo": todo,
    }


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _rewrite(value: Any, renames: Dict[str, str]) -> Any:
    if isinstance(value, str):
        return REF_RE.sub(lambda m: m.group(0).replace(f"$node.{m.group(1)}.", f"$node.{renames.get(m.group(1), m.group(1))}."), value)
    if isinstance(value, dict):
        return {k: _rewrite(v, renames) for k, v in value.items()}
    if isinstance(value, list):
        return [_rewrite(v, renames) for v in value]
    return value


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def generate(prompt: str, registry, ep: Optional[llm_service.Endpoint] = None) -> Dict[str, Any]:
    prompt = (prompt or "").strip()
    if len(prompt) < 8:
        raise GenerationError("Describe what you want to automate in a sentence or two.")
    if len(prompt) > MAX_PROMPT_CHARS:
        raise GenerationError(f"Please keep the description under {MAX_PROMPT_CHARS} characters.")

    ep = ep or llm_service.endpoint()
    messages = [{"role": "system", "content": system_prompt(registry, PREFERRED_AI.get(ep.provider, "LocalLLM"))},
                {"role": "user", "content": prompt}]
    error = ""
    for attempt in range(2):         # one retry if the model's reply is not usable JSON
        reply = await llm_service.chat(messages, json_mode=True, temperature=0.2, max_tokens=3000, ep=ep)
        try:
            draft = llm_service.extract_json(reply)
            return {**build_workflow(draft, registry, PREFERRED_AI.get(ep.provider, "LocalLLM")), "model": ep.model, "provider": ep.provider}
        except ValueError as exc:
            error = str(exc)
            logger.info("workflow draft attempt %d unusable: %s", attempt + 1, error)
            messages += [{"role": "assistant", "content": reply},
                         {"role": "user", "content": f"That reply was not usable ({error}). Reply again with only the JSON object."}]
    raise GenerationError(
        f"The AI could not turn that into a workflow ({error}). Try describing what should start it and what "
        f"should happen — or use a larger model."
    )
