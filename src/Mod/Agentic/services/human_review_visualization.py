"""Visualize human-in-the-loop fastener review plans in FreeCAD."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "fastener_human_review_plan.v1"
VISUALIZATION_SCHEMA_VERSION = "fastener_human_review_visualization.v1"

AXIS_COLOR = (0.1, 0.32, 0.95)
SAFE_COLOR = (0.0, 0.65, 0.25)
UNSAFE_COLOR = (0.9, 0.12, 0.08)
CENTER_COLOR = (1.0, 0.72, 0.08)


def load_review_plan(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("review plan must be a JSON object")
    return validate_review_plan(value)


def validate_review_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if plan.get("schema_version") != SCHEMA_VERSION or plan.get("units") != "mm":
        raise ValueError("human review plan schema/units are invalid")
    items = plan.get("review_items")
    if not isinstance(items, list):
        raise ValueError("human review plan requires review_items")
    seen = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"review_items[{index}] must be an object")
        candidate_id = item.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id or candidate_id in seen:
            raise ValueError(f"review_items[{index}].candidate_id is invalid")
        seen.add(candidate_id)
        if not _vector(item.get("center_mm"), 3) or not _vector(item.get("direction"), 3):
            raise ValueError(f"review_items[{index}] center/direction is invalid")
        if not _vector(item.get("screw_span_mm"), 2):
            raise ValueError(f"review_items[{index}].screw_span_mm is invalid")
        options = item.get("target_options")
        if not isinstance(options, list) or not options:
            raise ValueError(f"review_items[{index}] requires target_options")
        for option_index, option in enumerate(options):
            if not isinstance(option, dict):
                raise ValueError(f"review_items[{index}].target_options[{option_index}] must be an object")
            if not isinstance(option.get("target_instance_id"), str) or not option["target_instance_id"]:
                raise ValueError(f"review_items[{index}].target_options[{option_index}].target_instance_id is invalid")
            if not _vector(option.get("interval_mm"), 2):
                raise ValueError(f"review_items[{index}].target_options[{option_index}].interval_mm is invalid")
            if not isinstance(option.get("meets_geometry_gate"), bool):
                raise ValueError(
                    f"review_items[{index}].target_options[{option_index}].meets_geometry_gate is invalid"
                )
            if not isinstance(option.get("warnings"), list):
                raise ValueError(f"review_items[{index}].target_options[{option_index}].warnings is invalid")
    return json.loads(json.dumps(plan))


def build_visualization_records(plan: dict[str, Any]) -> dict[str, Any]:
    """Build deterministic overlay records before touching FreeCAD."""
    validated = validate_review_plan(plan)
    records = []
    for item in validated["review_items"]:
        center = [float(value) for value in item["center_mm"]]
        direction = _normalize([float(value) for value in item["direction"]])
        screw_span = [float(value) for value in item["screw_span_mm"]]
        records.append({
            "kind": "candidate_axis",
            "candidate_id": item["candidate_id"],
            "label": f"Review axis {item['candidate_id']}",
            "start_mm": _point_at(center, direction, min(screw_span)),
            "end_mm": _point_at(center, direction, max(screw_span)),
            "radius_mm": 1.2,
            "color": AXIS_COLOR,
            "warnings": [],
        })
        records.append({
            "kind": "candidate_center",
            "candidate_id": item["candidate_id"],
            "label": f"Review center {item['candidate_id']}",
            "center_mm": center,
            "radius_mm": 3.0,
            "color": CENTER_COLOR,
            "warnings": [],
        })
        for option in item["target_options"]:
            interval = [float(value) for value in option["interval_mm"]]
            warnings = [str(value) for value in option.get("warnings", [])]
            records.append({
                "kind": "target_option",
                "candidate_id": item["candidate_id"],
                "target_instance_id": option["target_instance_id"],
                "label": f"{item['candidate_id']} -> {option['target_instance_id']}",
                "start_mm": _point_at(center, direction, min(interval)),
                "end_mm": _point_at(center, direction, max(interval)),
                "radius_mm": 2.0,
                "color": SAFE_COLOR if option["meets_geometry_gate"] else UNSAFE_COLOR,
                "meets_geometry_gate": option["meets_geometry_gate"],
                "thread_engagement_mm": option.get("thread_engagement_mm"),
                "tip_breakthrough_mm": option.get("tip_breakthrough_mm"),
                "warnings": warnings,
            })
    return {
        "schema_version": VISUALIZATION_SCHEMA_VERSION,
        "units": "mm",
        "review_item_count": len(validated["review_items"]),
        "record_count": len(records),
        "safe_option_count": sum(
            1 for item in validated["review_items"] for option in item["target_options"]
            if option["meets_geometry_gate"]
        ),
        "unsafe_option_count": sum(
            1 for item in validated["review_items"] for option in item["target_options"]
            if not option["meets_geometry_gate"]
        ),
        "records": records,
    }


def default_review_plan_path(document: Any | None = None) -> Path | None:
    env_path = os.getenv("AGENTIC_CAD_HUMAN_REVIEW_PLAN")
    if env_path:
        return Path(env_path).expanduser()
    file_name = getattr(document, "FileName", "") if document is not None else ""
    if file_name:
        candidate = Path(file_name).resolve().parent / "wood_screw_human_review_plan.json"
        if candidate.is_file():
            return candidate
    cwd_candidate = Path.cwd() / "wood_screw_human_review_plan.json"
    return cwd_candidate if cwd_candidate.is_file() else None


def visualize_review_plan(path: str | Path | None = None) -> dict[str, Any]:
    """Create overlay geometry in the active FreeCAD document."""
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    document = App.ActiveDocument or App.newDocument("AgenticHumanReview")
    resolved_path = Path(path).expanduser() if path else default_review_plan_path(document)
    if resolved_path is None:
        raise FileNotFoundError("human review plan was not found")
    plan = load_review_plan(resolved_path)
    visualization = build_visualization_records(plan)

    group = document.addObject("App::DocumentObjectGroup", "AgenticHumanReview")
    group.Label = "Agentic Human Review"
    if "AgenticReviewPlanPath" not in group.PropertiesList:
        group.addProperty("App::PropertyString", "AgenticReviewPlanPath", "Agentic", "Review plan path")
    group.AgenticReviewPlanPath = str(resolved_path)

    created = []
    for index, record in enumerate(visualization["records"]):
        obj = document.addObject("Part::Feature", f"AgenticReview_{index:03d}_{record['kind']}")
        obj.Label = record["label"]
        if record["kind"] == "candidate_center":
            obj.Shape = Part.makeSphere(float(record["radius_mm"]), App.Vector(*record["center_mm"]))
        else:
            start = App.Vector(*record["start_mm"])
            end = App.Vector(*record["end_mm"])
            axis = end.sub(start)
            length = axis.Length
            if length <= 1e-9:
                continue
            obj.Shape = Part.makeCylinder(float(record["radius_mm"]), length, start, axis)
        _attach_metadata(obj, record)
        _style_object(obj, tuple(record["color"]))
        group.addObject(obj)
        created.append(obj.Name)
    document.recompute()
    _fit_view()
    return {
        "schema_version": VISUALIZATION_SCHEMA_VERSION,
        "status": "succeeded",
        "review_plan_path": str(resolved_path),
        "group": group.Name,
        "created_object_count": len(created),
        "created_objects": created,
        "review_item_count": visualization["review_item_count"],
        "safe_option_count": visualization["safe_option_count"],
        "unsafe_option_count": visualization["unsafe_option_count"],
    }


def format_visualization_summary(report: dict[str, Any]) -> str:
    return (
        "Agentic human review visualization: "
        f"{report.get('created_object_count', 0)} overlays, "
        f"{report.get('review_item_count', 0)} review items, "
        f"{report.get('safe_option_count', 0)} safe options, "
        f"{report.get('unsafe_option_count', 0)} unsafe options"
    )


def _attach_metadata(obj: Any, record: dict[str, Any]) -> None:
    fields = {
        "AgenticReviewKind": record.get("kind"),
        "AgenticCandidateId": record.get("candidate_id"),
        "AgenticTargetInstanceId": record.get("target_instance_id", ""),
        "AgenticWarnings": ",".join(record.get("warnings", [])),
    }
    for name, value in fields.items():
        if name not in obj.PropertiesList:
            obj.addProperty("App::PropertyString", name, "Agentic", name)
        setattr(obj, name, str(value or ""))


def _style_object(obj: Any, color: tuple[float, float, float]) -> None:
    view = getattr(obj, "ViewObject", None)
    if view is None:
        return
    if hasattr(view, "ShapeColor"):
        view.ShapeColor = color
    if hasattr(view, "Transparency"):
        view.Transparency = 35


def _fit_view() -> None:
    try:
        import FreeCADGui as Gui  # type: ignore

        active = Gui.activeDocument()
        if active:
            active.activeView().viewAxonometric()
            active.activeView().fitAll()
    except Exception:
        return


def _point_at(center: list[float], direction: list[float], offset: float) -> list[float]:
    return [round(center[index] + direction[index] * offset, 6) for index in range(3)]


def _normalize(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 1e-9:
        raise ValueError("direction is zero")
    return [value / length for value in vector]


def _vector(value: Any, length: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == length
        and all(isinstance(item, (int, float)) and math.isfinite(float(item)) for item in value)
    )
