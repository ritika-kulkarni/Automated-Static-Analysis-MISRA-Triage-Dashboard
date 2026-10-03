# Documentation Index

Guides for the **Automated Static Analysis & MISRA Triage** CLI (`misra-triage`).

## Start here

| Document | Audience | Description |
|----------|----------|-------------|
| [Architecture](ARCHITECTURE.md) | Architects, maintainers | C4 views, sequences, domain model, gate FSM, patterns |
| [User Guide](USER_GUIDE.md) | CI owners, safety engineers | CLI usage, workflows, exit codes |
| [Configuration](CONFIGURATION.md) | Integrators | YAML knobs, owner/DOORS maps, secrets |
| [Operations](OPERATIONS.md) | SRE / CI maintainers | Runbook, incidents, rollback |
| [Development](DEVELOPMENT.md) | Contributors | Setup, tests, extension points |
| [ADRs](ADR.md) | Architects | Key design decisions |
| [FAQ](FAQ.md) | Everyone | Common questions |

## Folder READMEs

| Path | Topic |
|------|-------|
| [../README.md](../README.md) | Project entry + quick start |
| [../config/README.md](../config/README.md) | Config file map |
| [../samples/README.md](../samples/README.md) | Sample Polyspace/QAC reports |
| [../tests/README.md](../tests/README.md) | Test layout & strategy |
| [../baseline/README.md](../baseline/README.md) | Accepted debt store |
| [../src/misra_triage/README.md](../src/misra_triage/README.md) | Application package map |
| [../src/misra_triage/parsers/README.md](../src/misra_triage/parsers/README.md) | Parser strategies |
| [../src/misra_triage/gate/README.md](../src/misra_triage/gate/README.md) | Merge gate |
| [../src/misra_triage/jira/README.md](../src/misra_triage/jira/README.md) | Jira integration |

## Diagram legend

Most diagrams use [Mermaid](https://mermaid.js.org/) and render on GitHub, GitLab, and VS Code/Cursor Markdown previews.
