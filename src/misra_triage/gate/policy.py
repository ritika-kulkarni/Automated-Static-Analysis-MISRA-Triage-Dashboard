"""Policy engine that decides whether a merge must be blocked."""

from __future__ import annotations

from dataclasses import dataclass, field

from misra_triage.models.config import GatePolicyConfig
from misra_triage.models.violation import Violation
from misra_triage.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GateDecision:
    passed: bool
    blocking: list[Violation] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 0 if self.passed else 1


class GatePolicy:
    """Evaluates *new* violations only — baseline debt never blocks."""

    def __init__(self, config: GatePolicyConfig | None = None) -> None:
        self.config = config or GatePolicyConfig()

    def evaluate(self, new_violations: list[Violation]) -> GateDecision:
        blocking = [v for v in new_violations if self.is_blocking(v)]
        reasons: list[str] = []
        for violation in blocking:
            reasons.append(
                f"{violation.rule_id} @ {violation.location()} "
                f"[{violation.misra_category.value}/{violation.asil_level.value}]"
            )
        passed = not blocking
        if passed:
            logger.info("Merge gate PASSED — no new blocking violations")
        else:
            logger.error("Merge gate FAILED — %d blocking violation(s)", len(blocking))
            for reason in reasons:
                logger.error("  BLOCK: %s", reason)
        return GateDecision(passed=passed, blocking=blocking, reasons=reasons)

    def is_blocking(self, violation: Violation) -> bool:
        if violation.misra_category in self.config.block_misra_categories:
            return True
        if violation.asil_level in self.config.block_asil_levels:
            return True
        return False
