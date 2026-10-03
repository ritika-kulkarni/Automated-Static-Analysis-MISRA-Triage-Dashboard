# baseline (package)

In-code baseline persistence and diffing (distinct from repo-root `baseline/` data dir).

| Module | Role |
|--------|------|
| `store.py` | `BaselineStore` — load/save JSON, atomic write |
| `differ.py` | `diff_violations()` → `BaselineDiff` (new / known / resolved) |

Comparison key: `Violation.fingerprint`. See [ARCHITECTURE § fingerprint](../../../docs/ARCHITECTURE.md).
