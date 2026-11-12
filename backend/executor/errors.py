"""
Turns a raw error message from a step into something a non-technical person can act on.

Every failed step gets an ErrorInfo: a category, whether trying again could help, a one-line title, what it
means and what to do about it. The engine uses `retryable` to retry only errors that can be temporary, and the
editor, the Executions page, the dashboard alert and the AI assistant all show the same wording.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ErrorInfo:
    category: str
    retryable: bool
    title: str
    explanation: str
    suggestion: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# A status code only counts when it is written as one: "(500)", "error 500", "status 401", "HTTP 503" - not a port or a count.
def _status(*codes: str) -> str:
    return r"(?:\(|error |status |status_code |http )\s*(?:" + "|".join(codes) + r")\b"


# Order matters: the first rule that matches wins, so the specific ones come first.
_RULES: List[Tuple[str, bool, str, str, str, str]] = [
    ("rate_limit", True, "The service is limiting requests",
     "The other service said you are sending requests too fast, or you have used up your quota.",
     "Wait a moment and run again. For AI steps, try a smaller model, or check the usage limits on your account.",
     r"rate.?limit|too many requests|quota|" + _status("429")),
    ("timeout", True, "The step took too long",
     "The step did not finish in time, so it was stopped.",
     "Try again. If it keeps happening, make the request smaller, pick a faster model, or raise the step's time limit.",
     r"timed? ?out|timeout|did not answer within"),
    ("network", True, "Could not reach the service",
     "The server could not connect to the address, or the connection dropped.",
     "Check the address is spelled right and the service is running, then try again. A service that is down usually comes back by itself.",
     r"can'?t reach|cannot connect|could not connect|connection (?:refused|reset|error|failed|closed|aborted)|connect call failed|"
     r"name or service not known|getaddrinfo|network is unreachable|temporary failure|connecterror|request failed:|remote(?:ly)? (?:closed|disconnected)"),
    ("auth", False, "The login or key was rejected",
     "The service did not accept the API key, password or permissions that were used.",
     "Check the key or password in this step (or in Credentials). Make sure it is for the right account, not expired, and has permission for this action.",
     r"unauthori[sz]ed|forbidden|invalid[_ ]?(?:api[_ ]?)?key|incorrect api key|authentication (?:failed|error|required)|rejected the (?:server'?s )?api key|"
     r"invalid[_ ]auth|not_authed|invalid_token|token (?:expired|invalid|revoked)|bad credentials|permission denied|access denied|"
     r"username and password not accepted|credentials? (?:are |is )?(?:invalid|wrong|incorrect)|" + _status("401", "403") + r"|\b535\b"),
    ("not_found", False, "Something was not found",
     "The address, channel, file, table or model does not exist, or this account cannot see it.",
     "Check the name or ID is exactly right. For a local AI model, make sure it is installed.",
     r"not[_ ]found|no such|does not exist|doesn'?t exist|unknown (?:channel|table|column|database|model)|is not installed|" + _status("404")),
    ("server", True, "The other service had a problem",
     "The service reported an error on its side, not yours.",
     "Try again in a few minutes. If it keeps failing, check the service's status page.",
     r"internal server error|bad gateway|service unavailable|gateway time-?out|overloaded|upstream|" + _status("500", "502", "503", "504")),
    ("data", False, "The data was not in the expected form",
     "A step received data it could not read, for example broken JSON, text where a number was expected, or an empty value.",
     "Look at the step before this one and check what it actually produced (the Executions page shows each step's output). Then adjust the value or the format.",
     r"invalid json|json decode|expecting value|unexpected format|could not (?:parse|convert|read)|cannot be parsed|not a valid|must be a json|is not json"),
    ("config", False, "A required setting is missing or wrong",
     "This step is not fully set up yet.",
     "Open the step, fill in the highlighted required fields, and check each value is in the right format.",
     r"is required|are required|required for|not configured|not set\b|missing|must be|must start|needs at least|pick your|enter (?:it|them)|unknown (?:authentication|connection|operation|type)|invalid (?:email|address|url|port)"),
    ("bad_request", False, "The service did not accept the request",
     "The service understood the request but refused it, usually because a value is not allowed or something is missing.",
     "Check the values sent by this step against what the service expects (the service's own message is shown in the details).",
     r"bad request|invalid_payload|unprocessable|invalid_arguments|" + _status("400", "422")),
]
_COMPILED = [(c, r, t, e, s, re.compile(p, re.IGNORECASE)) for c, r, t, e, s, p in _RULES]

UNKNOWN = ErrorInfo(
    "unknown", False, "Something went wrong",
    "The step stopped with an error that does not match a common cause.",
    "Read the error message below. If it is not clear, ask the AI assistant to explain it, and check the previous steps' output.",
)

RETRYABLE_CATEGORIES = {c for c, r, *_ in _RULES if r}


def classify_error(message: Optional[str], node_type: Optional[str] = None) -> ErrorInfo:
    """The ErrorInfo for an error message. `node_type` sharpens the advice for AI steps."""
    text = str(message or "")
    for category, retryable, title, explanation, suggestion, pattern in _COMPILED:
        if pattern.search(text):
            if node_type in {"OpenAI", "ClaudeAI", "Gemini", "Groq", "LocalLLM"} and category == "auth":
                suggestion = "Check the API key for this AI provider (in this step or under Credentials), and that the account has credit and access to the chosen model."
            return ErrorInfo(category, retryable, title, explanation, suggestion)
    return UNKNOWN
