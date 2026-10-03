# Configuration Reference

All runtime knobs live under [`config/`](../config/). Secrets never go in YAML.

## Files

| File | Purpose |
|------|---------|
| [`default.yaml`](../config/default.yaml) | App, gate, Jira, mapping paths |
| [`owner_map.yaml`](../config/owner_map.yaml) | Path prefix → SWC, owner, ASIL |
| [`doors_map.yaml`](../config/doors_map.yaml) | Path prefix → DOORS requirement ID |

Load with `--config path/to.yaml`.

## `default.yaml`

### Top-level

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `baseline_path` | path | `baseline/violations.json` | Accepted debt store |
| `report_output_dir` | path | `reports` | Where `triage_report.json` is written |
| `log_level` | str | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

### `gate`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `block_misra_categories` | list | `[mandatory]` | New findings in these categories fail the gate |
| `block_asil_levels` | list | `[C, D]` | New findings at these ASIL levels fail the gate |
| `fail_on_parse_errors` | bool | `true` | Abort on unreadable/unknown reports |
| `allow_empty_reports` | bool | `false` | Permit zero parseable rows without warning noise |

### `jira`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `true` | Master switch |
| `dry_run` | bool | `true` | Log/DRY keys only — **keep true until sandbox-validated** |
| `base_url` | URL | — | e.g. `https://jira.example.com` |
| `project_key` | str | `SWQ` | Jira project |
| `issue_type` | str | `Bug` | Issue type name |
| `api_token_env` | str | `JIRA_API_TOKEN` | Env var holding API token |
| `user_email_env` | str | `JIRA_USER_EMAIL` | Env var holding bot email |
| `max_retries` | int | `3` | Attempts for retryable failures |
| `timeout_seconds` | float | `30` | HTTP timeout |
| `labels` | list | `misra-triage`, … | Base labels; SWC/DOORS labels added automatically |

### `mapping`

| Key | Type | Description |
|-----|------|-------------|
| `owner_map_path` | path | YAML for SWC/owner/ASIL |
| `doors_map_path` | path | YAML for DOORS IDs |
| `default_owner` | str | Used when no prefix matches |
| `default_asil` | enum | Fallback ASIL (`UNKNOWN`, `QM`, `A`–`D`) |

## Owner map format

Longest-prefix match wins.

```yaml
mappings:
  - prefix: src/app/brake
    swc: BrakeCtrl
    owner: team-chassis@example.com
    asil: D
```

Matching rules:

- Paths normalized to `/`
- `file == prefix` or `file.startswith(prefix + "/")`

## DOORS map format

```yaml
mappings:
  - prefix: src/app/brake
    doors_id: REQ-BRK-003
    swc: BrakeCtrl          # optional
```

## Environment secrets

```bash
export JIRA_USER_EMAIL="bot@example.com"
export JIRA_API_TOKEN="<api-token>"
```

Use CI secret stores; never commit `.env` with real tokens (`.env` is gitignored).

## Gate policy examples

**Stricter** — also block new Required:

```yaml
gate:
  block_misra_categories: [mandatory, required]
  block_asil_levels: [B, C, D]
```

**ASIL-D program only**:

```yaml
gate:
  block_misra_categories: [mandatory]
  block_asil_levels: [D]
```

## Validate

```bash
misra-triage validate-config --config config/default.yaml
```
