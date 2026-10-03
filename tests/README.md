# Tests

Testing strategy overview: [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md).

## Layout

```text
tests/
├── conftest.py          # Shared fixtures (tmp config, sample Violation)
├── unit/                # Fast, isolated
├── integration/         # Full pipeline + CLI
└── edge/                # Malformed / corrupt inputs
```

```mermaid
flowchart LR
  U[unit] --> I[integration]
  I --> E[edge]
```

| Suite | Marker | What it proves |
|-------|--------|----------------|
| `unit/` | — | Fingerprints, parsers, differ, gate, enricher, Jira client |
| `integration/` | `integration` | Sample reports → baseline → gate → tickets → CLI |
| `edge/` | `edge` | Corrupt baseline, partial SARIF, unknown formats |

## Run

```bash
# All tests + coverage
pytest --cov=misra_triage --cov-report=term-missing

# Subsets
pytest tests/unit -q
pytest -m integration -q
pytest -m edge -q
```

Coverage floor: **80%** (configured in `pyproject.toml`).

## Fixtures

- `samples_dir` — path to [`samples/`](../samples/)
- `tmp_config` — isolated `AppConfig` with temp owner/DOORS maps and baseline path
- `sample_violation` — Mandatory / ASIL-D brake finding for enricher tests

## Writing new tests

1. Prefer pure unit tests for policy and parsing edge cases  
2. Use `tmp_path` for baseline/report files — do not mutate committed `baseline/`  
3. Mock `JiraClient._session.post` for HTTP — do not call real Jira  
4. Mark slow/E2E cases with `@pytest.mark.integration`  
