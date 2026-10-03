"""Diff current findings against the accepted baseline."""

from __future__ import annotations

from dataclasses import dataclass, field

from misra_triage.models.violation import Violation


@dataclass
class BaselineDiff:
    current: list[Violation] = field(default_factory=list)
    baseline: list[Violation] = field(default_factory=list)
    new: list[Violation] = field(default_factory=list)
    known: list[Violation] = field(default_factory=list)
    resolved: list[Violation] = field(default_factory=list)

    @property
    def has_new(self) -> bool:
        return bool(self.new)


def diff_violations(
    current: list[Violation],
    baseline: list[Violation],
) -> BaselineDiff:
    """
    Compare by fingerprint.

    - new: in current, not in baseline (potential merge blockers)
    - known: in both (legacy technical debt)
    - resolved: in baseline, not in current (fixed debt — informational)
    """
    current_by_fp = {_fp(v): v for v in current}
    baseline_by_fp = {_fp(v): v for v in baseline}

    new = [current_by_fp[fp] for fp in current_by_fp.keys() - baseline_by_fp.keys()]
    known = [current_by_fp[fp] for fp in current_by_fp.keys() & baseline_by_fp.keys()]
    resolved = [baseline_by_fp[fp] for fp in baseline_by_fp.keys() - current_by_fp.keys()]

    # Stable ordering for deterministic CI artifacts.
    key = lambda v: (v.file_path, v.line, v.rule_id, v.fingerprint or "")
    return BaselineDiff(
        current=sorted(current, key=key),
        baseline=sorted(baseline, key=key),
        new=sorted(new, key=key),
        known=sorted(known, key=key),
        resolved=sorted(resolved, key=key),
    )


def _fp(violation: Violation) -> str:
    return violation.fingerprint or violation.compute_fingerprint()
