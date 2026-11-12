"""Slack Message — posts a message to a Slack channel."""

from __future__ import annotations
from typing import Any, Dict
from nodes.base import BaseNode, NodeDefinition, NodeParameter, NodeOutputField, ParameterType, NodeExecutionError, SelectOption

# Incoming-webhook URLs only ever live here; refusing anything else keeps this node from being used to call arbitrary addresses
SLACK_WEBHOOK_PREFIX = "https://hooks.slack.com/"


class SlackMessage(BaseNode):
    definition = NodeDefinition(
        type="SlackMessage",
        display_name="Slack Message",
        description="Post a message to Slack with a bot token (any channel) or an incoming webhook (one channel, no app setup).",
        category="Actions",
        icon="💬",
        color="#4A154B",
        is_trigger=False,
        required_credentials=["slack_bot_token"],
        parameters=[
            NodeParameter(
                name="mode",
                display_name="How to connect",
                type=ParameterType.OPTIONS,
                required=False,
                default="bot_token",
                description="A bot token can post to any channel the bot is in. An incoming webhook is simpler but posts to one channel.",
                options=[
                    SelectOption(value="bot_token", label="Bot token"),
                    SelectOption(value="webhook", label="Incoming webhook URL"),
                ],
            ),
            NodeParameter(
                name="webhook_url",
                display_name="Webhook URL",
                type=ParameterType.CREDENTIAL,
                required=False,
                description="From Slack: Apps > Incoming Webhooks. Starts with https://hooks.slack.com/",
                is_private=True,
            ),
            NodeParameter(
                name="channel",
                display_name="Channel",
                type=ParameterType.EXPRESSION,
                required=True,
                description="Channel ID or name (e.g. #general or C012345678). Not needed with an incoming webhook.",
                placeholder="#general",
            ),
            NodeParameter(
                name="message",
                display_name="Message",
                type=ParameterType.EXPRESSION,
                required=True,
                description="Message text. Supports Slack markdown and {{$node.x.y}} expressions.",
                placeholder="Hello from FlowMind AI!",
            ),
            NodeParameter(
                name="token",
                display_name="Bot Token",
                type=ParameterType.CREDENTIAL,
                required=True,
                description="Slack Bot Token (xoxb-...). Store in Credentials for security.",
                is_private=True,
            ),
            NodeParameter(
                name="username",
                display_name="Bot Name",
                type=ParameterType.STRING,
                required=False,
                default="FlowMind AI",
            ),
        ],
        outputs=[
            NodeOutputField(name="sent", display_name="Sent", type="boolean"),
            NodeOutputField(name="timestamp", display_name="Message Timestamp", type="string"),
            NodeOutputField(name="channel", display_name="Channel", type="string"),
            NodeOutputField(name="sent_at", display_name="Sent At", type="string"),
        ],
    )

    async def execute(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any],
        context: Any,
    ) -> Dict[str, Any]:
        mode = str(config.get("mode") or "bot_token").strip().lower()
        username = config.get("username", "FlowMind AI")

        if mode == "webhook":
            self._require(config, "message")
            return await self._send_webhook(config, str(config["message"]), username)
        if mode != "bot_token":
            raise NodeExecutionError(f"Unknown connection type '{mode}'. Use bot_token or webhook.", self.definition.type)

        self._require(config, "channel", "message")
        channel = str(config["channel"])
        message = str(config["message"])
        token = config.get("token") or context.get_credential("slack_bot_token", "token", "")

        if not token:
            raise NodeExecutionError(
                "Slack bot token is required. Set it in the node config or in Credentials.",
                self.definition.type,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"channel": channel, "text": message, "username": username},
                )
                data = response.json()

            if not data.get("ok"):
                raise NodeExecutionError(
                    f"Slack API error: {data.get('error', 'unknown')}",
                    self.definition.type,
                )

            return {
                "sent": True,
                "timestamp": data.get("ts", ""),
                "channel": data.get("channel", channel),
                "sent_at": self._now_iso(),
            }
        except NodeExecutionError:
            raise
        except Exception as exc:
            raise NodeExecutionError(f"Slack request failed: {exc}", self.definition.type)

    async def _send_webhook(self, config: Dict[str, Any], message: str, username: Any) -> Dict[str, Any]:
        url = str(config.get("webhook_url") or "").strip()
        if not url.startswith(SLACK_WEBHOOK_PREFIX):
            raise NodeExecutionError(
                f"Webhook URL must start with {SLACK_WEBHOOK_PREFIX} (copy it from Slack: Apps > Incoming Webhooks).",
                self.definition.type,
            )
        payload: Dict[str, Any] = {"text": message, "username": username}
        channel = str(config.get("channel") or "").strip()
        if channel:
            payload["channel"] = channel   # only honoured by older webhooks; newer ones post to their own channel
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
        except Exception as exc:
            raise NodeExecutionError(f"Slack request failed: {exc}", self.definition.type)
        if response.status_code != 200 or response.text.strip() != "ok":
            raise NodeExecutionError(
                f"Slack webhook error ({response.status_code}): {response.text.strip()[:120] or 'no details'}",
                self.definition.type,
            )
        return {"sent": True, "timestamp": "", "channel": channel, "sent_at": self._now_iso()}
