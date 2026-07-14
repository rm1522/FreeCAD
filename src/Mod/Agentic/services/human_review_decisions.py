"""Capture human-in-the-loop decisions from FreeCAD review overlays."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "fastener_human_review_decisions.v1"
DEFAULT_DECISIONS_FILENAME = "human_review_decisions.json"


def default_decisions_path(document: Any | None = None) -> Path:
    env_path = os.getenv("AGENTIC_CAD_HUMAN_REVIEW_DECISIONS")
    if env_path:
        return Path(env_path).expanduser()
    file_name = getattr(document, "FileName", "") if document is not None else ""
    if file_name:
        return Path(file_name).resolve().parent / DEFAULT_DECISIONS_FILENAME
    return Path.cwd() / DEFAULT_DECISIONS_FILENAME


def load_decisions(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        return empty_decisions()
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("human review decisions must be a JSON object")
    return validate_decisions(value)


def empty_decisions() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "decisions": [],
    }


def validate_decisions(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("human review decisions schema is invalid")
    decisions = value.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("human review decisions require decisions")
    seen = set()
    for index, decision in enumerate(decisions):
        if not isinstance(decision, dict):
            raise ValueError(f"decisions[{index}] must be an object")
        candidate_id = decision.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id or candidate_id in seen:
            raise ValueError(f"decisions[{index}].candidate_id is invalid")
        seen.add(candidate_id)
        action = decision.get("action")
        if action not in {"select_target", "reject", "defer"}:
            raise ValueError(f"decisions[{index}].action is invalid")
        target_id = decision.get("target_instance_id")
        if action == "select_target" and (not isinstance(target_id, str) or not target_id):
            raise ValueError(f"decisions[{index}].target_instance_id is required")
        if target_id is not None and not isinstance(target_id, str):
            raise ValueError(f"decisions[{index}].target_instance_id is invalid")
    return json.loads(json.dumps(value))


def upsert_decision(decisions: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    validated = validate_decisions(decisions)
    item = _validate_single_decision(decision)
    updated_items = [
        existing for existing in validated["decisions"]
        if existing["candidate_id"] != item["candidate_id"]
    ]
    updated_items.append(item)
    return validate_decisions({
        "schema_version": SCHEMA_VERSION,
        "decisions": updated_items,
    })


def save_decisions(decisions: dict[str, Any], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(validate_decisions(decisions), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination


def decision_from_overlay(
    overlay: Any,
    action: str,
    *,
    reviewer: str = "freecad-ui",
    rationale: str | None = None,
) -> dict[str, Any]:
    candidate_id = _string_property(overlay, "AgenticCandidateId")
    target_id = _string_property(overlay, "AgenticTargetInstanceId")
    if not candidate_id:
        raise ValueError("select a human-review overlay with AgenticCandidateId")
    if action not in {"select_target", "reject", "defer"}:
        raise ValueError("human review action is invalid")
    if action == "select_target" and not target_id:
        raise ValueError("select a target option overlay before approving")
    decision = {
        "candidate_id": candidate_id,
        "action": action,
        "reviewer": reviewer,
        "rationale": rationale or _default_rationale(action, target_id),
        "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    if target_id:
        decision["target_instance_id"] = target_id
    return _validate_single_decision(decision)


def record_overlay_decision(
    overlay: Any,
    action: str,
    *,
    path: str | Path,
    reviewer: str = "freecad-ui",
    rationale: str | None = None,
) -> dict[str, Any]:
    decisions = load_decisions(path)
    decision = decision_from_overlay(
        overlay,
        action,
        reviewer=reviewer,
        rationale=rationale,
    )
    updated = upsert_decision(decisions, decision)
    save_decisions(updated, path)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "recorded",
        "path": str(Path(path)),
        "decision": decision,
        "decision_count": len(updated["decisions"]),
    }


def format_decision_summary(report: dict[str, Any]) -> str:
    decision = report.get("decision", {})
    action = decision.get("action", "unknown")
    candidate_id = decision.get("candidate_id", "unknown")
    target_id = decision.get("target_instance_id")
    target_text = f" -> {target_id}" if target_id else ""
    return (
        "Agentic human review decision recorded: "
        f"{candidate_id}{target_text} = {action} "
        f"({report.get('decision_count', 0)} total)"
    )


def _validate_single_decision(decision: dict[str, Any]) -> dict[str, Any]:
    wrapped = validate_decisions({
        "schema_version": SCHEMA_VERSION,
        "decisions": [decision],
    })
    return wrapped["decisions"][0]


def _string_property(obj: Any, name: str) -> str:
    value = getattr(obj, name, "")
    return str(value or "").strip()


def _default_rationale(action: str, target_id: str) -> str:
    if action == "select_target":
        return f"selected target option {target_id}"
    if action == "reject":
        return "rejected by FreeCAD human review"
    return "deferred by FreeCAD human review"
