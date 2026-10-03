# Operations Runbook

Day-2 operations for running `misra-triage` in CI and release trains.

## Health checklist

| Check | Command / signal | Healthy |
|-------|------------------|---------|
| Config valid | `misra-triage validate-config --config …` | Prints `Configuration OK` |
| Parsers work | Triage log lines `Parsed N violation(s)…` | N > 0 or empty allowed by policy |
| Baseline present | `baseline/violations.json` exists in repo | Loaded without `Corrupt baseline` |
| Gate outcome | Exit code + summary table | `0` / `1` expected; `2` = tooling incident |
| Artifact | `reports/triage_report.json` | Written each triage run |
| Jira | `dry_run` keys or real issue keys | No credential errors |

## Exit codes (ops view)

| Code | Severity | Action |
|------|----------|--------|
| `0` | OK | Merge allowed |
| `1` | Quality gate | Assign Jira / fix code; do **not** treat as infra failure |
| `2` | Tooling | Page CI/tooling owner — bad config, corrupt baseline, unreadable reports |

## Incident playbooks

### Gate failing on every PR (`exit 1`)

1. Open `reports/triage_report.json` → `blocking_violations`  
2. Confirm findings are truly **new** (not a baseline path/fingerprint drift)  
3. If tool upgraded and messages changed, fingerprints may churn — consider a reviewed baseline refresh  
4. Fix code or waive via safety process + `update-baseline`  

### Sudden `exit 2` after tool upgrade

1. Run with `--report` on a single file; check parser selection in logs  
2. Validate SARIF has top-level `runs`  
3. For XML, confirm root/nodes still match Polyspace/QAC heuristics  
4. Temporarily set `gate.fail_on_parse_errors: false` **only** to unblock investigation  

### Jira spam / missing tickets

1. Confirm `jira.enabled` and `dry_run`  
2. Check grouping — many findings in one SWC → one ticket (expected)  
3. Verify owner/DOORS maps still match source tree prefixes  
4. For REST failures: inspect 4xx body (fields/assignee); 5xx retries automatically  

### Baseline drift across agents

- Always **commit** `baseline/violations.json`  
- Never generate divergent baselines on ephemeral runners without pushing  

## Observability

Logs use Rich-formatted stderr. Key phrases:

- `Selected parser …` / `Parsed N violation(s)`  
- `Merge gate PASSED` / `Merge gate FAILED`  
- `BLOCK: <rule> @ <file:line>`  
- `[dry-run] Would create Jira issue` / `Created Jira issue`  

JSON artifact fields for dashboards: `summary.*`, `blocking_violations`, `jira_issues`, `errors`.

## Rollback

| Change | Rollback |
|--------|----------|
| Bad baseline bump | `git revert` the baseline commit |
| Bad gate tightening | Revert `config/default.yaml` `gate` section |
| Bad Jira enablement | Set `jira.dry_run: true` or `enabled: false` |

## Capacity notes

- Parsing is linear in report size; typical automotive SARIF drops finish in seconds  
- Jira calls are one HTTP POST **per group**, not per finding  
- Baseline JSON grows with accepted debt — still small vs source trees  
