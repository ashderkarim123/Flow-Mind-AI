"""
A readable, secret-free description of a workflow, for the AI assistant.

The editor sends what is on the canvas (steps, their settings, connections), the workflow's variables and the
last run's result. This turns that into plain text the model can explain and troubleshoot from, with every key,
password and token masked, and adds a check for the mistakes people make most (no trigger, a step nothing leads
to, a required setting left empty, a reference to a step or variable that does not exist).

The same text, written as an answer, is what the assistant falls back to when no AI model can be reached.
"""

from __future__ import annotations

import json
import re
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from executor.errors import classify_error
from nodes.base import NodeDefinition, ParameterType

MAX_VALUE_CHARS = 140
MAX_CHARS = 6000
MASK = "••••"

# A setting whose name looks like a secret is masked even when no node definition marks it private.
_SECRET_NAME = re.compile(r"pass(?:word)?|secret|token|api[_-]?key|credential|connection_string|webhook_url|authorization|private[_-]?key|key_value", re.I)
_SKIP_KEYS = {"name", "headersList", "paramsList", "argTypes"}

# Names the editor's sidebar uses, mapped to the server's node types.
_ALIASES = {"emailsend": "SendEmail", "scheduling": "Schedule", "conditional": "IfCondition", "variablesetter": "SetVariable",
            "onclickingexecute": "ManualTrigger", "stringmanipulation": "DataFormatter", "jsonparse": "JsonParser",
            "postgresqlquery": "PostgresQuery", "incomingwebhook": "Webhook"}


def _key(value: Any) -> str:
    return re.sub(r"[\s_\-]", "", str(value or "")).lower()


class _Index:
    """Finds a node's definition by any of the names the editor, the server or the AI use for it."""

    def __init__(self, registry):
        self.by_key: Dict[str, NodeDefinition] = {}
        for d in registry.all_definitions():
            self.by_key[_key(d.type)] = d
            self.by_key.setdefault(_key(d.display_name), d)

    def find(self, node_type: Any) -> Optional[NodeDefinition]:
        k = _key(node_type)
        if k in self.by_key:
            return self.by_key[k]
        alias = _ALIASES.get(k)
        return self.by_key.get(_key(alias)) if alias else None


def _short(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= MAX_VALUE_CHARS else text[:MAX_VALUE_CHARS] + "…"


def _is_secret(key: str, definition: Optional[NodeDefinition]) -> bool:
    if definition:
        for p in definition.parameters:
            if p.name == key and (p.is_private or p.type == ParameterType.CREDENTIAL):
                return True
    return bool(_SECRET_NAME.search(key))


def _config_lines(config: Dict[str, Any], definition: Optional[NodeDefinition]) -> List[str]:
    out = []
    for key, value in config.items():
        if key.startswith("_") or key in _SKIP_KEYS or value in (None, "", [], {}):
            continue
        if _is_secret(key, definition):
            out.append(f"{key}: {MASK}")
        elif isinstance(value, dict) and key in ("headers", "query_params"):
            out.append(f"{key}: " + ", ".join(f"{k}={MASK if _SECRET_NAME.search(k) else _short(v)}" for k, v in value.items()))
        else:
            out.append(f"{key}: {_short(value)}")
    return out


def _settings_line(config: Dict[str, Any]) -> str:
    s = config.get("_settings")
    if not isinstance(s, dict):
        return ""
    parts = []
    if s.get("retry_on_fail"):
        parts.append(f"retries up to {s.get('max_tries') or 3} times")
    if s.get("timeout_s"):
        parts.append(f"time limit {s['timeout_s']}s")
    if s.get("on_error") == "continue":
        parts.append("carries on if it fails")
    elif s.get("on_error") == "fallback":
        parts.append(f"uses a fallback value ({_short(s.get('fallback_value', ''))}) if it fails")
    if s.get("notes"):
        parts.append(f"note: {_short(s['notes'])}")
    return "; ".join(parts)


def _edges(state: Dict[str, Any]) -> List[Tuple[str, str, Optional[str]]]:
    out = []
    for c in (state.get("connections") or state.get("edges") or []):
        if not isinstance(c, dict):
            continue
        a = c.get("from") or c.get("source") or c.get("sourceNodeId")
        b = c.get("to") or c.get("target") or c.get("targetNodeId")
        if a and b:
            out.append((str(a), str(b), c.get("condition")))
    return out


def _all_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _all_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _all_strings(v)


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def describe_workflow(state: Optional[Dict[str, Any]], registry, variables: Optional[Dict[str, Any]] = None,
                      last_run: Optional[Dict[str, Any]] = None, name: str = "") -> Dict[str, Any]:
    """{"text": ..., "problems": [...], "steps": [...]} for a canvas state. Safe to send to a model: secrets are masked."""
    state = state or {}
    raw_nodes = [n for n in (state.get("nodes") or []) if isinstance(n, dict)]
    index = _Index(registry)
    edges = _edges(state)
    ids = {str(n.get("id")) for n in raw_nodes}

    steps: List[Dict[str, Any]] = []
    for n in raw_nodes:
        config = n.get("config") if isinstance(n.get("config"), dict) else (n.get("data") or {}).get("config") or {}
        d = index.find(n.get("type"))
        steps.append({"id": str(n.get("id")), "name": n.get("name") or (d.display_name if d else str(n.get("type"))),
                      "type": d.type if d else str(n.get("type")), "label": d.display_name if d else str(n.get("type")),
                      "description": d.description.split(". ")[0] if d else "", "trigger": bool(d and d.is_trigger),
                      "known": d is not None, "config": config, "definition": d})
    names = {s["id"]: s["name"] for s in steps}

    # order the steps the way a run reaches them
    nxt: Dict[str, List[str]] = {s["id"]: [] for s in steps}
    for a, b, _c in edges:
        if a in nxt and b in names:
            nxt[a].append(b)
    order: List[str] = []
    queue = deque(s["id"] for s in steps if s["trigger"])
    while queue:
        i = queue.popleft()
        if i in order:
            continue
        order.append(i)
        queue.extend(nxt.get(i, []))
    reachable = set(order)
    order += [s["id"] for s in steps if s["id"] not in reachable]
    by_id = {s["id"]: s for s in steps}

    # ---- problems -------------------------------------------------------------------
    problems: List[str] = []
    if not steps:
        problems.append("The workflow is empty: add a trigger first, then the steps it should run.")
    elif not any(s["trigger"] for s in steps):
        problems.append("There is no trigger. A workflow needs one (for example Manual Trigger, Schedule or Webhook) to start it.")
    for s in steps:
        if s["id"] not in reachable and any(x["trigger"] for x in steps):
            problems.append(f"'{s['name']}' is not connected to the trigger, so it will never run.")
        if not s["known"]:
            problems.append(f"'{s['name']}' is of type '{s['type']}', which the server does not know.")
    defined_vars = set((variables or {}).keys())
    for s in steps:
        if s["config"].get("variable_name"):
            defined_vars.add(str(s["config"]["variable_name"]))
    for s in steps:
        d, cfg = s["definition"], s["config"]
        if d:
            for p in d.parameters:
                if p.required and _blank(cfg.get(p.name)):
                    if p.is_private or p.type == ParameterType.CREDENTIAL:
                        problems.append(f"'{s['name']}' has no {p.display_name} typed in; it must come from Credentials or the server.")
                    else:
                        problems.append(f"'{s['name']}' is missing a required setting: {p.display_name}.")
        for text in _all_strings({k: v for k, v in cfg.items() if not k.startswith("_")}):
            for ref in re.findall(r"\{\{\s*\$node\.([A-Za-z0-9_\-]+)", text):
                if ref not in ids:
                    problems.append(f"'{s['name']}' refers to a step '{ref}' that does not exist (it may have been deleted or renamed).")
            for ref in re.findall(r"\{\{\s*\$vars\.([A-Za-z0-9_]+)", text):
                if ref not in defined_vars:
                    problems.append(f"'{s['name']}' uses the variable '{ref}', which is not defined (add it under Variables, or set it with a Variable Setter step).")
        if s["type"] == "IfCondition":
            have = {str(c).lower() for a, _b, c in edges if a == s["id"]}
            for branch in ("true", "false"):
                if branch not in have:
                    problems.append(f"'{s['name']}' has nothing connected to its '{branch}' path.")
    problems = list(dict.fromkeys(problems))

    # ---- text -----------------------------------------------------------------------
    lines: List[str] = [f'Workflow "{name or state.get("name") or "Untitled"}": {len(steps)} step(s).']
    if not steps:
        lines.append("(The canvas is empty.)")
    for number, i in enumerate(order, 1):
        s = by_id[i]
        role = " [trigger]" if s["trigger"] else ""
        lines.append(f'{number}. [{i}] "{s["name"]}" ({s["label"]}){role}' + (f" - {s['description']}" if s["description"] else ""))
        cfg_lines = _config_lines(s["config"], s["definition"])
        if cfg_lines:
            lines.append("   settings: " + "; ".join(cfg_lines))
        extra = _settings_line(s["config"])
        if extra:
            lines.append("   safety: " + extra)
    if edges:
        lines.append("Connections: " + "; ".join(f'{names.get(a, a)} -> {names.get(b, b)}' + (f" ({c})" if c else "") for a, b, c in edges))
    if variables:
        lines.append("Workflow variables: " + ", ".join(f"{k} = {MASK if _SECRET_NAME.search(k) else _short(v)}" for k, v in variables.items()))
    if problems:
        lines.append("Possible problems found before running:")
        lines += [f"- {p}" for p in problems]
    lines += _last_run_lines(last_run, names)

    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n… (the rest of the workflow was cut to keep this short)"
    return {"text": text, "problems": problems, "steps": [{k: v for k, v in s.items() if k not in ("config", "definition")} for s in steps]}


def _last_run_lines(run: Optional[Dict[str, Any]], names: Dict[str, str]) -> List[str]:
    if not run:
        return []
    out = [f"Last run: {run.get('status', 'unknown')}."]
    info = run.get("errorInfo") or (classify_error(run["error"]).to_dict() if run.get("error") and run.get("status") == "failed" else {})
    if run.get("error"):
        out.append(f"Error: {_short(run['error'])}")
    if info:
        out.append(f"Meaning: {info.get('title', '')} - {info.get('explanation', '')} Suggested fix: {info.get('suggestion', '')}")
    for log in (run.get("nodeLogs") or [])[:40]:
        if not isinstance(log, dict):
            continue
        mark = "OK" if log.get("status") == "success" else "FAILED" if log.get("status") == "failed" else str(log.get("status"))
        who = log.get("nodeName") or names.get(str(log.get("nodeId")), log.get("nodeType") or log.get("nodeId"))
        extra = []
        if log.get("executionTimeMs") is not None:
            extra.append(f"{round(float(log['executionTimeMs']))}ms")
        if (log.get("attempts") or 1) > 1:
            extra.append(f"tried {log['attempts']} times")
        if log.get("fallbackUsed"):
            extra.append("fallback value used")
        line = f'- "{who}": {mark}' + (f" ({', '.join(extra)})" if extra else "")
        if log.get("error"):
            line += f" - {_short(log['error'])}"
            title = (log.get("errorInfo") or classify_error(log["error"], log.get("nodeType")).to_dict()).get("title")
            if title:
                line += f" [{title}]"
        out.append(line)
    return out


def plain_explanation(digest: Dict[str, Any], last_run: Optional[Dict[str, Any]] = None) -> str:
    """The digest as an answer a person can read, used when no AI model is reachable."""
    steps = digest["steps"]
    if not steps:
        return "Your workflow is empty. Start by adding a trigger (for example Manual Trigger or Schedule), then the steps it should run."
    parts = [f"Your workflow has {len(steps)} step(s):"]
    for n, s in enumerate(steps, 1):
        parts.append(f"{n}. {s['name']} ({s['label']})" + (f": {s['description']}." if s["description"] else "."))
    run = last_run or {}
    if run.get("status") == "failed":
        info = run.get("errorInfo") or (classify_error(run["error"]).to_dict() if run.get("error") else {})
        parts.append(f"\nThe last run failed. {info.get('title', 'Something went wrong')}: {info.get('explanation', run.get('error', ''))}")
        if info.get("suggestion"):
            parts.append(f"What to do: {info['suggestion']}")
        if run.get("error"):
            parts.append(f"Technical message: {_short(run['error'])}")
    if digest["problems"]:
        parts.append("\nThings to check:")
        parts += [f"- {p}" for p in digest["problems"]]
    return "\n".join(parts)
