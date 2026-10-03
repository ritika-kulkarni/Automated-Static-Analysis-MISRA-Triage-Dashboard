# Architecture Decision Records

Lightweight ADRs for `misra-triage`. Newest first.

---

## ADR-004 — Group Jira tickets by SWC / DOORS / category

**Status:** Accepted  

**Context:** One Jira issue per finding creates unusable noise (thousands of tickets).  

**Decision:** Group new violations by `(swc_module, owner, doors_req_id, misra_category)` via `TicketFactory`.  

**Consequences:** Owners get one actionable ticket per drop/category; individual findings listed in the description (capped).  

---

## ADR-003 — Fingerprint includes location + message

**Status:** Accepted  

**Context:** Need stable identity across drops without tool-specific IDs.  

**Decision:**  

```text
sha256(rule_id | normalized_path | line | column | normalized_message)
```

**Consequences:** Relocations and message-text changes appear as new findings (safe/fail-closed). Pure whitespace/casing changes do not.  

---

## ADR-002 — Gate evaluates only *new* findings

**Status:** Accepted  

**Context:** Legacy MISRA debt cannot be cleared in one sprint; blocking on total count freezes delivery.  

**Decision:** `GatePolicy` receives only the diff `new` set. Baseline debt never fails the gate.  

**Consequences:** Requires disciplined `update-baseline` after reviewed waivers; prevents endless red CI on inherited debt.  

---

## ADR-001 — Strategy parsers + normalized Violation model

**Status:** Accepted  

**Context:** Polyspace and QAC export SARIF and multiple XML shapes.  

**Decision:** Introduce `ReportParser` strategy interface and a Pydantic `Violation` as the ubiquitous language past the parser boundary.  

**Consequences:** New formats plug in without touching gate/Jira; tests can inject fixtures as `Violation` lists.  

---

## ADR-000 — CLI-first, JSON artifact as dashboard contract

**Status:** Accepted  

**Context:** Need CI-native integration before investing in a UI.  

**Decision:** Ship Click CLI with exit codes; write `triage_report.json` as the dashboard/API surface.  

**Consequences:** Any UI (Streamlit, Grafana, custom) can consume the artifact without coupling to Python internals.  
