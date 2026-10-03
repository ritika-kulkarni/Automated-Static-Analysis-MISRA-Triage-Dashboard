"""Application configuration models loaded from YAML + environment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from misra_triage.models.violation import AsilLevel, MisraCategory


class GatePolicyConfig(BaseModel):
    """Merge-gate policy: which findings block the pipeline."""

    block_misra_categories: list[MisraCategory] = Field(
        default_factory=lambda: [MisraCategory.MANDATORY]
    )
    block_asil_levels: list[AsilLevel] = Field(
        default_factory=lambda: [AsilLevel.C, AsilLevel.D]
    )
    fail_on_parse_errors: bool = True
    allow_empty_reports: bool = False


class JiraConfig(BaseModel):
    """Jira REST integration settings."""

    enabled: bool = False
    dry_run: bool = True
    base_url: str = ""
    project_key: str = "SWQ"
    issue_type: str = "Bug"
    api_token_env: str = "JIRA_API_TOKEN"
    user_email_env: str = "JIRA_USER_EMAIL"
    max_retries: int = 3
    timeout_seconds: float = 30.0
    labels: list[str] = Field(default_factory=lambda: ["misra-triage", "static-analysis"])


class MappingConfig(BaseModel):
    """Maps source paths to SWC owners and DOORS requirement IDs."""

    owner_map_path: Path | None = None
    doors_map_path: Path | None = None
    default_owner: str = "unassigned"
    default_asil: AsilLevel = AsilLevel.UNKNOWN


class AppConfig(BaseModel):
    """Top-level runtime configuration."""

    baseline_path: Path = Path("baseline/violations.json")
    report_output_dir: Path = Path("reports")
    gate: GatePolicyConfig = Field(default_factory=GatePolicyConfig)
    jira: JiraConfig = Field(default_factory=JiraConfig)
    mapping: MappingConfig = Field(default_factory=MappingConfig)
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.upper()


class EnvSecrets(BaseSettings):
    """Secrets injected from environment (never stored in YAML)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jira_api_token: str | None = None
    jira_user_email: str | None = None


def load_config(path: Path | None) -> AppConfig:
    """Load AppConfig from YAML, falling back to defaults when path is None."""
    if path is None:
        return AppConfig()
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}
    return AppConfig.model_validate(raw)
