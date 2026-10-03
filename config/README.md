# Config

Runtime YAML for `misra-triage`. Full field reference: [docs/CONFIGURATION.md](../docs/CONFIGURATION.md).

## Files

| File | Role |
|------|------|
| `default.yaml` | Baseline path, gate policy, Jira settings, mapping paths |
| `owner_map.yaml` | Longest-prefix → SWC module, owner email, ASIL |
| `doors_map.yaml` | Longest-prefix → DOORS requirement ID |

## Usage

```bash
misra-triage triage --config config/default.yaml --report-dir samples/
misra-triage validate-config --config config/default.yaml
```

## Rules of thumb

- **Never** put API tokens in these files — use `JIRA_USER_EMAIL` / `JIRA_API_TOKEN`
- Keep `jira.dry_run: true` until sandbox-proven
- Prefer longer, more specific `prefix` values so nested SWCs win over broad trees
- Commit map updates with the software architecture change they reflect

## Minimal owner rule

```yaml
mappings:
  - prefix: src/app/brake
    swc: BrakeCtrl
    owner: team-chassis@example.com
    asil: D
```
