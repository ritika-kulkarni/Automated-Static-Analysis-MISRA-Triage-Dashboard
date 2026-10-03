# Architecture

Detailed system design for **`misra-triage`**: a post-build CLI that turns Polyspace / QAC static-analysis noise into a baseline-aware merge gate and owner-mapped Jira tickets.

Related docs: [User Guide](USER_GUIDE.md) · [Configuration](CONFIGURATION.md) · [Development](DEVELOPMENT.md) · [Operations](OPERATIONS.md) · [ADRs](ADR.md)

---

## 1. Problem statement

Automotive static analysis (Polyspace Bug Finder / Helix QAC) produces thousands of findings per release drop. Manual triage of **new** vs **legacy** MISRA violations burns engineering time and lets Mandatory / ASIL-critical regressions slip into merges.

`misra-triage` solves this by:

1. Normalizing multi-tool reports into a single domain model  
2. Diffing against an accepted **baseline** of technical debt  
3. **Blocking CI** when new Mandatory or ASIL-C/D findings appear  
4. Opening **categorized Jira tickets** mapped to SWC owners and DOORS IDs  

### Goals / non-goals

| Goals | Non-goals |
|-------|-----------|
| Deterministic new-vs-legacy classification | Replacing Polyspace/QAC themselves |
| Fail-closed merge gate for safety-critical new debt | Interactive GUI (JSON is the dashboard contract) |
| Stable fingerprints across tool exporters | Perfect MISRA catalog completeness out of the box |
| Low-noise Jira (grouped by SWC/DOORS) | Full ALM/DOORS live API sync (YAML maps first) |

---

## 2. C4 — System context

```mermaid
C4Context
  title MISRA Triage — System Context
  Person(safety, "Safety / Quality Engineer", "Reviews debt, waives baseline bumps")
  Person(dev, "SWC Developer", "Fixes new Mandatory / ASIL findings")
  System(triage, "misra-triage", "Parses reports, diffs baseline, gates merges, opens Jira")
  System_Ext(ps, "Polyspace Bug Finder", "Produces SARIF/XML")
  System_Ext(qac, "Helix QAC", "Produces SARIF/XML")
  System_Ext(ci, "CI Platform", "Invokes CLI post-build")
  System_Ext(jira, "Jira", "Tracks categorized tickets")
  System_Ext(doors, "DOORS maps", "Requirement IDs via YAML")
  Rel(ci, triage, "Runs triage / update-baseline")
  Rel(ps, triage, "SARIF/XML reports")
  Rel(qac, triage, "SARIF/XML reports")
  Rel(triage, jira, "Creates issues (optional)")
  Rel(triage, doors, "Reads path→REQ maps")
  Rel(triage, ci, "Exit 0/1/2 + JSON artifact")
  Rel(safety, triage, "Configures gate & baseline")
  Rel(dev, jira, "Receives / resolves tickets")
```

If your Markdown renderer does not support C4, use the equivalent flowchart below.

```mermaid
flowchart LR
  subgraph People
    SE[Safety / Quality]
    DEV[SWC Developer]
  end
  subgraph CI_Build["CI / Post-build"]
    PS[Polyspace Bug Finder]
    QAC[Helix QAC]
    CLI[misra-triage CLI]
  end
  subgraph Artifacts
    SARIF[(SARIF / XML)]
    BASE[(baseline/violations.json)]
    RPT[(reports/triage_report.json)]
  end
  subgraph External
    JIRA[Jira]
    MAPS[Owner + DOORS YAML]
  end
  PS --> SARIF
  QAC --> SARIF
  SARIF --> CLI
  MAPS --> CLI
  BASE --> CLI
  CLI --> BASE
  CLI --> RPT
  CLI --> JIRA
  CLI -->|exit code| CI_Build
  SE --> CLI
  DEV --> JIRA
```

---

## 3. C4 — Containers

```mermaid
flowchart TB
  subgraph Container["misra-triage package"]
    CLI[CLI - Click]
    SVC[TriageService]
    PAR[Parser strategies]
    ENR[ViolationEnricher]
    BL[BaselineStore + Differ]
    GATE[GatePolicy]
    JIRA[TicketFactory + JiraClient]
  end
  CFG[(config YAML)]
  REP[(tool reports)]
  OUT[(triage_report.json)]
  BASE[(baseline JSON)]
  JR[(Jira REST)]

  REP --> CLI
  CFG --> CLI
  CLI --> SVC
  SVC --> PAR --> ENR --> BL --> GATE --> JIRA
  BL <--> BASE
  JIRA --> JR
  SVC --> OUT
```

---

## 4. Runtime pipeline (sequence)

```mermaid
sequenceDiagram
  autonumber
  participant CI as CI Job
  participant CLI as misra-triage
  participant P as Parsers
  participant E as Enricher
  participant B as BaselineStore
  participant D as Differ
  participant G as GatePolicy
  participant T as TicketFactory
  participant J as JiraClient

  CI->>CLI: triage --config ... --report-dir ...
  CLI->>P: detect_parser + parse each file
  P-->>CLI: List[Violation]
  CLI->>E: enrich_many (SWC / owner / DOORS / ASIL)
  CLI->>B: load()
  B-->>CLI: baseline violations
  CLI->>D: diff_violations(current, baseline)
  D-->>CLI: new / known / resolved
  CLI->>G: evaluate(new)
  alt blocking new findings
    G-->>CLI: FAILED + blocking list
    CLI->>T: build_issues(new)
    T-->>CLI: grouped payloads
    CLI->>J: create_issues (dry-run or REST)
    J-->>CLI: issue refs
    CLI-->>CI: exit 1 + triage_report.json
  else no blocking new findings
    G-->>CLI: PASSED
    CLI-->>CI: exit 0 + triage_report.json
  end
```

### Stage summary

| Stage | Input | Output | Failure mode |
|-------|-------|--------|--------------|
| Parse | Report paths | `Violation[]` | Unknown format → exit `2` (if strict) |
| Enrich | Violations + maps | Annotated violations | Missing map → `unassigned` / `UNKNOWN` |
| Diff | Current + baseline | new / known / resolved | Corrupt baseline → exit `2` |
| Gate | New violations | `GateDecision` | Blocking → exit `1` |
| Jira | New violations | Issue refs | 5xx retried; 4xx fail fast |
| Report | Full result | `triage_report.json` | Disk I/O error → exit `2` |

---

## 5. Component package map

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

| Package | Responsibility | Key types | README |
|---------|----------------|-----------|--------|
| `models/` | Domain + config (Pydantic) | `Violation`, `AppConfig`, `TriageReport` | [src/.../models/README](../src/misra_triage/models/README.md) |
| `parsers/` | Tool-format adapters (Strategy) | `ReportParser`, SARIF/XML parsers | [parsers/README](../src/misra_triage/parsers/README.md) |
| `baseline/` | Persist & diff technical debt | `BaselineStore`, `BaselineDiff` | [baseline/README](../src/misra_triage/baseline/README.md) |
| `gate/` | Merge policy | `GatePolicy`, `GateDecision` | [gate/README](../src/misra_triage/gate/README.md) |
| `mapping/` | Path → ownership / ASIL / DOORS | `ViolationEnricher` | [mapping/README](../src/misra_triage/mapping/README.md) |
| `jira/` | Ticket grouping + REST | `TicketFactory`, `JiraClient` | [jira/README](../src/misra_triage/jira/README.md) |
| `service.py` | Application facade | `TriageService` | — |
| `cli.py` | CI presentation | Click commands | — |

---

## 6. Domain model

```mermaid
classDiagram
  direction TB
  class Violation {
    +str rule_id
    +str message
    +str file_path
    +int line
    +int column
    +ViolationSeverity severity
    +MisraCategory misra_category
    +AsilLevel asil_level
    +ToolSource tool
    +str swc_module
    +str owner
    +str doors_req_id
    +str fingerprint
    +compute_fingerprint() str
    +is_blocking bool
  }
  class TriageSummary {
    +int total
    +int baseline
    +int new
    +int resolved
    +int blocking_new
    +int tickets_created
    +bool gate_passed
  }
  class TriageReport {
    +datetime generated_at
    +TriageSummary summary
    +List~Violation~ new_violations
    +List~Violation~ baseline_violations
    +List~Violation~ resolved_violations
    +List~Violation~ blocking_violations
    +List jira_issues
    +List~str~ errors
  }
  class GateDecision {
    +bool passed
    +List~Violation~ blocking
    +List~str~ reasons
    +exit_code int
  }
  class BaselineDiff {
    +List~Violation~ new
    +List~Violation~ known
    +List~Violation~ resolved
  }
  class AppConfig {
    +Path baseline_path
    +GatePolicyConfig gate
    +JiraConfig jira
    +MappingConfig mapping
  }
  TriageReport --> TriageSummary
  TriageReport --> Violation
  GateDecision --> Violation
  BaselineDiff --> Violation
  AppConfig --> GatePolicyConfig
  AppConfig --> JiraConfig
  AppConfig --> MappingConfig
```

### Fingerprint identity

```text
sha256( lower(rule_id) | normalize(path) | line | column | normalize(message) )
```

- Paths: `\` → `/`, strip `./`, lowercase  
- Messages: collapse whitespace, lowercase  
- Same logical finding ⇒ same fingerprint across drops  

### Diff set semantics

```mermaid
flowchart LR
  subgraph Current
    C1[Finding A]
    C2[Finding B]
    C3[Finding C]
  end
  subgraph Baseline
    B1[Finding A]
    B2[Finding D]
  end
  C1 -.->|known| K[Known debt]
  C2 -.->|new| N[New]
  C3 -.->|new| N
  B2 -.->|resolved| R[Resolved]
```

---

## 7. Parser strategy

```mermaid
flowchart TD
  F[Report path] --> D{detect_parser}
  D -->|*.sarif / JSON with runs| S[SarifParser]
  D -->|Polyspace XML heuristics| P[PolyspaceXmlParser]
  D -->|QAC / PRQA heuristics| Q[QacXmlParser]
  D -->|no match| X[ParseError]
  S --> V[Violation]
  P --> V
  Q --> V
  V --> CAT[rule_catalog classify MISRA + ASIL]
```

Probe order matters: SARIF first, then Polyspace XML, then QAC XML. Filename hints (`*qac*`, `*polyspace*`) break ties for ambiguous XML.

---

## 8. Merge-gate state machine

```mermaid
stateDiagram-v2
  [*] --> Parsing
  Parsing --> Enriching: ok
  Parsing --> ToolFailure: unreadable / unknown format
  Enriching --> Diffing
  Diffing --> Evaluating
  Evaluating --> Passed: no blocking new
  Evaluating --> Failed: Mandatory or ASIL-C/D new
  Failed --> Ticketing
  Ticketing --> Artifact
  Passed --> Artifact
  Artifact --> [*]
  ToolFailure --> [*]
```

Default block condition (new findings only):

```text
misra_category ∈ block_misra_categories  OR  asil_level ∈ block_asil_levels
```

Defaults: `mandatory` and `{C, D}`. Baseline debt never transitions to `Failed`.

---

## 9. Jira categorization

```mermaid
flowchart LR
  N[New violations] --> G[Group by SWC + owner + DOORS + category]
  G --> I1[Ticket: BrakeCtrl / REQ-BRK-003]
  G --> I2[Ticket: NvM / REQ-NVM-014]
  G --> I3[Ticket: HmiMgr / REQ-HMI-022]
```

Grouping key:

```text
(swc_module, owner, doors_req_id, misra_category)
```

Dry-run emits `DRY-n` keys without calling Jira REST.

---

## 10. Design patterns & SOLID

| Pattern / principle | Where | Why |
|---------------------|-------|-----|
| **Strategy** | `ReportParser` | Swap SARIF/XML without changing orchestration |
| **Facade** | `TriageService` | One entry for the pipeline |
| **Factory** | `TicketFactory` | Build categorized Jira payloads |
| **Policy** | `GatePolicy` | Declarative, testable merge rules |
| **SRP** | Package boundaries | Parsing ≠ gating ≠ ticketing |
| **OCP** | New parsers / YAML flags | Extend without rewriting the core |
| **DIP** | `detect_parser()` | Service depends on abstraction |

---

## 11. Reliability & error handling

```mermaid
flowchart TD
  A[Report file] --> B{Parser probe}
  B -->|unknown| E[ParseError → exit 2]
  B -->|known| C[Row-level parse]
  C -->|bad row| D[Log + skip]
  C -->|ok| F[Violation]
  F --> G[Enrich → Diff → Gate]
  G -->|fail| J[Jira create]
  J -->|5xx / network| K[Exponential backoff]
  J -->|4xx| L[Fail fast]
  G -->|pass| M[Write triage_report.json]
  J --> M
```

| Mechanism | Detail |
|-----------|--------|
| Per-row isolation | Corrupt SARIF/XML node ≠ abort whole file |
| Atomic baseline | Write `.tmp` then `replace()` |
| Selective retry | `JiraRetryableError` for 5xx only |
| Dry-run default | No production tickets until configured |
| Strict parse | `fail_on_parse_errors` fails the job on bad inputs |

---

## 12. Deployment / CI topology

```mermaid
flowchart TB
  subgraph Pipeline
    BLD[Build + unit tests]
    SA[Polyspace / QAC job]
    TR[misra-triage triage]
    ART[Upload triage_report.json]
  end
  BLD --> SA --> TR --> ART
  TR -->|exit 1| BLOCK[Block merge]
  TR -->|exit 0| OK[Allow merge]
  BASELINE[(Committed baseline/violations.json)] --> TR
```

Recommended: run triage **after** static analysis artifacts are published; commit baseline updates only via reviewed PRs.

---

## 13. Extension points

| Need | How |
|------|-----|
| New report format | Implement `ReportParser`, register in `detect_parser()` |
| Custom mandatory rules | Extend `rule_catalog.py` or tool properties |
| Different gate rules | Edit `gate.block_*` in YAML |
| Alt ticketing | Parallel client to `jira/`, wire in `TriageService` |
| Dashboard UI | Consume `reports/triage_report.json` |

---

## 14. Repository layout

```text
.
├── README.md
├── docs/                      # Architecture, guides, ADRs, ops
├── config/                    # Runtime YAML + README
├── samples/                   # Example tool exports + README
├── src/misra_triage/          # Application (+ per-package READMEs)
├── tests/                     # unit / integration / edge + README
├── baseline/                  # Accepted debt store + README
└── .github/workflows/ci.yml
```
