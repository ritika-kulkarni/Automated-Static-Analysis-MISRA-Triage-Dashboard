# reports/

CI/local output directory for triage artifacts.

| Artifact | Produced by | Purpose |
|----------|-------------|---------|
| `triage_report.json` | `misra-triage triage` | Dashboard contract — summary, new/blocking findings, Jira refs |

This directory is **gitignored** (except this README). Upload the JSON as a build artifact in CI.

Schema shape: see `TriageReport.to_dashboard_dict()` in `src/misra_triage/models/triage_result.py` and [Architecture](../docs/ARCHITECTURE.md).
