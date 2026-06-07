"""n8n MCP Server — Workflow-Management via Claude.

Auth-Architektur (identisch zu whisper-mcp / ntfy-mcp / hero-mcp):
  1. Statischer Bearer (MCP_API_KEY)
  2. Bearer JWT → Authelia OIDC Introspection
"""

import json
import logging
import os
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)

from . import client  # noqa: E402

server = Server(
    "n8n-mcp-server",
    instructions=(
        "MCP-Server für selbst gehostetes n8n. Workflow-Lifecycle (CRUD + "
        "activate/deactivate), Execution-Logs einsehen, Tags und Users.\n\n"
        "Workflows werden als komplettes JSON-Objekt mit 'nodes' (Array) und "
        "'connections' (Object) übergeben — siehe n8n REST API Docs. "
        "Vor dem Erstellen am besten ein existierendes Workflow mit "
        "n8n_get_workflow inspizieren um die Struktur zu lernen."
    ),
)


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # ── Workflows ─────────────────────────────────────────────────
        types.Tool(
            name="n8n_list_workflows",
            description=(
                "Listet Workflows. Optional gefiltert nach active=true/false, "
                "Tag-Namen (komma-separiert) oder Name (Substring)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "active": {"type": "boolean"},
                    "tags": {"type": "string", "description": "Tag-Namen komma-separiert"},
                    "name": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                },
            },
        ),
        types.Tool(
            name="n8n_get_workflow",
            description="Voll-Details eines Workflows inkl. nodes + connections.",
            inputSchema={
                "type": "object",
                "properties": {"workflow_id": {"type": "string"}},
                "required": ["workflow_id"],
            },
        ),
        types.Tool(
            name="n8n_create_workflow",
            description=(
                "Erstellt einen neuen Workflow. `workflow` ist ein n8n-Workflow-"
                "Objekt mit mindestens {name, nodes[], connections{}}. "
                "Settings ist optional aber empfohlen."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow": {
                        "type": "object",
                        "description": (
                            "n8n-Workflow-Spec: {name, nodes, connections, settings?}"
                        ),
                    }
                },
                "required": ["workflow"],
            },
        ),
        types.Tool(
            name="n8n_update_workflow",
            description="Ersetzt einen Workflow vollständig (PUT-Semantik).",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "workflow": {"type": "object"},
                },
                "required": ["workflow_id", "workflow"],
            },
        ),
        types.Tool(
            name="n8n_delete_workflow",
            description="Löscht einen Workflow permanent.",
            inputSchema={
                "type": "object",
                "properties": {"workflow_id": {"type": "string"}},
                "required": ["workflow_id"],
            },
        ),
        types.Tool(
            name="n8n_activate_workflow",
            description="Aktiviert einen Workflow (Trigger werden scharf geschaltet).",
            inputSchema={
                "type": "object",
                "properties": {"workflow_id": {"type": "string"}},
                "required": ["workflow_id"],
            },
        ),
        types.Tool(
            name="n8n_deactivate_workflow",
            description="Deaktiviert einen Workflow.",
            inputSchema={
                "type": "object",
                "properties": {"workflow_id": {"type": "string"}},
                "required": ["workflow_id"],
            },
        ),
        # ── Executions ────────────────────────────────────────────────
        types.Tool(
            name="n8n_list_executions",
            description=(
                "Listet Workflow-Executions. Filter: workflow_id, status "
                "('success', 'error', 'waiting', 'running')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["success", "error", "waiting", "running"],
                    },
                    "include_data": {"type": "boolean", "default": False},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        ),
        types.Tool(
            name="n8n_get_execution",
            description=(
                "Volle Execution inkl. aller Node-Outputs (per Default mit Data)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string"},
                    "include_data": {"type": "boolean", "default": True},
                },
                "required": ["execution_id"],
            },
        ),
        types.Tool(
            name="n8n_delete_execution",
            description="Löscht eine Execution.",
            inputSchema={
                "type": "object",
                "properties": {"execution_id": {"type": "string"}},
                "required": ["execution_id"],
            },
        ),
        # ── Tags / Credentials Meta / Users ───────────────────────────
        types.Tool(
            name="n8n_list_tags",
            description="Listet alle Tags.",
            inputSchema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 100}},
            },
        ),
        types.Tool(
            name="n8n_list_credential_schemas",
            description=(
                "Listet verfügbare Credential-Typen mit ihren Schemas. "
                "Liefert KEINE tatsächlichen Credential-Werte (Secrets bleiben "
                "in n8n)."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="n8n_list_users",
            description="Listet die n8n-User der Instanz.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent]:
    try:
        result = await _dispatch(name, arguments or {})
    except Exception as exc:
        result = {"error": str(exc), "tool": name}
    return [
        types.TextContent(
            type="text", text=json.dumps(result, ensure_ascii=False, indent=2)
        )
    ]


async def _dispatch(name: str, a: dict[str, Any]) -> Any:
    if name == "n8n_list_workflows":
        return await client.list_workflows(
            active=a.get("active"),
            tags=a.get("tags"),
            name=a.get("name"),
            limit=a.get("limit", 50),
        )
    if name == "n8n_get_workflow":
        return await client.get_workflow(a["workflow_id"])
    if name == "n8n_create_workflow":
        return await client.create_workflow(a["workflow"])
    if name == "n8n_update_workflow":
        return await client.update_workflow(a["workflow_id"], a["workflow"])
    if name == "n8n_delete_workflow":
        return await client.delete_workflow(a["workflow_id"])
    if name == "n8n_activate_workflow":
        return await client.activate_workflow(a["workflow_id"])
    if name == "n8n_deactivate_workflow":
        return await client.deactivate_workflow(a["workflow_id"])
    if name == "n8n_list_executions":
        return await client.list_executions(
            workflow_id=a.get("workflow_id"),
            status=a.get("status"),
            include_data=a.get("include_data", False),
            limit=a.get("limit", 20),
        )
    if name == "n8n_get_execution":
        return await client.get_execution(
            a["execution_id"], include_data=a.get("include_data", True)
        )
    if name == "n8n_delete_execution":
        return await client.delete_execution(a["execution_id"])
    if name == "n8n_list_tags":
        return await client.list_tags(limit=a.get("limit", 100))
    if name == "n8n_list_credential_schemas":
        return await client.list_credentials_schemas()
    if name == "n8n_list_users":
        return await client.list_users()
    raise ValueError(f"Unbekanntes Tool: {name}")


def main() -> None:
    import asyncio

    if os.getenv("MCP_TRANSPORT", "stdio") == "sse":
        _run_sse()
    else:
        asyncio.run(mcp.server.stdio.run_server(server))


def _run_sse() -> None:
    import contextlib
    from collections.abc import AsyncIterator

    import httpx as _httpx
    import uvicorn
    from mcp.server.sse import SseServerTransport
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.routing import Mount, Route

    mcp_api_key = os.getenv("MCP_API_KEY", "")
    oidc_introspection_url = os.getenv("OIDC_INTROSPECTION_URL", "")
    oidc_client_id = os.getenv("OIDC_CLIENT_ID", "")
    oidc_client_secret = os.getenv("OIDC_CLIENT_SECRET", "")

    async def _is_authorized(request: Request) -> tuple[bool, str | None]:
        if not mcp_api_key:
            return True, None
        auth = request.headers.get("Authorization", "")
        if not auth:
            return False, "no_header"
        if auth == f"Bearer {mcp_api_key}":
            return True, None
        if not auth.startswith("Bearer "):
            return False, "invalid_token"
        if oidc_introspection_url and oidc_client_id and oidc_client_secret:
            jwt_token = auth[7:]
            try:
                async with _httpx.AsyncClient() as http:
                    resp = await http.post(
                        oidc_introspection_url,
                        data={"token": jwt_token},
                        auth=(oidc_client_id, oidc_client_secret),
                        timeout=5.0,
                    )
                    data = resp.json()
                    if data.get("active", False):
                        return True, None
                    return False, "invalid_token"
            except Exception as e:
                logging.error("Introspection fehlgeschlagen: %s", e)
                return False, "invalid_token"
        return False, "invalid_token"

    def _unauthorized(reason: str | None) -> Response:
        if reason == "invalid_token":
            www = (
                'Bearer realm="n8n-mcp", error="invalid_token", '
                'error_description="The access token expired or is invalid"'
            )
            return Response(
                "Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": www},
            )
        return Response("Unauthorized", status_code=401)

    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        ok, reason = await _is_authorized(request)
        if not ok:
            return _unauthorized(reason)
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )
        return Response()

    class _AlreadySent(Response):
        def __init__(self) -> None:
            super().__init__(content=b"", status_code=200)

        async def __call__(self, scope, receive, send):  # noqa: D401
            return

    session_manager = StreamableHTTPSessionManager(
        app=server,
        json_response=True,
    )

    async def handle_streamable_http(request: Request):
        ok, reason = await _is_authorized(request)
        if not ok:
            return _unauthorized(reason)
        await session_manager.handle_request(
            request.scope, request.receive, request._send
        )
        return _AlreadySent()

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            logging.info("StreamableHTTPSessionManager started")
            yield
            logging.info("StreamableHTTPSessionManager stopping")

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_streamable_http, methods=["POST"]),
            Route("/mcp", endpoint=handle_streamable_http, methods=["POST"]),
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ],
        lifespan=lifespan,
    )

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
