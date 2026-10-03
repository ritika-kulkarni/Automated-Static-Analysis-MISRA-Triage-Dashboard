"""Jira REST client with retries and dry-run support."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from misra_triage.models.config import JiraConfig
from misra_triage.utils.logging import get_logger

logger = get_logger(__name__)


class JiraError(RuntimeError):
    """Raised when Jira API interaction fails (non-retryable or exhausted)."""


class JiraRetryableError(JiraError):
    """Transient Jira/server failure eligible for retry."""


@dataclass
class JiraIssueRef:
    key: str
    url: str
    dry_run: bool = False
    meta: dict[str, Any] | None = None


class JiraClient:
    def __init__(self, config: JiraConfig, *, wait=None) -> None:
        self.config = config
        self._session = requests.Session()
        self._wait = wait or wait_exponential(multiplier=0.2, min=0.1, max=2)

    def create_issues(self, payloads: list[dict[str, Any]]) -> list[JiraIssueRef]:
        if not self.config.enabled:
            logger.info("Jira integration disabled — skipping ticket creation")
            return []

        created: list[JiraIssueRef] = []
        for payload in payloads:
            fields = payload.get("fields") or payload
            meta = payload.get("meta") or {}
            if self.config.dry_run:
                key = f"DRY-{len(created) + 1}"
                ref = JiraIssueRef(
                    key=key,
                    url=f"{self.config.base_url.rstrip('/')}/browse/{key}",
                    dry_run=True,
                    meta=meta,
                )
                logger.info("[dry-run] Would create Jira issue: %s", fields.get("summary"))
                created.append(ref)
                continue
            ref = self._create_one(fields, meta)
            created.append(ref)
        return created

    def _auth(self) -> tuple[str, str]:
        email = os.environ.get(self.config.user_email_env, "")
        token = os.environ.get(self.config.api_token_env, "")
        if not email or not token:
            raise JiraError(
                f"Missing Jira credentials. Set {self.config.user_email_env} "
                f"and {self.config.api_token_env}."
            )
        return email, token

    def _create_one(self, fields: dict[str, Any], meta: dict[str, Any]) -> JiraIssueRef:
        if not self.config.base_url:
            raise JiraError("jira.base_url is required when dry_run is false")

        @retry(
            reraise=True,
            stop=stop_after_attempt(self.config.max_retries),
            wait=self._wait,
            retry=retry_if_exception_type((requests.RequestException, JiraRetryableError)),
        )
        def _do_create() -> JiraIssueRef:
            url = f"{self.config.base_url.rstrip('/')}/rest/api/2/issue"
            response = self._session.post(
                url,
                json={"fields": fields},
                auth=self._auth(),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=self.config.timeout_seconds,
            )
            if response.status_code >= 500:
                raise JiraRetryableError(
                    f"Jira server error {response.status_code}: {response.text[:300]}"
                )
            if response.status_code >= 400:
                raise JiraError(f"Jira client error {response.status_code}: {response.text[:500]}")
            data = response.json()
            key = str(data.get("key") or "")
            if not key:
                raise JiraError(f"Jira response missing issue key: {data}")
            browse = f"{self.config.base_url.rstrip('/')}/browse/{key}"
            logger.info("Created Jira issue %s", key)
            return JiraIssueRef(key=key, url=browse, dry_run=False, meta=meta)

        return _do_create()
