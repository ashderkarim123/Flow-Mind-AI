"""
Outbound-URL guard (SSRF protection) for user-supplied server addresses.

Users can point the platform at an MCP server or a local-model server. On a shared/hosted
deployment that would let them make the backend call internal addresses (localhost, cloud
metadata, private networks). Private hosts are therefore refused unless the operator opts in
with ALLOW_PRIVATE_HOSTS=true — which is exactly what a self-hosted, single-owner install
(Ollama / MCP servers on the same machine or LAN) wants.
"""

import ipaddress
import os
import socket
from urllib.parse import urlparse

_TRUE = {"1", "true", "yes", "on"}


class UnsafeURL(ValueError):
    """Raised for a URL the backend must not call."""


def allow_private_hosts() -> bool:
    return os.getenv("ALLOW_PRIVATE_HOSTS", "").strip().lower() in _TRUE


def assert_safe_url(url: str) -> None:
    """Blocking (does a DNS lookup) — call via asyncio.to_thread from async code.

    # ponytail: checks at call time only; a hostile DNS server could still rebind between this
    # check and the request. Pin the resolved IP if the threat model needs it.
    """
    parsed = urlparse(url or "")
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UnsafeURL("The address must be a full http:// or https:// URL.")
    if allow_private_hosts():
        return
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except socket.gaierror as exc:
        raise UnsafeURL(f"Could not resolve the host '{parsed.hostname}': {exc}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise UnsafeURL(
                f"'{parsed.hostname}' points to a private/internal address, which this server does not allow "
                f"(an administrator can enable it with ALLOW_PRIVATE_HOSTS=true)."
            )
