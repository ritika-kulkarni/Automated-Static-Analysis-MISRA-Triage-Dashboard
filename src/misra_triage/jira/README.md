# jira

Ticket creation for new findings.

| Module | Role |
|--------|------|
| `ticket_factory.py` | Groups violations → Jira field payloads |
| `client.py` | REST create with dry-run + selective retry |

```mermaid
flowchart LR
  V[New violations] --> F[TicketFactory]
  F --> C[JiraClient]
  C -->|dry_run| D[DRY-n refs]
  C -->|live| R[POST /rest/api/2/issue]
```

Credentials: env vars named in `jira.api_token_env` / `jira.user_email_env` (never YAML).
