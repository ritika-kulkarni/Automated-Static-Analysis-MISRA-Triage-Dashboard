# utils

Cross-cutting helpers.

| Module | Role |
|--------|------|
| `logging.py` | Rich console logging setup |
| `retry.py` | Tenacity decorator helper (`retryable`) |

Prefer package-local retry policies (e.g. Jira client) when wait/stop must be injectable for tests.
