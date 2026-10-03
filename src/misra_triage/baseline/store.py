"""Persistent baseline of known (accepted) technical-debt violations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from misra_triage.models.violation import Violation
from misra_triage.utils.logging import get_logger

logger = get_logger(__name__)


class BaselineStore:
    """JSON-backed store keyed by violation fingerprint."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def exists(self) -> bool:
        return self.path.exists() and self.path.stat().st_size > 0

    def load(self) -> list[Violation]:
        if not self.path.exists():
            logger.info("No baseline at %s — treating as empty", self.path)
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Corrupt baseline JSON at {self.path}: {exc}") from exc

        items = payload.get("violations", payload if isinstance(payload, list) else [])
        violations: list[Violation] = []
        for item in items:
            try:
                violations.append(Violation.model_validate(item))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping invalid baseline entry: %s", exc)
        logger.info("Loaded %d baseline violations from %s", len(violations), self.path)
        return violations

    def save(self, violations: list[Violation], *, note: str = "") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "note": note,
            "count": len(violations),
            "violations": [v.model_dump() for v in violations],
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)
        logger.info("Wrote baseline (%d violations) to %s", len(violations), self.path)

    def fingerprints(self) -> set[str]:
        return {v.fingerprint or v.compute_fingerprint() for v in self.load()}
