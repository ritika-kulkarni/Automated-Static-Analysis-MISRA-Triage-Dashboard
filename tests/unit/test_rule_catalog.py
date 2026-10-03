from misra_triage.models.violation import AsilLevel, MisraCategory
from misra_triage.parsers.rule_catalog import (
    classify_asil,
    classify_misra_category,
    map_severity,
    normalize_rule_id,
)


def test_normalize_rule_id_variants():
    assert normalize_rule_id("MISRA C:2012 Rule-9.1") == "rule-9.1"
    assert normalize_rule_id("Dir_4.1") == "dir-4.1"
    assert normalize_rule_id("rule 17-3") == "rule-17.3"


def test_classify_mandatory_from_catalog_and_hint():
    assert classify_misra_category("rule-9.1") == MisraCategory.MANDATORY
    assert classify_misra_category("custom", "This is Mandatory") == MisraCategory.MANDATORY
    assert classify_misra_category("rule-8.4") == MisraCategory.REQUIRED
    assert classify_misra_category("rule-2.2", "advisory guidance") == MisraCategory.ADVISORY


def test_classify_asil_and_severity():
    assert classify_asil("ASIL-D critical path") == AsilLevel.D
    assert classify_asil("asil_qm") == AsilLevel.QM
    assert map_severity("error").value == "critical"
    assert map_severity("warning").value == "high"
