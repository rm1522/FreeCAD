"""Human-readable and structured previews for typed FreeCAD plans."""

from __future__ import annotations

import math
from typing import Any


def build_plan_preview(plan: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build structured before/after evidence for a typed FreeCAD plan."""
    context = context or {}
    operations = plan.get("operations") or []
    objects = context.get("objects") or []
    preview = {
        "schema_version": "agentic_cad_plan_preview.v1",
        "operation_count": len(operations),
        "object_count_before": len(objects),
        "object_count_after": len(objects),
        "mutates_document": False,
        "operations": [],
        "lines": [],
    }
    if not operations:
        preview["lines"].append("[diff] no document changes")
        return preview

    object_count_after = len(objects)
    for index, operation in enumerate(operations, start=1):
        item = _preview_operation(index, operation, objects, object_count_after)
        object_count_after = int(item.get("object_count_after", object_count_after))
        if item.get("mutates_document"):
            preview["mutates_document"] = True
        preview["operations"].append(item)
        preview["lines"].append(_format_legacy_line(item))
    preview["object_count_after"] = object_count_after
    return preview


def build_plan_preview_lines(plan: dict[str, Any], context: dict[str, Any] | None = None) -> list[str]:
    """Summarize likely document changes before the user approves execution."""
    return list(build_plan_preview(plan, context).get("lines", []))


def format_plan_preview(preview: dict[str, Any]) -> str:
    """Format structured preview details for the FreeCAD Dock."""
    lines = [
        "Plan Preview",
        f"Operations: {preview.get('operation_count', 0)}",
        f"Objects: {preview.get('object_count_before', 0)} -> {preview.get('object_count_after', 0)}",
        f"Mutates document: {bool(preview.get('mutates_document'))}",
    ]
    for item in preview.get("operations", []):
        lines.append("")
        lines.append(f"#{item.get('index')} {item.get('title')}")
        lines.append(f"Before: {item.get('before', '')}")
        lines.append(f"After: {item.get('after', '')}")
        verify = item.get("verify")
        if verify:
            lines.append(f"Verify: {verify}")
        warning = item.get("warning")
        if warning:
            lines.append(f"Warning: {warning}")
    return "\n".join(lines)


def _preview_operation(
    index: int,
    operation: dict[str, Any],
    objects: list[dict[str, Any]],
    object_count_before: int,
) -> dict[str, Any]:
    operation_type = operation.get("type")
    arguments = operation.get("arguments") or {}
    if operation_type == "primitive.create_box":
        length = _float_or_none(arguments.get("length_mm"))
        width = _float_or_none(arguments.get("width_mm"))
        height = _float_or_none(arguments.get("height_mm"))
        bbox = _bbox_or_none(length, width, height)
        return {
            "index": index,
            "type": operation_type,
            "title": f"Add Part::Box {arguments.get('label') or ''}".strip(),
            "mutates_document": True,
            "object_count_before": object_count_before,
            "object_count_after": object_count_before + 1,
            "before": f"objects={object_count_before}",
            "after": f"objects={object_count_before + 1}, bbox={_fmt_bbox(bbox)}, volume={_fmt_volume(_box_volume(bbox))}",
            "verify": "new object has valid shape and measured bbox after recompute",
            "legacy": (
                "[diff] add Part::Box "
                f"{_dims(arguments, ('length_mm', 'width_mm', 'height_mm'))}; "
                f"objects {object_count_before} -> {object_count_before + 1}"
            ),
        }
    if operation_type == "bim.create_element":
        length = _float_or_none(arguments.get("length_mm"))
        width = _float_or_none(arguments.get("width_mm"))
        height = _float_or_none(arguments.get("height_mm"))
        bbox = _bbox_or_none(length, width, height)
        ifc_type = str(arguments.get("ifc_type") or "IfcBuildingElementProxy")
        return {
            "index": index,
            "type": operation_type,
            "title": f"Add {ifc_type} {arguments.get('label') or ''}".strip(),
            "mutates_document": True,
            "object_count_before": object_count_before,
            "object_count_after": object_count_before + 1,
            "before": f"objects={object_count_before}",
            "after": (
                f"objects={object_count_before + 1}, ifc_type={ifc_type}, "
                f"bbox={_fmt_bbox(bbox)}, volume={_fmt_volume(_box_volume(bbox))}"
            ),
            "verify": "new object has valid shape, IFC classification, and source evidence refs after recompute",
            "legacy": (
                f"[diff] add {ifc_type} "
                f"{_dims(arguments, ('length_mm', 'width_mm', 'height_mm'))}; "
                f"objects {object_count_before} -> {object_count_before + 1}"
            ),
        }
    if operation_type == "primitive.create_cylinder":
        radius = _float_or_none(arguments.get("radius_mm"))
        height = _float_or_none(arguments.get("height_mm"))
        diameter = radius * 2.0 if radius is not None else None
        bbox = _bbox_or_none(diameter, diameter, height)
        volume = math.pi * radius * radius * height if radius is not None and height is not None else None
        return {
            "index": index,
            "type": operation_type,
            "title": f"Add Part::Cylinder {arguments.get('label') or ''}".strip(),
            "mutates_document": True,
            "object_count_before": object_count_before,
            "object_count_after": object_count_before + 1,
            "before": f"objects={object_count_before}",
            "after": f"objects={object_count_before + 1}, bbox={_fmt_bbox(bbox)}, volume={_fmt_volume(volume)}",
            "verify": "new object has valid shape and measured bbox after recompute",
            "legacy": (
                "[diff] add Part::Cylinder "
                f"radius={arguments.get('radius_mm')}mm height={arguments.get('height_mm')}mm; "
                f"objects {object_count_before} -> {object_count_before + 1}"
            ),
        }
    if operation_type == "object.update_parameters":
        target_id = str(operation.get("target") or "")
        target = _find_context_object(objects, target_id)
        label = target.get("label") or target.get("name") if target else target_id
        old_dimensions = _shape_dimensions(target)
        new_dimensions = dict(old_dimensions)
        changes = []
        for key, value in (arguments.get("parameters") or {}).items():
            old = old_dimensions.get(key)
            new_value = _float_or_none(value)
            if new_value is not None:
                new_dimensions[key] = new_value
            if old is None:
                changes.append(f"{key}: ? -> {value}mm")
            else:
                changes.append(f"{key}: {old}mm -> {value}mm")
        old_bbox = _dimensions_to_bbox(old_dimensions)
        new_bbox = _dimensions_to_bbox(new_dimensions)
        return {
            "index": index,
            "type": operation_type,
            "title": f"Update {label} ({target_id})",
            "mutates_document": True,
            "object_count_before": object_count_before,
            "object_count_after": object_count_before,
            "before": f"bbox={_fmt_bbox(old_bbox)}, volume={_fmt_volume(_box_volume(old_bbox))}",
            "after": f"bbox={_fmt_bbox(new_bbox)}, volume={_fmt_volume(_box_volume(new_bbox))}",
            "verify": "target stable ID resolves and measured bbox reflects requested parameters",
            "warning": "target object was not found in context" if target is None else "",
            "legacy": f"[diff] update {label} ({target_id}): " + ", ".join(changes),
        }
    if operation_type == "object.translate":
        target_id = str(operation.get("target") or "")
        target = _find_context_object(objects, target_id)
        label = target.get("label") or target.get("name") if target else target_id
        translation = arguments.get("translation_mm") or []
        translation_text = _fmt_translation(translation)
        return {
            "index": index,
            "type": operation_type,
            "title": f"Move {label} ({target_id})",
            "mutates_document": True,
            "object_count_before": object_count_before,
            "object_count_after": object_count_before,
            "before": "placement=current document placement",
            "after": f"placement=current + {translation_text}",
            "verify": "target stable ID resolves and shape remains valid after recompute",
            "warning": "target object was not found in context" if target is None else "",
            "legacy": f"[diff] move {label} ({target_id}) by {translation_text}",
        }
    if operation_type == "document.undo":
        return {
            "index": index,
            "type": operation_type,
            "title": "Undo Previous Transaction",
            "mutates_document": True,
            "object_count_before": object_count_before,
            "object_count_after": object_count_before,
            "before": f"objects={object_count_before}",
            "after": "previous transaction is rolled back by FreeCAD undo stack",
            "verify": "document context is re-read after undo",
            "legacy": "[diff] undo previous document transaction",
        }
    if operation_type == "document.inspect":
        return {
            "index": index,
            "type": operation_type,
            "title": "Inspect Document",
            "mutates_document": False,
            "object_count_before": object_count_before,
            "object_count_after": object_count_before,
            "before": f"objects={object_count_before}",
            "after": "no document changes",
            "verify": "read-only context only",
            "legacy": f"[diff] inspect only; objects stay {object_count_before}",
        }
    modeling_preview = _preview_modeling_operation(index, operation, object_count_before)
    if modeling_preview is not None:
        return modeling_preview
    return {
        "index": index,
        "type": operation_type,
        "title": str(operation_type),
        "mutates_document": True,
        "object_count_before": object_count_before,
        "object_count_after": object_count_before,
        "before": f"objects={object_count_before}",
        "after": "unknown typed operation effect",
        "warning": "preview support is incomplete for this operation type",
        "legacy": f"[diff] {operation_type}",
    }


def _preview_modeling_operation(
    index: int,
    operation: dict[str, Any],
    object_count_before: int,
) -> dict[str, Any] | None:
    """Compact previews for the typed sketch/PartDesign modeling vocabulary."""
    operation_type = str(operation.get("type"))
    arguments = operation.get("arguments") or {}
    target = str(operation.get("target") or "")
    creates_object = True
    verify = "new object has valid shape evidence after recompute"
    if operation_type == "sketch.create":
        summary = f"sketch on {arguments.get('plane')} plane"
        if arguments.get("body_target"):
            summary += f" in body {arguments.get('body_target')}"
        verify = "sketch exists and the constraint solver reports success"
    elif operation_type == "sketch.add_geometry":
        creates_object = False
        kinds = [str(item.get("kind")) for item in arguments.get("geometry") or []]
        summary = f"add {len(kinds)} geometry ({', '.join(kinds)}) to {target}"
        verify = "geometry indices are returned and the sketch still solves"
    elif operation_type == "sketch.add_constraint":
        creates_object = False
        kinds = [str(item.get("kind")) for item in arguments.get("constraints") or []]
        summary = f"add {len(kinds)} constraints ({', '.join(kinds)}) to {target}"
        verify = "constraint solver returns success after recompute"
    elif operation_type == "partdesign.create_body":
        summary = "empty PartDesign body"
        verify = "body exists as a feature container"
    elif operation_type == "partdesign.pad":
        summary = f"pad {target} by {arguments.get('length_mm')}mm"
    elif operation_type == "partdesign.pocket":
        depth = "through all" if arguments.get("through_all") else f"{arguments.get('length_mm')}mm"
        summary = f"pocket {target} {depth}"
    elif operation_type == "partdesign.revolution":
        summary = f"revolve {target} by {arguments.get('angle_deg')} deg"
    elif operation_type == "partdesign.hole":
        positions = arguments.get("positions") or []
        summary = f"cut {len(positions)} holes Ø{arguments.get('diameter_mm')}mm into {target}"
    else:
        return None
    object_count_after = object_count_before + (1 if creates_object else 0)
    return {
        "index": index,
        "type": operation_type,
        "title": f"{operation_type}: {summary}",
        "mutates_document": True,
        "object_count_before": object_count_before,
        "object_count_after": object_count_after,
        "before": f"objects={object_count_before}",
        "after": f"objects={object_count_after}, {summary}",
        "verify": verify,
        "legacy": f"[diff] {operation_type} {summary}",
    }


def _format_legacy_line(item: dict[str, Any]) -> str:
    return str(item.get("legacy") or f"[diff] {item.get('type')}")


def _dims(arguments: dict[str, Any], keys: tuple[str, ...]) -> str:
    return " x ".join(f"{arguments.get(key)}mm" for key in keys)


def _find_context_object(objects: list[dict[str, Any]], stable_id: str) -> dict[str, Any] | None:
    for obj in objects:
        if obj.get("stable_id") == stable_id or obj.get("name") == stable_id:
            return obj
    return None


def _shape_dimensions(obj: dict[str, Any] | None) -> dict[str, float]:
    if not obj:
        return {}
    shape = obj.get("shape") or {}
    bbox = shape.get("bbox_mm") or []
    if len(bbox) != 3:
        return {}
    return {
        "length": float(bbox[0]),
        "width": float(bbox[1]),
        "height": float(bbox[2]),
    }


def _dimensions_to_bbox(dimensions: dict[str, float]) -> list[float] | None:
    if not all(key in dimensions for key in ("length", "width", "height")):
        return None
    return [dimensions["length"], dimensions["width"], dimensions["height"]]


def _bbox_or_none(*values: float | None) -> list[float] | None:
    if any(value is None for value in values):
        return None
    return [float(value) for value in values if value is not None]


def _box_volume(bbox: list[float] | None) -> float | None:
    if not bbox or len(bbox) != 3:
        return None
    return float(bbox[0]) * float(bbox[1]) * float(bbox[2])


def _fmt_bbox(bbox: list[float] | None) -> str:
    if not bbox:
        return "unknown"
    return " x ".join(f"{value:g}mm" for value in bbox)


def _fmt_translation(value: Any) -> str:
    if not isinstance(value, list) or len(value) != 3:
        return "unknown"
    try:
        return "[" + ", ".join(f"{float(component):g}mm" for component in value) + "]"
    except (TypeError, ValueError):
        return "unknown"


def _fmt_volume(volume: float | None) -> str:
    if volume is None:
        return "unknown"
    return f"{volume:g}mm^3"


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None
