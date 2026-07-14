"""Thin FreeCAD plugin adapter for the service-side CAD agent loop."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

from services.capability_registry import list_capabilities
from services.native_tools import execute_plan, get_document_context


def run_approved_local_agent_loop(
    prompt: str,
    *,
    stage: str = "s3_engineering",
    scratch_document: bool = False,
    promotion_evidence: dict[str, Any] | None = None,
    llm_planner: Any | None = None,
    persist_report: bool = True,
) -> dict[str, Any]:
    """Plan and execute a prompt through the real local FreeCAD native tools.

    `stage` selects the design-stage contract (`s0_envelope` .. `s3_engineering`);
    unknown stages fail closed with `ValueError`. Entering `s2_features` (or
    promoting a scratch draft into `s3_engineering`) requires the matching
    fail-closed stage promotion record via `promotion_evidence`.
    """
    repo_root = _repo_root()
    service = _agent_loop_service(repo_root)
    context = get_document_context()
    capabilities = list_capabilities()
    payload = service.run_local_freecad_agent_loop(
        prompt,
        context=context,
        capabilities=capabilities,
        execute_operation=_execute_native_operation,
        stage=stage,
        scratch_document=scratch_document,
        promotion_evidence=promotion_evidence,
        llm_planner=llm_planner,
    )
    if persist_report:
        payload["report_path"] = str(save_agent_loop_report(payload, document_context=context, repo_root=repo_root))
    return payload


def save_agent_loop_report(
    report: dict[str, Any],
    *,
    document_context: dict[str, Any] | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Persist a redacted machine-readable agent episode report."""
    destination_dir = _episode_dir(document_context or {}, repo_root=repo_root or _repo_root())
    destination_dir.mkdir(parents=True, exist_ok=True)
    task_id = str(report.get("task_id") or "agent-episode")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = destination_dir / f"{stamp}_{_safe_name(task_id)}.json"
    destination.write_text(
        json.dumps(_redacted_report(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination


def _native_tool_implementations():
    service = _agent_loop_service(_repo_root())
    return service.build_native_tool_implementations(list_capabilities(), _execute_native_operation)


def _execute_single_operation(arguments: dict[str, Any], aliases: dict[str, str] | None = None) -> Any:
    service = _agent_loop_service(_repo_root())
    return service.execute_single_operation(arguments, _execute_native_operation, aliases=aliases)


def _execute_native_operation(operation: dict[str, Any]) -> dict[str, Any]:
    return execute_plan(
        {
            "schema_version": "freecad_tool_plan.v0",
            "plan_id": f"local_agent_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}",
            "status": "ready",
            "operations": [operation],
        },
        approved=True,
    )


def _episode_dir(document_context: dict[str, Any], *, repo_root: Path) -> Path:
    document = document_context.get("document") if isinstance(document_context, dict) else None
    file_name = document.get("file_name") if isinstance(document, dict) else None
    if isinstance(file_name, str) and file_name:
        return Path(file_name).resolve().parent / "agentic_episodes"
    return repo_root / "out" / "freecad_agent_episodes"


def _redacted_report(report: dict[str, Any]) -> dict[str, Any]:
    redacted = json.loads(json.dumps(report))
    redacted.pop("goal", None)
    for event in redacted.get("trace_events", []):
        if isinstance(event, dict):
            event.pop("goal", None)
    return redacted


def _safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)
    return safe[:80] or "agent-episode"


def _repo_root() -> Path:
    for candidate in _repo_root_candidates():
        if (candidate / "backend" / "orchestration" / "agent_execution_loop.py").is_file():
            return candidate
    raise FileNotFoundError("agentic-cad repo root was not found")


def _repo_root_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_root = os.environ.get("AGENTIC_CAD_SERVICE_ROOT")
    if env_root:
        candidates.append(Path(env_root).expanduser().resolve())
    for start in (Path(__file__).resolve(), Path.cwd().resolve()):
        for parent in (start, *start.parents):
            candidates.append(parent)
            candidates.append(parent / "ai-agentic-cad")
    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique.append(candidate)
    return unique


def _agent_loop_service(repo_root: Path):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from backend.freecad_bridge import local_agent_loop_service

    return local_agent_loop_service
