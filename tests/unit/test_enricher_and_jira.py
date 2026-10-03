from unittest.mock import MagicMock

import pytest
from tenacity import wait_none

from misra_triage.jira.client import JiraClient, JiraError
from misra_triage.jira.ticket_factory import TicketFactory
from misra_triage.mapping.enricher import ViolationEnricher
from misra_triage.models.config import JiraConfig
from misra_triage.models.violation import AsilLevel, MisraCategory, Violation


def test_enricher_maps_owner_doors_asil(tmp_config, sample_violation):
    enricher = ViolationEnricher(tmp_config.mapping)
    enriched = enricher.enrich(sample_violation)
    assert enriched.swc_module == "BrakeCtrl"
    assert enriched.owner == "team-chassis@example.com"
    assert enriched.doors_req_id == "REQ-BRK-003"
    assert enriched.asil_level == AsilLevel.D


def test_enricher_default_owner_for_unknown_path(tmp_config):
    enricher = ViolationEnricher(tmp_config.mapping)
    v = Violation(rule_id="rule-1.1", file_path="vendor/third_party/foo.c", line=1)
    enriched = enricher.enrich(v)
    assert enriched.owner == "unassigned"
    assert enriched.doors_req_id is None


def test_ticket_factory_groups_by_swc_and_doors(tmp_config):
    factory = TicketFactory(tmp_config.jira)
    violations = [
        Violation(
            rule_id="rule-9.1",
            file_path="src/app/brake/a.c",
            line=1,
            misra_category=MisraCategory.MANDATORY,
            asil_level=AsilLevel.D,
            swc_module="BrakeCtrl",
            owner="team-chassis@example.com",
            doors_req_id="REQ-BRK-003",
        ),
        Violation(
            rule_id="dir-4.12",
            file_path="src/app/brake/b.c",
            line=2,
            misra_category=MisraCategory.MANDATORY,
            asil_level=AsilLevel.D,
            swc_module="BrakeCtrl",
            owner="team-chassis@example.com",
            doors_req_id="REQ-BRK-003",
        ),
        Violation(
            rule_id="rule-21.3",
            file_path="src/app/hmi/c.c",
            line=3,
            misra_category=MisraCategory.MANDATORY,
            swc_module="HmiMgr",
            owner="team-hmi@example.com",
            doors_req_id="REQ-HMI-022",
        ),
    ]
    issues = factory.build_issues(violations)
    assert len(issues) == 2
    brake = next(i for i in issues if i["meta"]["swc_module"] == "BrakeCtrl")
    assert brake["meta"]["violation_count"] == 2
    assert "REQ-BRK-003" in brake["fields"]["summary"]


def test_jira_dry_run_does_not_call_network(tmp_config):
    client = JiraClient(tmp_config.jira)
    refs = client.create_issues(
        [{"fields": {"summary": "test", "project": {"key": "SWQ"}, "issuetype": {"name": "Bug"}}}]
    )
    assert len(refs) == 1
    assert refs[0].dry_run is True
    assert refs[0].key.startswith("DRY-")


def test_jira_create_issue_success(monkeypatch):
    cfg = JiraConfig(
        enabled=True,
        dry_run=False,
        base_url="https://jira.example.com",
        project_key="SWQ",
        max_retries=2,
    )
    monkeypatch.setenv(cfg.user_email_env, "bot@example.com")
    monkeypatch.setenv(cfg.api_token_env, "token")
    client = JiraClient(cfg)
    response = MagicMock()
    response.status_code = 201
    response.json.return_value = {"key": "SWQ-42"}
    client._session.post = MagicMock(return_value=response)
    refs = client.create_issues(
        [{"fields": {"summary": "x", "project": {"key": "SWQ"}, "issuetype": {"name": "Bug"}}}]
    )
    assert refs[0].key == "SWQ-42"
    assert "SWQ-42" in refs[0].url
    client._session.post.assert_called_once()


def test_jira_retries_on_500_then_fails(monkeypatch):
    cfg = JiraConfig(
        enabled=True,
        dry_run=False,
        base_url="https://jira.example.com",
        max_retries=2,
        timeout_seconds=1.0,
    )
    monkeypatch.setenv(cfg.user_email_env, "bot@example.com")
    monkeypatch.setenv(cfg.api_token_env, "token")
    client = JiraClient(cfg, wait=wait_none())
    response = MagicMock()
    response.status_code = 503
    response.text = "boom"
    client._session.post = MagicMock(return_value=response)
    with pytest.raises(JiraError):
        client.create_issues([{"fields": {"summary": "x"}}])
    assert client._session.post.call_count == 2
