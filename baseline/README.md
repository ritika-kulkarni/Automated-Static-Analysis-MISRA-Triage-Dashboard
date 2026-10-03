# Baseline store

Holds the accepted technical-debt snapshot produced by:

```bash
misra-triage update-baseline --config config/default.yaml --report-dir <reports>
```

| File | Description |
|------|-------------|
| `violations.json` | Fingerprinted findings treated as known debt |

**Merge gate rule:** findings present here never block CI. Only **new** fingerprints can fail the gate.

Commit this file with each reviewed baseline bump so all CI agents share the same debt set. See [User Guide](../docs/USER_GUIDE.md).
