"""Thin FreeCAD plugin adapter for the service-side CAD agent loop."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.capability_registry import list_capabilities
from services.local_agent_service_client import LocalAgentServiceSession
from services.native_tools import execute_plan, get_document_context


ALLOWED_DESIGN_STAGES = {"s0_envelope", "s1_structure", "s2_features", "s3_engineering"}


class _ToolResult:
    def __init__(self, ok: bool, output: Any = None, error: str | None = None):
        self.ok = ok
        self.output = output
        self.error = error


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
    if stage not in ALLOWED_DESIGN_STAGES:
        raise ValueError(f"Unknown design stage: {stage}")
    if llm_planner is not None:
        raise ValueError("llm_planner objects must run inside the external agent service")
    repo_root = _repo_root()
    context = get_document_context()
    capabilities = list_capabilities()
    with LocalAgentServiceSession(repo_root) as client:
        service_payload = client.plan_freecad_agent_episode(
            {
                "prompt": prompt,
                "document_context": context,
                "capabilities": capabilities,
                "stage": stage,
                "scratch_document": scratch_document,
                "promotion_evidence": promotion_evidence,
            }
        )
    payload = _execute_service_plan(service_payload)
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
    aliases: dict[str, str] = {}

    def _implementation(arguments: dict[str, Any]) -> _ToolResult:
        return _execute_single_operation(arguments, aliases)

    return {str(item["name"]): _implementation for item in list_capabilities()}


def _execute_single_operation(arguments: dict[str, Any], aliases: dict[str, str] | None = None) -> Any:
    aliases = {} if aliases is None else aliases
    payload = dict(arguments)
    operation_type = str(payload.pop("_operation_type"))
    alias = payload.pop("_alias", None)
    target = payload.pop("target", None)
    if "body_target" in payload:
        payload["body_target"] = _resolve_alias_reference(payload["body_target"], aliases)
    operation = {
        "type": operation_type,
        "arguments": payload,
    }
    if target is not None:
        operation["target"] = _resolve_alias_reference(target, aliases)
    result = _execute_native_operation(operation)
    if alias:
        changed = result.get("changed") or []
        stable_id = changed[0].get("stable_id") if changed else None
        if not stable_id:
            raise ValueError(f"Aliased operation returned no stable_id: {alias}")
        aliases[str(alias)] = str(stable_id)
    return _ToolResult(ok=True, output=result)


def _execute_service_plan(service_payload: dict[str, Any]) -> dict[str, Any]:
    status = service_payload.get("status")
    task_id = str(service_payload.get("task_id") or "freecad-local-agent")
    trace_events = list(service_payload.get("trace_events") or [])
    if status == "needs_user_input":
        return {
            "schema_version": "cad_agent_loop_report.v1",
            "status": "needs_user_input",
            "task_id": task_id,
            "artifact_kind": "freecad_document",
            "iterations": 1,
            "questions": service_payload.get("questions") or [],
            "error": None,
            "tool_results": [],
            "verification": None,
            "trace_events": trace_events,
        }
    if status != "ready":
        return {
            "schema_version": "cad_agent_loop_report.v1",
            "status": "rejected",
            "task_id": task_id,
            "artifact_kind": "freecad_document",
            "iterations": 1,
            "questions": [],
            "error": service_payload.get("error") or "agent_service_rejected",
            "tool_results": [],
            "verification": None,
            "trace_events": trace_events,
        }
    result = execute_plan(service_payload["plan"], approved=True)
    return {
        "schema_version": "cad_agent_loop_report.v1",
        "status": "committed",
        "task_id": task_id,
        "artifact_kind": "freecad_document",
        "iterations": 1,
        "questions": [],
        "error": None,
        "tool_results": [{"ok": True, "output": result, "error": None}],
        "verification": {"status": "pass", "summary": "all tool calls succeeded"},
        "trace_events": trace_events + [{"event": "agent_ipc_plan_executed"}],
    }


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


ALIAS_REF_PREFIX = "@alias:"


def _resolve_alias_reference(value: Any, aliases: dict[str, str]) -> Any:
    if isinstance(value, str) and value.startswith(ALIAS_REF_PREFIX):
        name = value[len(ALIAS_REF_PREFIX) :]
        if name not in aliases:
            raise ValueError(f"Alias is referenced before it is created: {name}")
        return aliases[name]
    return value


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
