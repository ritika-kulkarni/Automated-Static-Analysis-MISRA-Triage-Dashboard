from misra_triage.baseline.differ import diff_violations
from misra_triage.baseline.store import BaselineStore
from misra_triage.gate.policy import GatePolicy
from misra_triage.models.config import GatePolicyConfig
from misra_triage.models.violation import AsilLevel, MisraCategory, Violation


def _v(rule: str, path: str, line: int, **kwargs) -> Violation:
    return Violation(rule_id=rule, file_path=path, line=line, message=f"{rule}:{line}", **kwargs)


def test_baseline_roundtrip(tmp_path):
    store = BaselineStore(tmp_path / "baseline.json")
    items = [_v("rule-1.1", "a.c", 1), _v("rule-2.2", "b.c", 2)]
    store.save(items, note="seed")
    loaded = store.load()
    assert len(loaded) == 2
    assert store.fingerprints() == {i.fingerprint for i in items}


def test_diff_new_known_resolved():
    baseline = [_v("rule-1.1", "a.c", 1), _v("rule-2.2", "b.c", 2)]
    current = [_v("rule-1.1", "a.c", 1), _v("rule-3.1", "c.c", 3)]
    diff = diff_violations(current, baseline)
    assert len(diff.new) == 1
    assert diff.new[0].rule_id == "rule-3.1"
    assert len(diff.known) == 1
    assert len(diff.resolved) == 1
    assert diff.resolved[0].rule_id == "rule-2.2"


def test_gate_blocks_new_mandatory_and_asil():
    policy = GatePolicy(GatePolicyConfig())
    new = [
        _v("rule-9.1", "a.c", 1, misra_category=MisraCategory.MANDATORY),
        _v("rule-8.4", "b.c", 2, misra_category=MisraCategory.REQUIRED, asil_level=AsilLevel.D),
        _v("rule-2.2", "c.c", 3, misra_category=MisraCategory.ADVISORY, asil_level=AsilLevel.A),
    ]
    decision = policy.evaluate(new)
    assert decision.passed is False
    assert len(decision.blocking) == 2
    assert decision.exit_code == 1


def test_gate_passes_when_only_legacy_style_new_advisory():
    policy = GatePolicy()
    decision = policy.evaluate(
        [_v("rule-2.2", "c.c", 3, misra_category=MisraCategory.ADVISORY, asil_level=AsilLevel.A)]
    )
    assert decision.passed is True
    assert decision.blocking == []
