"""Send Email — sends an email via SMTP."""

from __future__ import annotations
from email.utils import formataddr, getaddresses
from typing import Any, Dict, List
from nodes.base import BaseNode, NodeDefinition, NodeParameter, NodeOutputField, ParameterType, NodeExecutionError, SelectOption

# Connection settings for the common mail services. The editor shows the same values when a provider is picked
# (lib/workflow/NodeDefinitions.ts); a host or port typed into the node always wins over the preset.
EMAIL_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "gmail": {"host": "smtp.gmail.com", "port": 587, "security": "starttls"},
    "outlook": {"host": "smtp.office365.com", "port": 587, "security": "starttls"},
    "yahoo": {"host": "smtp.mail.yahoo.com", "port": 465, "security": "ssl"},
    "zoho": {"host": "smtp.zoho.com", "port": 465, "security": "ssl"},
    "icloud": {"host": "smtp.mail.me.com", "port": 587, "security": "starttls"},
}
SECURITY_MODES = ("starttls", "ssl", "none")


def smtp_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Host, port and connection security from a node config: typed values, else the provider preset, else defaults."""
    preset = EMAIL_PROVIDERS.get(str(config.get("provider") or "custom").strip().lower(), {})
    host = str(config.get("smtp_host") or "").strip() or preset.get("host", "")
    raw_port = config.get("smtp_port")
    try:
        port = int(raw_port) if raw_port not in (None, "") else int(preset.get("port", 587))
    except (TypeError, ValueError):
        raise NodeExecutionError(f"SMTP port must be a number, not '{raw_port}'.", "SendEmail")
    # port 465 has always meant implicit SSL; anything else starts plain and upgrades with STARTTLS
    security = str(config.get("smtp_security") or "").strip().lower() or preset.get("security") or ("ssl" if port == 465 else "starttls")
    if security not in SECURITY_MODES:
        raise NodeExecutionError(f"Connection security must be one of {', '.join(SECURITY_MODES)}, not '{security}'.", "SendEmail")
    return {"host": host, "port": port, "security": security}


def _addresses(value: Any, label: str) -> List[str]:
    """'a@x.com, B <b@y.com>' -> ['a@x.com', 'b@y.com'], refusing anything that is not an address."""
    found = [addr.strip() for _, addr in getaddresses([str(value or "").replace(";", ",")]) if addr.strip()]
    bad = [a for a in found if "@" not in a or " " in a]
    if bad:
        raise NodeExecutionError(f"{label} has an invalid email address: {bad[0]}", "SendEmail")
    return found


def _one_line(value: Any) -> str:
    return " ".join(str(value or "").split())   # stops a stray line break from injecting extra mail headers


class SendEmail(BaseNode):
    definition = NodeDefinition(
        type="SendEmail",
        display_name="Send Email",
        description="Send an email through Gmail, Outlook, Yahoo, Zoho, iCloud or any SMTP server.",
        category="Actions",
        icon="📧",
        color="#F59E0B",
        is_trigger=False,
        parameters=[
            NodeParameter(
                name="provider",
                display_name="Email service",
                type=ParameterType.OPTIONS,
                required=False,
                default="custom",
                description="Pick your mail service to fill in its server settings, or choose Custom SMTP.",
                options=[
                    SelectOption(value="gmail", label="Gmail"),
                    SelectOption(value="outlook", label="Outlook / Microsoft 365"),
                    SelectOption(value="yahoo", label="Yahoo Mail"),
                    SelectOption(value="zoho", label="Zoho Mail"),
                    SelectOption(value="icloud", label="iCloud Mail"),
                    SelectOption(value="custom", label="Custom SMTP server"),
                ],
            ),
            NodeParameter(
                name="to",
                display_name="To",
                type=ParameterType.EXPRESSION,
                required=True,
                description="Recipient email address(es). Comma-separated for multiple.",
                placeholder="user@example.com",
            ),
            NodeParameter(
                name="subject",
                display_name="Subject",
                type=ParameterType.EXPRESSION,
                required=True,
                placeholder="Hello from FlowMind AI",
            ),
            NodeParameter(
                name="body",
                display_name="Body",
                type=ParameterType.EXPRESSION,
                required=True,
                description="Email body. Supports plain text or HTML.",
                placeholder="Hi there!",
            ),
            NodeParameter(
                name="cc", display_name="Cc", type=ParameterType.EXPRESSION, required=False,
                description="Copy these addresses in (comma-separated).",
            ),
            NodeParameter(
                name="bcc", display_name="Bcc", type=ParameterType.EXPRESSION, required=False,
                description="Hidden copies (comma-separated).",
            ),
            NodeParameter(
                name="reply_to", display_name="Reply-To", type=ParameterType.EXPRESSION, required=False,
                description="Where replies should go, if not the sender.",
            ),
            NodeParameter(
                name="smtp_host",
                display_name="SMTP Host",
                type=ParameterType.STRING,
                required=False,
                default="",
                description="SMTP server hostname. Filled in automatically for Gmail, Outlook, Yahoo, Zoho and iCloud.",
                placeholder="smtp.gmail.com",
            ),
            NodeParameter(
                name="smtp_port",
                display_name="SMTP Port",
                type=ParameterType.NUMBER,
                required=False,
                default=587,
                description="SMTP port. 587 for STARTTLS, 465 for SSL.",
            ),
            NodeParameter(
                name="smtp_security",
                display_name="Connection security",
                type=ParameterType.OPTIONS,
                required=False,
                default="starttls",
                description="STARTTLS (port 587), SSL/TLS (port 465), or none (only for a trusted local server).",
                options=[
                    SelectOption(value="starttls", label="STARTTLS (port 587)"),
                    SelectOption(value="ssl", label="SSL / TLS (port 465)"),
                    SelectOption(value="none", label="None"),
                ],
            ),
            NodeParameter(
                name="smtp_user",
                display_name="SMTP Username",
                type=ParameterType.STRING,
                required=True,
                default="",
                description="SMTP login email address.",
                placeholder="you@gmail.com",
            ),
            NodeParameter(
                name="smtp_pass",
                display_name="SMTP Password",
                type=ParameterType.CREDENTIAL,
                required=True,
                description="SMTP password. Gmail and Yahoo need an app password, not your normal password.",
                is_private=True,
            ),
            NodeParameter(
                name="from_email",
                display_name="From Email",
                type=ParameterType.STRING,
                required=False,
                default="",
                description="Sender address. Defaults to SMTP Username if blank.",
                placeholder="noreply@example.com",
            ),
            NodeParameter(
                name="from_name",
                display_name="From Name",
                type=ParameterType.STRING,
                required=False,
                default="FlowMind AI",
            ),
            NodeParameter(
                name="is_html",
                display_name="Send as HTML",
                type=ParameterType.BOOLEAN,
                required=False,
                default=False,
            ),
        ],
        outputs=[
            NodeOutputField(name="sent", display_name="Sent", type="boolean"),
            NodeOutputField(name="message_id", display_name="Message ID", type="string"),
            NodeOutputField(name="sent_at", display_name="Sent At", type="string"),
            NodeOutputField(name="to", display_name="Recipients", type="string"),
        ],
    )

    async def execute(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any],
        context: Any,
    ) -> Dict[str, Any]:
        self._require(config, "to", "subject", "body")

        to = _addresses(config["to"], "To")
        cc = _addresses(config.get("cc"), "Cc")
        bcc = _addresses(config.get("bcc"), "Bcc")
        reply_to = _addresses(config.get("reply_to"), "Reply-To")
        if not to:
            raise NodeExecutionError("To needs at least one email address.", self.definition.type)
        subject = _one_line(config["subject"])
        body = str(config["body"])
        from_name = _one_line(config.get("from_name", "FlowMind AI"))
        is_html = config.get("is_html", False)

        # Credentials come from the node (or a saved credential via {{$creds.name}}) - there is no .env fallback
        smtp = smtp_settings(config)
        smtp_user = str(config.get("smtp_user") or "").strip()
        smtp_pass = str(config.get("smtp_pass") or "").strip()
        from_email = str(config.get("from_email") or "").strip() or smtp_user

        if not smtp["host"]:
            raise NodeExecutionError(
                "Pick your email service, or enter the SMTP host (for example smtp.gmail.com).",
                self.definition.type,
            )
        if not smtp_user or not smtp_pass:
            raise NodeExecutionError(
                "SMTP Username and Password are required. Enter them in the node config.",
                self.definition.type,
            )

        try:
            import aiosmtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            import uuid

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr((from_name, from_email))
            msg["To"] = ", ".join(to)
            if cc:
                msg["Cc"] = ", ".join(cc)
            if reply_to:
                msg["Reply-To"] = ", ".join(reply_to)
            message_id = f"<{uuid.uuid4()}@flowmindai>"
            msg["Message-ID"] = message_id

            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, content_type))

            await aiosmtplib.send(
                msg,
                sender=from_email,
                recipients=to + cc + bcc,   # Bcc is delivered but never written into the headers
                hostname=smtp["host"],
                port=smtp["port"],
                username=smtp_user,
                password=smtp_pass,
                use_tls=smtp["security"] == "ssl",
                start_tls=smtp["security"] == "starttls",
            )

            return {
                "sent": True,
                "message_id": message_id,
                "sent_at": self._now_iso(),
                "to": ", ".join(to),
            }
        except NodeExecutionError:
            raise
        except Exception as exc:
            raise NodeExecutionError(f"Failed to send email: {exc}", self.definition.type)
