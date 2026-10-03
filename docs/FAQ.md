# FAQ

### Why did a finding I thought was baseline suddenly block the gate?

Fingerprints include path, line, column, and normalized message. If the tool changed wording, or the line shifted, it looks **new**. Compare fingerprints in `baseline/violations.json` vs `triage_report.json`.

### Does the gate block Required or Advisory MISRA?

Not by default — only **Mandatory** (and ASIL-C/D). Expand `gate.block_misra_categories` if your program needs more.

### Can I run without Jira?

Yes: `--no-jira`, or set `jira.enabled: false`. Gate and report still run.

### What if owner/DOORS maps miss a path?

Owner becomes `default_owner` (usually `unassigned`); DOORS ID stays empty/`NO-DOORS` in tickets. Fix the YAML prefixes.

### SARIF from another tool — will it work?

If it is SARIF 2.1 with `runs[].results[]`, `SarifParser` should work. MISRA/ASIL classification depends on rule IDs, messages, and properties/tags.

### Should `baseline/violations.json` be committed?

Yes for shared CI. Treat baseline bumps as reviewed changes (like lockfiles).

### Exit code 1 vs 2?

`1` = quality gate (new blocking findings). `2` = tool/config/parse failure. Do not auto-retry `1` as infrastructure flake.

### How do I seed the first baseline?

```bash
misra-triage update-baseline --config config/default.yaml --report-dir <analysis-out>
git add baseline/violations.json && git commit -m "Seed MISRA baseline for release X"
```
