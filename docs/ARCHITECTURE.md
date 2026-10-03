# Architecture

## 1. Problem statement

Automotive static analysis (Polyspace Bug Finder / Helix QAC) produces thousands of findings per release drop. Manual triage of **new** vs **legacy** MISRA violations burns engineering time and lets Mandatory / ASIL-critical regressions slip into merges.

`misra-triage` is a **post-build CLI** that:

1. Normalizes multi-tool reports into a single domain model
2. Diffs against an accepted **baseline** of technical debt
3. **Blocks CI** when new Mandatory or ASIL-C/D findings appear
4. Opens **categorized Jira tickets** mapped to SWC owners and DOORS IDs

## 2. Context (C4 container view)

```mermaid
flowchart LR
  subgraph Build["CI / Post-build"]
    PS[Polyspace Bug Finder]
    QAC[Helix QAC]
    CLI[misra-triage CLI]
  end

  subgraph Artifacts["Artifacts"]
    SARIF[(SARIF / XML reports)]
    BASE[(baseline/violations.json)]
    RPT[(reports/triage_report.json)]
  end

  subgraph Ext["External systems"]
    JIRA[Jira]
    DOORS[DOORS req map YAML]
    OWN[SWC owner map YAML]
  end

  PS --> SARIF
  QAC --> SARIF
  SARIF --> CLI
  BASE --> CLI
  OWN --> CLI
  DOORS --> CLI
  CLI --> BASE
  CLI --> RPT
  CLI --> JIRA
  CLI -->|exit 0/1/2| Build
```

## 3. Pipeline (runtime sequence)

```mermaid
sequenceDiagram
  participant CI as CI Job
  participant CLI as misra-triage
  participant P as Parsers
  participant E as Enricher
  participant B as BaselineStore
  participant D as Differ
  participant G as GatePolicy
  participant J as JiraClient

  CI->>CLI: triage --report-dir ...
  CLI->>P: detect + parse each report
  P-->>CLI: List[Violation]
  CLI->>E: enrich (SWC / owner / DOORS / ASIL)
  CLI->>B: load baseline
  CLI->>D: diff(current, baseline)
  D-->>CLI: new / known / resolved
  CLI->>G: evaluate(new)
  alt blocking new findings
    G-->>CLI: FAILED
    CLI->>J: create grouped tickets
    CLI-->>CI: exit 1 + triage_report.json
  else clean or non-blocking only
    G-->>CLI: PASSED
    CLI-->>CI: exit 0 + triage_report.json
  end
```

## 4. Component package map

```mermaid
flowchart TB
  CLI[cli.py] --> SVC[service.py]
  SVC --> PAR[parsers/]
  SVC --> MAP[mapping/]
  SVC --> BL[baseline/]
  SVC --> GATE[gate/]
  SVC --> JIRA[jira/]
  PAR --> MOD[models/]
  MAP --> MOD
  BL --> MOD
  GATE --> MOD
  JIRA --> MOD
  SVC --> MOD
  PAR --> UTIL[utils/]
  JIRA --> UTIL
  CLI --> UTIL
```

| Package | Responsibility | Key types |
|---------|----------------|-----------|
| `models/` | Domain + config (Pydantic) | `Violation`, `AppConfig`, `TriageReport` |
| `parsers/` | Tool-format adapters (Strategy) | `ReportParser`, `SarifParser`, `PolyspaceXmlParser`, `QacXmlParser` |
| `baseline/` | Persist & diff technical debt | `BaselineStore`, `BaselineDiff` |
| `gate/` | Merge policy | `GatePolicy`, `GateDecision` |
| `mapping/` | Path → ownership / ASIL / DOORS | `ViolationEnricher` |
| `jira/` | Ticket grouping + REST | `TicketFactory`, `JiraClient` |
| `service.py` | Application service / facade | `TriageService` |
| `cli.py` | Presentation / CI interface | Click commands |

## 5. Domain model

```mermaid
classDiagram
  class Violation {
    +str rule_id
    +str file_path
    +int line
    +MisraCategory misra_category
    +AsilLevel asil_level
    +str fingerprint
    +str swc_module
    +str owner
    +str doors_req_id
    +compute_fingerprint()
    +is_blocking
  }

  class TriageReport {
    +TriageSummary summary
    +List~Violation~ new_violations
    +List~Violation~ blocking_violations
    +List jira_issues
  }

  class GateDecision {
    +bool passed
    +List~Violation~ blocking
    +exit_code
  }

  class BaselineDiff {
    +List~Violation~ new
    +List~Violation~ known
    +List~Violation~ resolved
  }

  TriageReport --> Violation
  GateDecision --> Violation
  BaselineDiff --> Violation
```

### Fingerprint identity

A finding’s stable ID is:

```text
sha256( rule_id | normalized_path | line | column | normalized_message )
```

Paths are lowercased and slash-normalized; messages are whitespace-collapsed. This keeps baseline comparison deterministic across tool exporters.

## 6. Design patterns & SOLID

| Pattern / principle | Where | Why |
|---------------------|-------|-----|
| **Strategy** | `ReportParser` implementations | Swap SARIF/XML without changing orchestration |
| **Facade** | `TriageService` | Single entry for parse → enrich → diff → gate → Jira |
| **Factory** | `TicketFactory` | Build categorized Jira payloads from violation groups |
| **Policy** | `GatePolicy` | Keep merge rules declarative and testable |
| **SRP** | Package boundaries | Parsing ≠ gating ≠ ticketing |
| **OCP** | New parsers / policy flags | Extend via new classes or YAML, not rewrites |
| **DIP** | Service depends on abstractions | Parsers selected via `detect_parser()` |

## 7. Reliability mechanisms

```mermaid
flowchart TD
  A[Report file] --> B{Parser probe}
  B -->|unknown format| E[ParseError → exit 2]
  B -->|known| C[Row-level parse]
  C -->|bad row| D[Log + skip row]
  C -->|ok| F[Violation]
  F --> G[Enrich]
  G --> H[Diff vs baseline]
  H --> I{Gate}
  I -->|fail| J[Jira create with retry]
  J -->|5xx| K[Exponential backoff]
  J -->|4xx| L[Fail fast]
  I -->|pass| M[Write triage_report.json]
  J --> M
```

- **Per-row isolation** — one corrupt SARIF/XML node does not abort the whole report
- **Atomic baseline writes** — `.tmp` + rename
- **Retryable Jira errors only** — HTTP 5xx / transport; 4xx not retried
- **Dry-run default** — no tickets against production until explicitly enabled
- **Strict parse mode** — `gate.fail_on_parse_errors` fails the job when a file cannot be read

## 8. Merge-gate policy

Default policy blocks a merge when **any new** finding has:

- `misra_category == mandatory`, **or**
- `asil_level ∈ {C, D}`

Baseline (known) debt is never blocking. Advisory / Required findings at ASIL A/B do not fail the gate unless you change `config/default.yaml`.

## 9. Jira categorization

New violations are grouped by:

```text
(swc_module, owner, doors_req_id, misra_category)
```

Each group becomes one issue so SWC owners receive a single triage ticket per drop instead of one ticket per finding.

## 10. Extension points

| Need | Extension |
|------|-----------|
| New report format | Implement `ReportParser`, register in `detect_parser()` |
| Custom mandatory rules | Extend `parsers/rule_catalog.py` or enrich from tool properties |
| Different gate rules | Edit `gate.block_misra_categories` / `block_asil_levels` |
| Alt ticketing (Azure DevOps, etc.) | Add a client parallel to `jira/` and call from `TriageService` |
| Dashboard UI | Consume `reports/triage_report.json` (already dashboard-shaped) |

## 11. Repository layout

```text
.
├── README.md                 # Project entry
├── docs/                     # Architecture & guides
├── config/                   # Runtime YAML
├── samples/                  # Example tool exports
├── src/misra_triage/         # Application package
├── tests/                    # unit / integration / edge
├── baseline/                 # Accepted debt store (generated/committed per project)
├── reports/                  # Triage JSON artifact (CI)
└── .github/workflows/ci.yml  # Multi-Python CI
```
