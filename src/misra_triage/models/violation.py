"""Canonical violation model shared across parsers, baseline, gate, and Jira."""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ToolSource(str, Enum):
    POLYSPACE = "polyspace"
    QAC = "qac"
    SARIF = "sarif"
    UNKNOWN = "unknown"


class ViolationSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"


class MisraCategory(str, Enum):
    """MISRA C:2012 guideline categories."""

    MANDATORY = "mandatory"
    REQUIRED = "required"
    ADVISORY = "advisory"
    UNKNOWN = "unknown"


class AsilLevel(str, Enum):
    """ISO 26262 ASIL classification used for merge gating."""

    QM = "QM"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    UNKNOWN = "UNKNOWN"


class Violation(BaseModel):
    """Normalized static-analysis finding independent of tool format."""

    rule_id: str = Field(..., min_length=1, description="MISRA / tool rule identifier")
    message: str = Field(default="", description="Human-readable violation message")
    file_path: str = Field(..., min_length=1)
    line: int = Field(default=0, ge=0)
    column: int = Field(default=0, ge=0)
    severity: ViolationSeverity = ViolationSeverity.UNKNOWN
    misra_category: MisraCategory = MisraCategory.UNKNOWN
    asil_level: AsilLevel = AsilLevel.UNKNOWN
    tool: ToolSource = ToolSource.UNKNOWN
    swc_module: str | None = None
    doors_req_id: str | None = None
    owner: str | None = None
    fingerprint: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("file_path", "rule_id", mode="before")
    @classmethod
    def _strip_required(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    def model_post_init(self, __context: Any) -> None:
        if not self.fingerprint:
            object.__setattr__(self, "fingerprint", self.compute_fingerprint())

    def compute_fingerprint(self) -> str:
        """
        Stable identity for baseline comparison.

        Location (file:line:column) is included so relocated/duplicated
        findings are treated as distinct; rule + message keep semantics.
        """
        payload = "|".join(
            [
                self.rule_id.lower(),
                _normalize_path(self.file_path),
                str(self.line),
                str(self.column),
                _normalize_message(self.message),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def is_blocking(self) -> bool:
        """True when the finding must block a merge under default policy."""
        return self.misra_category == MisraCategory.MANDATORY or self.asil_level in {
            AsilLevel.C,
            AsilLevel.D,
        }

    def location(self) -> str:
        return f"{self.file_path}:{self.line}:{self.column}"


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./").lower()


def _normalize_message(message: str) -> str:
    return " ".join(message.split()).lower()
