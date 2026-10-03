"""Enrich violations with SWC module owner, DOORS ID, and ASIL from path maps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from misra_triage.models.config import MappingConfig
from misra_triage.models.violation import AsilLevel, Violation
from misra_triage.parsers.rule_catalog import classify_asil
from misra_triage.utils.logging import get_logger

logger = get_logger(__name__)


class ViolationEnricher:
    """
    Applies longest-prefix path matching against YAML maps:

    owner_map.yaml:
      mappings:
        - prefix: src/bsw/can
          swc: CanIf
          owner: team-can@example.com
          asil: B

    doors_map.yaml:
      mappings:
        - prefix: src/bsw/can
          doors_id: REQ-CAN-001
    """

    def __init__(self, config: MappingConfig) -> None:
        self.config = config
        self._owner_rules = _load_rules(config.owner_map_path)
        self._doors_rules = _load_rules(config.doors_map_path)

    def enrich_many(self, violations: list[Violation]) -> list[Violation]:
        return [self.enrich(v) for v in violations]

    def enrich(self, violation: Violation) -> Violation:
        owner_rule = _best_match(violation.file_path, self._owner_rules)
        doors_rule = _best_match(violation.file_path, self._doors_rules)

        swc = None
        owner = self.config.default_owner
        asil = violation.asil_level

        if owner_rule:
            swc = str(owner_rule.get("swc") or owner_rule.get("module") or swc or "")
            owner = str(owner_rule.get("owner") or owner)
            if owner_rule.get("asil"):
                asil = classify_asil(str(owner_rule["asil"]), default=asil)

        doors_id = None
        if doors_rule:
            doors_id = str(doors_rule.get("doors_id") or doors_rule.get("requirement_id") or "")
            if not swc:
                swc = str(doors_rule.get("swc") or "") or None

        if asil == AsilLevel.UNKNOWN:
            asil = self.config.default_asil

        return violation.model_copy(
            update={
                "swc_module": swc or violation.swc_module,
                "owner": owner,
                "doors_req_id": doors_id or violation.doors_req_id,
                "asil_level": asil,
            }
        )


def _load_rules(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    if not path.exists():
        logger.warning("Mapping file not found: %s", path)
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    rules = data.get("mappings", data if isinstance(data, list) else [])
    normalized: list[dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict) or "prefix" not in rule:
            logger.warning("Ignoring invalid mapping rule: %s", rule)
            continue
        rule = dict(rule)
        rule["prefix"] = str(rule["prefix"]).replace("\\", "/").rstrip("/")
        normalized.append(rule)
    # Longest prefix first for efficient matching.
    normalized.sort(key=lambda r: len(r["prefix"]), reverse=True)
    logger.info("Loaded %d mapping rules from %s", len(normalized), path)
    return normalized


def _best_match(file_path: str, rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized = file_path.replace("\\", "/")
    for rule in rules:
        prefix = rule["prefix"]
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return rule
    return None
