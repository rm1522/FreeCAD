"""FreeCAD plugin entry points for generic fastener evidence reports."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any


def build_focused_reprobe_request(
    *,
    document: Any | None = None,
    candidate_report_path: str | Path | None = None,
    output_path: str | Path | None = None,
    decisions: tuple[str, ...] = ("ask_user",),
) -> dict[str, Any]:
    """Create a focused material probe request from the current candidate report."""
    context = resolve_fastener_context(document=document)
    repo_root = context["repo_root"]
    _ensure_repo_import(repo_root)
    from backend.freecad_bridge.fastener_candidate_report import validate_wood_screw_candidate_report
    from backend.freecad_bridge.material_path_probe import build_focused_reprobe_request_from_candidate_report

    source_path = Path(candidate_report_path).expanduser().resolve() if candidate_report_path else context["candidate_report_path"]
    destination = Path(output_path).expanduser().resolve() if output_path else context["base_dir"] / "focused_material_path_probe_request.json"
    report = validate_wood_screw_candidate_report(_read_json(source_path))
    request = build_focused_reprobe_request_from_candidate_report(report, decisions=decisions)
    _write_json(destination, request)
    return {
        "schema_version": "agentic_fastener_report_command.v1",
        "status": "focused_reprobe_request_written",
        "candidate_count": len(request.get("candidates", [])),
        "source_report": str(source_path),
        "artifacts": {"focused_reprobe_request": str(destination)},
    }


def rebuild_wood_screw_candidate_report(
    *,
    document: Any | None = None,
    probe_report_path: str | Path | None = None,
    hardware_ir_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Rebuild a wood screw candidate report from current probe evidence."""
    context = resolve_fastener_context(document=document)
    repo_root = context["repo_root"]
    _ensure_repo_import(repo_root)
    from backend.freecad_bridge.fastener_candidate_report import build_wood_screw_candidate_report_from_files

    probe_path = Path(probe_report_path).expanduser().resolve() if probe_report_path else context["probe_report_path"]
    hardware_path = Path(hardware_ir_path).expanduser().resolve() if hardware_ir_path else context["hardware_ir_path"]
    destination = Path(output_path).expanduser().resolve() if output_path else context["base_dir"] / "wood_screw_candidate_report.json"
    report = build_wood_screw_candidate_report_from_files(
        probe_path,
        hardware_path,
        evidence=str(probe_path),
        output_path=destination,
    )
    return {
        "schema_version": "agentic_fastener_report_command.v1",
        "status": "candidate_report_written",
        "candidate_summary": report.get("summary", {}),
        "report_status": report.get("status"),
        "probe_quality": report.get("probe_quality", {}),
        "artifacts": {"wood_screw_candidate_report": str(destination)},
    }


def run_focused_reprobe_pipeline(
    *,
    document: Any | None = None,
    assembly_model_path: str | Path | None = None,
    candidate_report_path: str | Path | None = None,
    hardware_ir_path: str | Path | None = None,
    workspace_dir: str | Path | None = None,
    output_report_path: str | Path | None = None,
    decisions: tuple[str, ...] = ("ask_user",),
    runtime: Any | None = None,
    timeout_s: int = 180,
) -> dict[str, Any]:
    """Build a focused request, run FreeCAD material probing, and rebuild candidates."""
    context = resolve_fastener_context(document=document)
    repo_root = context["repo_root"]
    _ensure_repo_import(repo_root)
    from backend.freecad_bridge.material_path_probe import generate_material_path_probe

    focused = build_focused_reprobe_request(
        document=document,
        candidate_report_path=candidate_report_path,
        output_path=context["base_dir"] / "focused_material_path_probe_request.json",
        decisions=decisions,
    )
    request_path = Path(focused["artifacts"]["focused_reprobe_request"]).resolve()
    request = _read_json(request_path)
    model_path = _assembly_model_path(context, document, assembly_model_path)
    workspace = Path(workspace_dir).expanduser().resolve() if workspace_dir else context["base_dir"] / "focused_reprobe"
    probe_kwargs: dict[str, Any] = {
        "run_id": "agentic_focused_material_reprobe",
        "timeout_s": timeout_s,
    }
    if runtime is not None:
        probe_kwargs["runtime"] = runtime
    probe = generate_material_path_probe(
        model_path,
        request,
        workspace,
        **probe_kwargs,
    )
    probe_report_path = Path(probe["artifacts"]["validation_report"]).resolve()
    candidate_output = (
        Path(output_report_path).expanduser().resolve()
        if output_report_path
        else workspace / "wood_screw_candidate_report.json"
    )
    candidate = rebuild_wood_screw_candidate_report(
        document=document,
        probe_report_path=probe_report_path,
        hardware_ir_path=hardware_ir_path,
        output_path=candidate_output,
    )
    return {
        "schema_version": "agentic_fastener_report_command.v1",
        "status": "focused_reprobe_pipeline_completed",
        "candidate_count": focused.get("candidate_count", 0),
        "probe_status": probe.get("status"),
        "geometry_passed": probe.get("geometry_passed"),
        "report_status": candidate.get("report_status"),
        "candidate_summary": candidate.get("candidate_summary", {}),
        "artifacts": {
            "focused_reprobe_request": str(request_path),
            "material_path_probe_report": str(probe_report_path),
            "wood_screw_candidate_report": candidate.get("artifacts", {}).get("wood_screw_candidate_report"),
        },
        "runtime": probe.get("runtime", {}),
    }


def build_hardware_unresolved_report_for_workspace(
    *,
    document: Any | None = None,
    hardware_ir_path: str | Path | None = None,
    candidate_report_path: str | Path | None = None,
    human_review_plan_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a fail-closed unresolved hardware report for the active workspace."""
    context = resolve_fastener_context(document=document)
    repo_root = context["repo_root"]
    _ensure_repo_import(repo_root)
    from backend.freecad_bridge.hardware_unresolved_report import (
        build_hardware_unresolved_report,
        save_hardware_unresolved_report,
    )

    hardware_path = Path(hardware_ir_path).expanduser().resolve() if hardware_ir_path else context["hardware_ir_path"]
    screw_path = Path(candidate_report_path).expanduser().resolve() if candidate_report_path else context["candidate_report_path"]
    review_path = _review_plan_path(context, human_review_plan_path)
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / "hardware_unresolved_report.json"
    )
    report = build_hardware_unresolved_report(
        _read_json(hardware_path),
        wood_screw_candidate_report=_read_json(screw_path),
        human_review_plan=_read_json(review_path) if review_path and review_path.is_file() else None,
    )
    save_hardware_unresolved_report(report, destination)
    return {
        "schema_version": "agentic_fastener_report_command.v1",
        "status": "hardware_unresolved_report_written",
        "report_status": report.get("status"),
        "summary": report.get("summary", {}),
        "unresolved_items": report.get("items", []),
        "artifacts": {
            "hardware_ir": str(hardware_path),
            "wood_screw_candidate_report": str(screw_path),
            "human_review_plan": str(review_path) if review_path else None,
            "hardware_unresolved_report": str(destination),
        },
    }


def build_hardware_resolution_plan_for_workspace(
    *,
    document: Any | None = None,
    unresolved_report_path: str | Path | None = None,
    human_review_plan_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a machine-readable next-action plan for unresolved hardware."""
    context = resolve_fastener_context(document=document)
    repo_root = context["repo_root"]
    _ensure_repo_import(repo_root)
    from backend.freecad_bridge.hardware_resolution_plan import (
        build_hardware_resolution_plan,
        save_hardware_resolution_plan,
    )

    unresolved_path = (
        Path(unresolved_report_path).expanduser().resolve()
        if unresolved_report_path
        else context["base_dir"] / "hardware_unresolved_report.json"
    )
    if not unresolved_path.is_file():
        unresolved = build_hardware_unresolved_report_for_workspace(
            document=document,
            output_path=unresolved_path,
        )
        unresolved_path = Path(unresolved["artifacts"]["hardware_unresolved_report"]).resolve()
    review_path = _review_plan_path(context, human_review_plan_path)
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / "hardware_resolution_plan.json"
    )
    plan = build_hardware_resolution_plan(
        _read_json(unresolved_path),
        human_review_plan=_read_json(review_path) if review_path and review_path.is_file() else None,
    )
    save_hardware_resolution_plan(plan, destination)
    return {
        "schema_version": "agentic_fastener_report_command.v1",
        "status": "hardware_resolution_plan_written",
        "plan_status": plan.get("status"),
        "summary": plan.get("summary", {}),
        "actions": plan.get("actions", []),
        "artifacts": {
            "hardware_unresolved_report": str(unresolved_path),
            "human_review_plan": str(review_path) if review_path else None,
            "hardware_resolution_plan": str(destination),
        },
    }


def resolve_fastener_context(*, document: Any | None = None) -> dict[str, Path]:
    repo_root = _repo_root()
    base_dir = _base_dir(document)
    cad_root = base_dir.parent
    context = {
        "repo_root": repo_root,
        "base_dir": base_dir,
        "candidate_report_path": _env_path("AGENTIC_CAD_CANDIDATE_REPORT") or base_dir / "wood_screw_candidate_report.json",
        "probe_report_path": _env_path("AGENTIC_CAD_MATERIAL_PROBE_REPORT") or _first_existing(
            base_dir,
            ("material_path_probe_report.json", "focused_reprobe/material_path_probe_report.json"),
        ),
        "hardware_ir_path": _env_path("AGENTIC_CAD_HARDWARE_IR")
        or _first_existing(base_dir, ("assembly_hardware_ir.json",))
        or _first_existing(cad_root, ("*/assembly_hardware_ir.json",)),
    }
    _validate_context(context)
    return context


def format_focused_reprobe_summary(report: dict[str, Any]) -> str:
    return (
        "Focused reprobe request: "
        f"{report.get('candidate_count', 0)} candidate axes -> "
        f"{report.get('artifacts', {}).get('focused_reprobe_request')}"
    )


def format_candidate_report_summary(report: dict[str, Any]) -> str:
    summary = report.get("candidate_summary", {})
    return (
        "Wood screw candidate report: "
        f"{report.get('report_status', 'unknown')}, "
        f"place={summary.get('place', 0)}, "
        f"reject={summary.get('reject', 0)}, "
        f"ask_user={summary.get('ask_user', 0)}"
    )


def format_focused_reprobe_pipeline_summary(report: dict[str, Any]) -> str:
    summary = report.get("candidate_summary", {})
    return (
        "Focused reprobe pipeline: "
        f"{report.get('probe_status', 'unknown')}, "
        f"geometry_passed={report.get('geometry_passed')}, "
        f"candidate_report={report.get('report_status', 'unknown')}, "
        f"place={summary.get('place', 0)}, "
        f"reject={summary.get('reject', 0)}, "
        f"ask_user={summary.get('ask_user', 0)}"
    )


def format_hardware_unresolved_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    items = report.get("unresolved_items", [])
    quantities = ", ".join(
        f"{item.get('description', item.get('stable_part_id'))}: {item.get('unplaced_quantity', 0)}"
        for item in items[:4]
    )
    if len(items) > 4:
        quantities += f", +{len(items) - 4} more"
    return (
        "Hardware unresolved report: "
        f"{report.get('report_status', 'unknown')}, "
        f"{summary.get('placed_quantity', 0)}/{summary.get('required_quantity', 0)} placed, "
        f"{summary.get('unplaced_quantity', 0)} unplaced"
        + (f" ({quantities})" if quantities else "")
    )


def format_hardware_unresolved_details(report: dict[str, Any]) -> str:
    """Format unresolved hardware as a compact review list for the chat panel."""
    lines = [format_hardware_unresolved_summary(report)]
    artifact = report.get("artifacts", {}).get("hardware_unresolved_report")
    if artifact:
        lines.append(f"Report: {artifact}")
    items = report.get("unresolved_items", [])
    if not items:
        lines.append("No unresolved hardware remains.")
        return "\n".join(lines)
    for item in items:
        lines.append(
            "- "
            f"{item.get('description') or item.get('stable_part_id')}: "
            f"{item.get('unplaced_quantity', 0)} unplaced, "
            f"{item.get('resolution_status', 'unknown')}"
        )
        for reason in item.get("reasons", [])[:2]:
            lines.append(f"  reason: {reason}")
        for action in item.get("next_actions", [])[:1]:
            lines.append(f"  next: {action}")
    return "\n".join(lines)


def format_hardware_resolution_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware resolution plan: "
        f"{report.get('plan_status', 'unknown')}, "
        f"{summary.get('action_count', 0)} actions, "
        f"{summary.get('unplaced_quantity', 0)} unplaced "
        f"(review={summary.get('human_review_quantity', 0)}, "
        f"evidence={summary.get('source_evidence_quantity', 0)}, "
        f"spec={summary.get('missing_spec_quantity', 0)})"
    )


def format_hardware_resolution_details(report: dict[str, Any]) -> str:
    """Format the resolution plan as a compact action list for the chat panel."""
    lines = [format_hardware_resolution_summary(report)]
    artifact = report.get("artifacts", {}).get("hardware_resolution_plan")
    if artifact:
        lines.append(f"Plan: {artifact}")
    actions = report.get("actions", [])
    if not actions:
        lines.append("No resolution actions remain.")
        return "\n".join(lines)
    for action in actions:
        lines.append(
            "- "
            f"{action.get('description') or action.get('stable_part_id')}: "
            f"{action.get('unplaced_quantity', 0)} unplaced -> "
            f"{action.get('recommended_action', 'unknown')}"
        )
        lines.append(f"  gate: {action.get('decision_gate', 'unknown')}")
        required = ", ".join(action.get("required_input", [])[:3])
        if required:
            lines.append(f"  required: {required}")
    return "\n".join(lines)


def _assembly_model_path(
    context: dict[str, Path],
    document: Any | None,
    explicit_path: str | Path | None,
) -> Path:
    if explicit_path is not None:
        candidate = Path(explicit_path).expanduser().resolve()
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"assembly model does not exist: {candidate}")
    env_path = _env_path("AGENTIC_CAD_ASSEMBLY_MODEL")
    if env_path:
        if env_path.is_file():
            return env_path
        raise FileNotFoundError(f"AGENTIC_CAD_ASSEMBLY_MODEL does not exist: {env_path}")
    base_candidate = context["base_dir"] / "assembly_candidate.FCStd"
    if base_candidate.is_file():
        return base_candidate.resolve()
    file_name = getattr(document, "FileName", "") if document is not None else ""
    if file_name:
        candidate = Path(file_name).resolve()
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("assembly model was not found; set AGENTIC_CAD_ASSEMBLY_MODEL")


def _review_plan_path(context: dict[str, Path], explicit_path: str | Path | None) -> Path | None:
    if explicit_path is not None:
        path = Path(explicit_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"human review plan does not exist: {path}")
        return path
    env_path = _env_path("AGENTIC_CAD_HUMAN_REVIEW_PLAN")
    if env_path:
        if env_path.is_file():
            return env_path
        raise FileNotFoundError(f"AGENTIC_CAD_HUMAN_REVIEW_PLAN does not exist: {env_path}")
    candidate = context["base_dir"] / "wood_screw_human_review_plan.json"
    return candidate.resolve() if candidate.is_file() else None


def _repo_root() -> Path:
    env_path = _env_path("AGENTIC_CAD_REPO_ROOT")
    if env_path:
        return _require_repo_root(env_path)
    for start in (Path(__file__).resolve(), Path.cwd().resolve()):
        for parent in (start, *start.parents):
            if (parent / "backend" / "freecad_bridge" / "material_path_probe.py").is_file():
                return parent
    raise FileNotFoundError("agentic-cad repo root was not found; set AGENTIC_CAD_REPO_ROOT")


def _base_dir(document: Any | None) -> Path:
    env_path = _env_path("AGENTIC_CAD_FASTENER_BASE_DIR")
    if env_path:
        return env_path
    file_name = getattr(document, "FileName", "") if document is not None else ""
    if file_name:
        parent = Path(file_name).resolve().parent
        for candidate in (parent, parent.parent):
            if (candidate / "wood_screw_candidate_report.json").is_file() or (candidate / "material_path_probe_report.json").is_file():
                return candidate
    cwd = Path.cwd().resolve()
    if (cwd / "wood_screw_candidate_report.json").is_file() or (cwd / "material_path_probe_report.json").is_file():
        return cwd
    raise FileNotFoundError("fastener report base directory was not found; set AGENTIC_CAD_FASTENER_BASE_DIR")


def _first_existing(root: Path, patterns: tuple[str, ...]) -> Path | None:
    for pattern in patterns:
        matches = sorted(root.glob(pattern))
        if matches:
            return matches[0].resolve()
    return None


def _env_path(name: str) -> Path | None:
    value = os.getenv(name)
    return Path(value).expanduser().resolve() if value else None


def _require_repo_root(path: Path) -> Path:
    if not (path / "backend" / "freecad_bridge" / "material_path_probe.py").is_file():
        raise FileNotFoundError(f"invalid AGENTIC_CAD_REPO_ROOT: {path}")
    return path


def _validate_context(context: dict[str, Path | None]) -> None:
    for key, path in context.items():
        if key in {"base_dir", "repo_root"}:
            continue
        if path is None or not path.is_file():
            raise FileNotFoundError(f"{key} does not exist: {path}")


def _ensure_repo_import(repo_root: Path) -> None:
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
