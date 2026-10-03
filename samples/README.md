# Sample reports

Illustrative Polyspace / QAC exports used for local demos and integration tests.

| File | Format | Tool | Findings (approx.) |
|------|--------|------|--------------------|
| `polyspace_bugfinder.sarif` | SARIF 2.1 | Polyspace Bug Finder | Mandatory + Required, ASIL tags |
| `polyspace_results.xml` | XML | Polyspace Bug Finder | `Check` / `Result` nodes |
| `qac_report.xml` | XML | Helix QAC | `Diagnostic` / `Message` nodes |

## Try them

```bash
misra-triage update-baseline --config config/default.yaml --report-dir samples/
misra-triage triage --config config/default.yaml --report-dir samples/
```

After seeding the baseline, triage should **PASS** (zero new findings).

## Replacing with real exports

Point `--report` / `--report-dir` at your CI artifact directory. Supported extensions:

- `.sarif` / `.json` (SARIF with a top-level `runs` array)
- `.xml` (Polyspace Bug Finder or QAC/PRQA-style diagnostics)

Parser selection is automatic; see [Architecture § parsers](../docs/ARCHITECTURE.md).

## Note

These fixtures are **synthetic** and do not represent a real ECU codebase. Paths under `src/bsw/...` and `src/app/...` align with the example maps in `config/`.
