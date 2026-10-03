# models

Pydantic domain models — the ubiquitous language of the pipeline.

| Module | Types |
|--------|-------|
| `violation.py` | `Violation`, `MisraCategory`, `AsilLevel`, `ToolSource`, `ViolationSeverity` |
| `config.py` | `AppConfig`, `GatePolicyConfig`, `JiraConfig`, `MappingConfig`, `load_config()` |
| `triage_result.py` | `TriageReport`, `TriageSummary` |

`Violation.fingerprint` is computed on init if omitted. Prefer constructing models in tests over raw dicts.
