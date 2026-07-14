"""GUI-facing smoke helpers for typed FreeCAD operations."""

from __future__ import annotations

from typing import Any

from services.api_client import AgenticApiClient
from services.capability_registry import list_capabilities
from services.native_tools import execute_plan, get_document_context


def run_plan_execute_smoke(
    *,
    prompt: str = "長さ22mm、幅14mm、高さ9mmの箱を作って",
) -> dict[str, Any]:
    """Verify backend planning and approved native execution from the GUI process."""
    plan = AgenticApiClient().plan_freecad(
        prompt,
        get_document_context(),
        list_capabilities(),
    )
    result = execute_plan(plan, approved=True)
    return {
        "schema_version": "agentic_cad_gui_smoke.v1",
        "status": "passed",
        "kind": "plan_execute",
        "plan": plan,
        "result": result,
        "summary": f"Plan Execute smoke: {result.get('summary', '')}",
    }


def run_selection_update_smoke(
    *,
    create_prompt: str = "長さ30mm、幅20mm、高さ10mmの箱を作って",
    update_prompt: str = "幅33mmに変更して",
    expected_width_mm: float = 33.0,
) -> dict[str, Any]:
    """Create, select, then update an object through the planner selection path."""
    client = AgenticApiClient()
    capabilities = list_capabilities()
    create_plan = client.plan_freecad(create_prompt, get_document_context(), capabilities)
    create_result = execute_plan(create_plan, approved=True)
    created = _first_evidence_object(create_result)
    _select_object(created["name"])
    selected_context = get_document_context()
    update_plan = client.plan_freecad(update_prompt, selected_context, capabilities)
    update_result = execute_plan(update_plan, approved=True)
    updated = _first_evidence_object(update_result)
    width = _bbox_width(updated)
    if abs(width - expected_width_mm) > 1e-6:
        raise RuntimeError(f"selection update smoke expected width {expected_width_mm}, got {width}")
    return {
        "schema_version": "agentic_cad_gui_smoke.v1",
        "status": "passed",
        "kind": "selection_update",
        "created_stable_id": created.get("stable_id"),
        "selected_count": len(selected_context.get("selection", [])),
        "update_plan": update_plan,
        "update_result": update_result,
        "summary": f"Selection update smoke: width={width}mm",
    }


def _first_evidence_object(result: dict[str, Any]) -> dict[str, Any]:
    evidence = result.get("evidence") or []
    if not evidence:
        raise RuntimeError("operation did not return shape evidence")
    obj = evidence[0].get("object") or {}
    if not obj.get("name"):
        raise RuntimeError("operation evidence is missing object name")
    return obj


def _bbox_width(obj: dict[str, Any]) -> float:
    shape = obj.get("shape") or {}
    bbox = shape.get("bbox_mm") or []
    if len(bbox) != 3:
        raise RuntimeError("updated evidence is missing bbox")
    return float(bbox[1])


def _select_object(object_name: str) -> None:
    try:
        import FreeCAD  # type: ignore
        import FreeCADGui as Gui  # type: ignore

        document = FreeCAD.ActiveDocument
        if document is None:
            raise RuntimeError("no active FreeCAD document")
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(document.Name, object_name)
        update = getattr(Gui, "updateGui", None)
        if callable(update):
            update()
    except Exception as exc:
        raise RuntimeError(f"failed to select object for smoke: {object_name}") from exc
