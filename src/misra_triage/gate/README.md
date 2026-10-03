# gate

Merge-policy evaluation for **new** violations only.

| Type | Role |
|------|------|
| `GatePolicy` | Applies `GatePolicyConfig` block lists |
| `GateDecision` | `passed`, `blocking`, `reasons`, `exit_code` |

Default: block new `mandatory` or ASIL `C`/`D`. Configure via YAML, not code, when possible.
