"""HTTP Request — makes an HTTP call to any external URL."""

from __future__ import annotations
import json
from typing import Any, Dict
from nodes.base import BaseNode, NodeDefinition, NodeParameter, NodeOutputField, ParameterType, NodeExecutionError, SelectOption


def _as_dict(value: Any, label: str) -> Dict[str, Any]:
    """Headers / query parameters arrive as an object, or as JSON text typed into a field."""
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except ValueError:
            raise NodeExecutionError(f"{label} must be a JSON object like {{\"Key\": \"value\"}}.", "HttpRequest")
        if isinstance(parsed, dict):
            return parsed
        raise NodeExecutionError(f"{label} must be a JSON object like {{\"Key\": \"value\"}}.", "HttpRequest")
    return {}


def apply_auth(config: Dict[str, Any], headers: Dict[str, Any], params: Dict[str, Any]) -> Any:
    """Add the chosen authentication to the request; returns an httpx auth object for Basic, else None."""
    kind = str(config.get("auth_type") or "none").strip().lower()
    if kind in ("", "none"):
        return None

    def need(key: str, label: str) -> str:
        value = str(config.get(key) or "").strip()
        if not value:
            raise NodeExecutionError(f"{label} is required for this authentication type.", "HttpRequest")
        return value

    if kind == "basic":
        import httpx
        return httpx.BasicAuth(need("auth_username", "Username"), str(config.get("auth_password") or ""))
    if kind == "bearer":
        headers["Authorization"] = f"Bearer {need('auth_token', 'Token')}"
    elif kind == "api_key_header":
        headers[need("auth_key_name", "Key name")] = need("auth_key_value", "Key value")
    elif kind == "api_key_query":
        params[need("auth_key_name", "Key name")] = need("auth_key_value", "Key value")
    else:
        raise NodeExecutionError(f"Unknown authentication type '{kind}'.", "HttpRequest")
    return None


class HttpRequest(BaseNode):
    definition = NodeDefinition(
        type="HttpRequest",
        display_name="HTTP Request",
        description="Make an HTTP request to any URL, with optional authentication (Basic, Bearer token or API key).",
        category="Actions",
        icon="🌐",
        color="#0EA5E9",
        is_trigger=False,
        parameters=[
            NodeParameter(
                name="url",
                display_name="URL",
                type=ParameterType.EXPRESSION,
                required=True,
                description="The URL to request. Supports {{$node.x.y}} expressions.",
                placeholder="https://api.example.com/users",
            ),
            NodeParameter(
                name="method",
                display_name="Method",
                type=ParameterType.OPTIONS,
                required=False,
                default="GET",
                options=[
                    SelectOption(value="GET", label="GET"),
                    SelectOption(value="POST", label="POST"),
                    SelectOption(value="PUT", label="PUT"),
                    SelectOption(value="PATCH", label="PATCH"),
                    SelectOption(value="DELETE", label="DELETE"),
                ],
            ),
            NodeParameter(
                name="headers",
                display_name="Headers",
                type=ParameterType.COLLECTION,
                required=False,
                default={},
                description="Key-value pairs to send as HTTP headers",
            ),
            NodeParameter(
                name="body",
                display_name="Body (JSON)",
                type=ParameterType.EXPRESSION,
                required=False,
                default={},
                description="Request body as JSON object or expression",
            ),
            NodeParameter(
                name="query_params",
                display_name="Query Parameters",
                type=ParameterType.COLLECTION,
                required=False,
                default={},
                description="Key-value pairs appended to the URL as query parameters",
            ),
            NodeParameter(
                name="auth_type",
                display_name="Authentication",
                type=ParameterType.OPTIONS,
                required=False,
                default="none",
                description="How the API knows who you are.",
                options=[
                    SelectOption(value="none", label="None"),
                    SelectOption(value="basic", label="Basic (username and password)"),
                    SelectOption(value="bearer", label="Bearer token"),
                    SelectOption(value="api_key_header", label="API key in a header"),
                    SelectOption(value="api_key_query", label="API key in the URL (query)"),
                ],
            ),
            NodeParameter(name="auth_username", display_name="Username", type=ParameterType.STRING, required=False),
            NodeParameter(name="auth_password", display_name="Password", type=ParameterType.CREDENTIAL, required=False, is_private=True),
            NodeParameter(name="auth_token", display_name="Token", type=ParameterType.CREDENTIAL, required=False, is_private=True,
                          description="Sent as 'Authorization: Bearer <token>'."),
            NodeParameter(name="auth_key_name", display_name="Key name", type=ParameterType.STRING, required=False,
                          description="The header or query parameter name, for example X-API-Key or api_key."),
            NodeParameter(name="auth_key_value", display_name="Key value", type=ParameterType.CREDENTIAL, required=False, is_private=True),
            NodeParameter(
                name="timeout",
                display_name="Timeout (seconds)",
                type=ParameterType.NUMBER,
                required=False,
                default=30,
                min_value=1,
                max_value=300,
            ),
            NodeParameter(
                name="follow_redirects",
                display_name="Follow redirects",
                type=ParameterType.BOOLEAN,
                required=False,
                default=False,
                description="Follow 301/302 redirects to the final address.",
            ),
        ],
        outputs=[
            NodeOutputField(name="status_code", display_name="Status Code", type="number"),
            NodeOutputField(name="response_body", display_name="Response Body", type="object"),
            NodeOutputField(name="headers", display_name="Response Headers", type="object"),
            NodeOutputField(name="ok", display_name="Success (2xx)", type="boolean"),
            NodeOutputField(name="response_text", display_name="Response Text", type="string"),
        ],
    )

    async def execute(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any],
        context: Any,
    ) -> Dict[str, Any]:
        self._require(config, "url")

        url: str = str(config["url"])
        method: str = config.get("method", "GET").upper()
        headers = _as_dict(config.get("headers"), "Headers")
        body = config.get("body") or None
        params = _as_dict(config.get("query_params"), "Query parameters")
        timeout: float = float(config.get("timeout", 30))
        auth = apply_auth(config, headers, params)

        try:
            import httpx
        except ImportError:
            raise NodeExecutionError("httpx is not installed. Add it to requirements.txt.", self.definition.type)

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=bool(config.get("follow_redirects"))) as client:
                request_kwargs: Dict[str, Any] = {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "params": params,
                }
                if auth is not None:
                    request_kwargs["auth"] = auth
                if body and method not in ("GET", "DELETE", "HEAD"):
                    if isinstance(body, dict):
                        request_kwargs["json"] = body
                    else:
                        request_kwargs["content"] = str(body).encode()

                response = await client.request(**request_kwargs)

            # Try to parse JSON body
            try:
                response_body = response.json()
            except Exception:
                response_body = {}

            return {
                "status_code": response.status_code,
                "response_body": response_body,
                "headers": dict(response.headers),
                "ok": 200 <= response.status_code < 300,
                "response_text": response.text,
            }

        except httpx.TimeoutException:
            raise NodeExecutionError(f"Request to {url} timed out after {timeout}s", self.definition.type)
        except httpx.RequestError as exc:
            raise NodeExecutionError(f"HTTP request failed: {exc}", self.definition.type)
