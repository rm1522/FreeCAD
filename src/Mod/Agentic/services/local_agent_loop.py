"""Run the CAD agent loop inside the FreeCAD plugin process."""

from __future__ import annotations

import json
import uuid
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
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.orchestration.agent_execution_loop import (
        AgentPlan,
        AgentPlanStatus,
        CADAgentExecutionLoop,
        default_freecad_agent_registry,
        pass_if_all_tools_ok,
    )
    from backend.orchestration.cad_agent_harness import (
        DesignStage,
        EpisodeTrace,
        TaskContract,
        ToolCall,
        ToolResult,
    )
    from backend.orchestration.freecad_planner import build_freecad_plan

    context = get_document_context()
    capabilities = list_capabilities()
    trace = EpisodeTrace(f"freecad-local-agent-{uuid.uuid4().hex[:8]}")
    loop = CADAgentExecutionLoop(default_freecad_agent_registry(capabilities), trace=trace)
    contract = TaskContract(
        task_id=trace.task_id,
        goal=prompt,
        artifact_kind="freecad_document",
        source_refs=[],
        approval_gates=[],
        max_iterations=3,
        stage=DesignStage(stage),
        scratch_document=bool(scratch_document),
        promotion_evidence=promotion_evidence,
    )

    def planner(_loop_context):
        plan = build_freecad_plan(
            prompt, context=context, capabilities=capabilities, llm_planner=llm_planner
        )
        if plan.get("status") == "needs_clarification":
            return AgentPlan(
                status=AgentPlanStatus.NEEDS_USER_INPUT,
                questions=[str(item) for item in plan.get("questions", [])],
                explanation=str(plan.get("explanation") or ""),
            )
        calls = []
        for operation in plan.get("operations", []):
            arguments = dict(operation.get("arguments") or {})
            arguments["_operation_type"] = operation.get("type")
            if operation.get("alias"):
                arguments["_alias"] = operation["alias"]
            if "target" in operation:
                arguments["target"] = operation["target"]
            calls.append(
                ToolCall(
                    tool_name=str(operation.get("type")),
                    arguments=arguments,
                    reason=str(plan.get("explanation") or "Execute typed FreeCAD operation."),
                )
            )
        return AgentPlan(
            status=AgentPlanStatus.READY,
            tool_calls=calls,
            explanation=str(plan.get("explanation") or ""),
        )

    report = loop.run(
        contract,
        planner,
        _native_tool_implementations(),
        pass_if_all_tools_ok,
        approval_provider=lambda *_args: True,
    )
    payload = report.as_dict()
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


ALIAS_REF_PREFIX = "@alias:"


def _native_tool_implementations():
    aliases: dict[str, str] = {}

    def _implementation(arguments: dict[str, Any]) -> Any:
        return _execute_single_operation(arguments, aliases)

    return {str(item["name"]): _implementation for item in list_capabilities()}


def _resolve_alias_reference(value: Any, aliases: dict[str, str]) -> Any:
    if isinstance(value, str) and value.startswith(ALIAS_REF_PREFIX):
        name = value[len(ALIAS_REF_PREFIX) :]
        if name not in aliases:
            raise ValueError(f"Alias is referenced before it is created: {name}")
        return aliases[name]
    return value


def _execute_single_operation(arguments: dict[str, Any], aliases: dict[str, str] | None = None) -> Any:
    from backend.orchestration.cad_agent_harness import ToolResult

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
    result = execute_plan(
        {
            "schema_version": "freecad_tool_plan.v0",
            "plan_id": f"local_agent_{uuid.uuid4().hex[:12]}",
            "status": "ready",
            "operations": [operation],
        },
        approved=True,
    )
    if alias:
        changed = result.get("changed") or []
        stable_id = changed[0].get("stable_id") if changed else None
        if not stable_id:
            raise ValueError(f"Aliased operation returned no stable_id: {alias}")
        aliases[str(alias)] = str(stable_id)
    return ToolResult(ok=True, output=result)


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
    for start in (Path(__file__).resolve(), Path.cwd().resolve()):
        for parent in (start, *start.parents):
            if (parent / "backend" / "orchestration" / "agent_execution_loop.py").is_file():
                return parent
    raise FileNotFoundError("agentic-cad repo root was not found")
