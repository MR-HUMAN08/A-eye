from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

BASE = Path(__file__).resolve().parent
BACKEND_ROOT = BASE.parent / "backend"

if str(BASE.parent) not in sys.path:
    sys.path.insert(0, str(BASE.parent))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("FINPATH_BACKEND_URL", "http://localhost:8000")

from mcp_server.prompts import finpath_prompts  # noqa: E402
from mcp_server.resources import finpath_resources  # noqa: E402
from mcp_server.tools import (  # noqa: E402
    audit_tools,
    behavioral_tools,
    browser_tools,
    cfo_tools,
    document_tools,
    goal_tools,
    memory_tools,
    nudge_tools,
    portfolio_tools,
    rag_coordinator_tools,
    rag_tools,
    retirement_tools,
    sentiment_tools,
    tax_tools,
)


app = FastMCP(
    "finpath-mcp",
    instructions="FinPath MCP server exposing auditable financial intelligence tools.",
    host="0.0.0.0",
    port=8001,
    sse_path="/sse",
)


def register_all() -> None:
    behavioral_tools.register(app)
    goal_tools.register(app)
    portfolio_tools.register(app)
    nudge_tools.register(app)
    rag_tools.register(app)
    rag_coordinator_tools.register(app)
    browser_tools.register(app)
    cfo_tools.register(app)
    tax_tools.register(app)
    sentiment_tools.register(app)
    document_tools.register(app)
    retirement_tools.register(app)
    audit_tools.register(app)
    memory_tools.register(app)
    finpath_resources.register(app)
    finpath_prompts.register(app)


register_all()

# FastMCP currently returns a tuple from call_tool in some versions.
# Normalize to a content block list so verification scripts can access result[0].text.
_raw_call_tool = app.call_tool


async def _call_tool_compat(name: str, arguments: dict[str, object]) -> object:
    result = await _raw_call_tool(name, arguments)
    if isinstance(result, tuple) and result:
        return result[0]
    return result


app.call_tool = _call_tool_compat  # type: ignore[assignment]


async def _run_stdio_safe() -> None:
    try:
        await app.run_stdio_async()
    except Exception as err:  # noqa: BLE001
        print(f"FinPath MCP stdio transport stopped: {err}", file=sys.stderr, flush=True)


async def _run_sse_safe() -> None:
    try:
        await app.run_sse_async(mount_path="/")
    except Exception as err:  # noqa: BLE001
        print(f"FinPath MCP SSE transport stopped: {err}", file=sys.stderr, flush=True)


async def _main() -> None:
    tools = await app.list_tools()
    resources = await app.list_resources()
    prompts = await app.list_prompts()
    print(
        f"FinPath MCP Server started. Tools: {len(tools)}. Resources: {len(resources)}. Prompts: {len(prompts)}.",
        file=sys.stderr,
        flush=True,
    )
    await asyncio.gather(_run_stdio_safe(), _run_sse_safe())


if __name__ == "__main__":
    asyncio.run(_main())
