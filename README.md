# n8n-mcp-server

> MCP-Server für selbst gehostetes [n8n](https://n8n.io). Workflow-Lifecycle + Execution-Inspection aus Claude.

## Tools

| Tool | Zweck |
|---|---|
| `n8n_list_workflows` · `n8n_get_workflow` | Listen + Details |
| `n8n_create_workflow` · `n8n_update_workflow` · `n8n_delete_workflow` | CRUD |
| `n8n_activate_workflow` · `n8n_deactivate_workflow` | Trigger an/aus |
| `n8n_list_executions` · `n8n_get_execution` · `n8n_delete_execution` | Run-Inspection |
| `n8n_list_tags` · `n8n_list_credential_schemas` · `n8n_list_users` | Meta |

## Auth (identisch zu whisper-mcp / ntfy-mcp / hero-mcp)

1. **Statischer Bearer** (`MCP_API_KEY`) — Claude Desktop / direkte Clients
2. **JWT via Authelia OIDC Introspection** — Claude.ai

API-Key fürs Backend in n8n UI erstellen: Settings → API → "Create an API key".
