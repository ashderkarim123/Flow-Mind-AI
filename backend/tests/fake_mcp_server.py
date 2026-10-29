"""
A tiny real MCP server used by the tests (stdio by default, `--http PORT` for streamable HTTP).

    python tests/fake_mcp_server.py            # stdio
    python tests/fake_mcp_server.py --http 8765
"""

import os
import sys

from mcp.server.mcpserver import MCPServer

server = MCPServer("fake-tools")


@server.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@server.tool()
def shout(text: str, times: int = 1) -> str:
    """Repeat text in upper case."""
    return " ".join([text.upper()] * times)


@server.tool()
def secret_env() -> str:
    """Report whether a sensitive backend variable leaked into this process (it must not)."""
    return "LEAKED" if os.environ.get("FIREBASE_PRIVATE_KEY") else "clean"


@server.tool()
def echo_env(name: str) -> str:
    """Return the value of an environment variable inside this server process."""
    return os.environ.get(name, "")


@server.tool()
def boom() -> str:
    """Always fails."""
    raise ValueError("tool exploded")


if __name__ == "__main__":
    if "--http" in sys.argv:
        port = int(sys.argv[sys.argv.index("--http") + 1])
        server.run(transport="streamable-http", host="127.0.0.1", port=port)
    else:
        server.run(transport="stdio")
