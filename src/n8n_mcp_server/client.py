"""n8n REST API client."""

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

N8N_URL = os.getenv("N8N_URL", "").rstrip("/")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


def _check_config() -> None:
    if not N8N_URL or not N8N_API_KEY:
        raise RuntimeError(
            "N8N_URL und N8N_API_KEY müssen gesetzt sein. "
            "API-Key in n8n UI unter Settings → API → 'Create an API key' erzeugen."
        )


def _headers() -> dict[str, str]:
    return {
        "X-N8N-API-KEY": N8N_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    _check_config()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{N8N_URL}/api/v1{path}", params=params, headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def _post(path: str, json_body: Any | None = None) -> Any:
    _check_config()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{N8N_URL}/api/v1{path}", json=json_body, headers=_headers()
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}


async def _put(path: str, json_body: Any) -> Any:
    _check_config()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.put(
            f"{N8N_URL}/api/v1{path}", json=json_body, headers=_headers()
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}


async def _delete(path: str) -> Any:
    _check_config()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.delete(f"{N8N_URL}/api/v1{path}", headers=_headers())
        resp.raise_for_status()
        return resp.json() if resp.content else {"ok": True}


# ─── Workflows ──────────────────────────────────────────────────────────


async def list_workflows(
    active: bool | None = None,
    tags: str | None = None,
    name: str | None = None,
    limit: int | None = None,
) -> Any:
    params: dict[str, Any] = {}
    if active is not None:
        params["active"] = "true" if active else "false"
    if tags:
        params["tags"] = tags
    if name:
        params["name"] = name
    if limit:
        params["limit"] = limit
    return await _get("/workflows", params=params)


async def get_workflow(workflow_id: str) -> Any:
    return await _get(f"/workflows/{workflow_id}")


async def create_workflow(workflow: dict[str, Any]) -> Any:
    return await _post("/workflows", json_body=workflow)


async def update_workflow(workflow_id: str, workflow: dict[str, Any]) -> Any:
    return await _put(f"/workflows/{workflow_id}", json_body=workflow)


async def delete_workflow(workflow_id: str) -> Any:
    return await _delete(f"/workflows/{workflow_id}")


async def activate_workflow(workflow_id: str) -> Any:
    return await _post(f"/workflows/{workflow_id}/activate")


async def deactivate_workflow(workflow_id: str) -> Any:
    return await _post(f"/workflows/{workflow_id}/deactivate")


# ─── Executions ─────────────────────────────────────────────────────────


async def list_executions(
    workflow_id: str | None = None,
    status: str | None = None,
    include_data: bool = False,
    limit: int = 20,
) -> Any:
    params: dict[str, Any] = {"limit": limit}
    if workflow_id:
        params["workflowId"] = workflow_id
    if status:
        params["status"] = status
    if include_data:
        params["includeData"] = "true"
    return await _get("/executions", params=params)


async def get_execution(execution_id: str, include_data: bool = True) -> Any:
    params = {"includeData": "true"} if include_data else None
    return await _get(f"/executions/{execution_id}", params=params)


async def delete_execution(execution_id: str) -> Any:
    return await _delete(f"/executions/{execution_id}")


# ─── Tags, Credentials Meta, Users ──────────────────────────────────────


async def list_tags(limit: int = 100) -> Any:
    return await _get("/tags", params={"limit": limit})


async def list_credentials_schemas() -> Any:
    """Listet die verfügbaren Credential-Schemas (keine echten Credentials!)"""
    return await _get("/credentials/schema")


async def list_users() -> Any:
    return await _get("/users")
