"""Import a review-first architectural scan BIM IR into an active FreeCAD document."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARCHITECTURAL_SCAN_IR = (
    REPO_ROOT
    / "out/product_workspaces/architectural_scan_page2_page7/cad/architectural_scan_rough_bim_ir.json"
)


def import_architectural_scan_ir(ir_path: str | Path | None = None) -> dict[str, Any]:
    """Create detailed proxy objects from an architectural scan IR in FreeCAD.

    The importer deliberately creates reviewable proxy geometry and provenance
    properties. It does not claim that the drawing has been fully verified.
    """
    path = Path(ir_path) if ir_path else DEFAULT_ARCHITECTURAL_SCAN_IR
    data = json.loads(path.read_text(encoding="utf-8"))
    objects = data.get("objects") or []
    if not objects:
        raise ValueError(f"architectural scan IR has no objects: {path}")

    import FreeCAD  # type: ignore
    import Part  # type: ignore

    doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("architectural_scan_page2_page7")
    group = _ensure_group(doc, "Agentic_Architectural_Scan_1F")
    groups_by_kind: dict[str, Any] = {}
    created = []
    doc.openTransaction("Import Agentic Architectural Scan IR")
    try:
        floor_trace = data.get("floor_plate_trace") or {}
        floor_points = floor_trace.get("points_mm") or []
        for item in objects:
            obj = _create_feature(doc, item, floor_points=floor_points)
            if obj is None:
                continue
            kind = str(item.get("kind") or "unknown")
            kind_group = groups_by_kind.get(kind)
            if kind_group is None:
                kind_group = _ensure_group(doc, f"Agentic_{_safe_label(kind)}")
                groups_by_kind[kind] = kind_group
                group.addObject(kind_group)
            kind_group.addObject(obj)
            created.append(obj)
        doc.recompute()
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise

    report = {
        "schema_version": "agentic_architectural_scan_import_report.v1",
        "source_ir": str(path),
        "level": data.get("level"),
        "created_object_count": len(created),
        "source_object_count": len(objects),
        "status": "imported_review_proxy",
        "warnings": [
            "Objects are detailed review proxies; dimensions and source interpretation still require human review.",
            "Door/window proxies are not yet boolean-cut openings in host walls.",
        ],
    }
    _print_message(f"Imported {len(created)} architectural scan proxy objects from {path}")
    return report


def _create_feature(doc: Any, item: dict[str, Any], *, floor_points: list[list[float]] | list[tuple[float, float]]) -> Any | None:
    import FreeCAD  # type: ignore
    import Part  # type: ignore

    item_id = str(item.get("id") or "")
    if not item_id:
        return None
    if item_id == "SLAB-APPROX-ENVELOPE" and floor_points:
        shape = _floor_shape(floor_points)
    else:
        sx, sy, sz = [float(value) for value in item["size"]]
        cx, cy, cz = [float(value) for value in item["center"]]
        shape = _local_shape_for_kind(str(item.get("kind") or "unknown"), sx, sy, sz)
        shape.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), float(item.get("rotation_deg") or 0.0))
        shape.translate(FreeCAD.Vector(cx, cy, cz))

    obj = doc.addObject("Part::Feature", _safe_label(item_id))
    obj.Shape = shape
    obj.Label = f"{item_id} · {item.get('kind', 'unknown')}"
    _set_property(obj, "App::PropertyString", "AgenticSourceId", item_id)
    _set_property(obj, "App::PropertyString", "AgenticKind", str(item.get("kind") or "unknown"))
    _set_property(obj, "App::PropertyString", "SourceEvidence", str(item.get("source") or ""))
    _set_property(obj, "App::PropertyString", "ReviewNote", str(item.get("note") or ""))
    _set_property(obj, "App::PropertyString", "AgenticColorRGBA", json.dumps(item.get("color") or [190, 190, 185, 255]))
    _set_property(obj, "App::PropertyFloat", "InterpretationConfidence", float(item.get("confidence") or 0.0))
    _apply_view_style(obj, item)
    return obj


def _local_shape_for_kind(kind: str, sx: float, sy: float, sz: float) -> Any:
    """Build recognizable local proxy geometry centered around the origin."""
    import FreeCAD  # type: ignore
    import Part  # type: ignore

    if kind in {"round_table_top", "round_table_pedestal"}:
        radius = min(sx, sy) / 2.0
        return Part.makeCylinder(radius, sz, FreeCAD.Vector(0, 0, -sz / 2))

    if kind == "ceramic_toilet_bowl":
        radius = min(sx, sy) * 0.34
        bowl_height = sz * 0.72
        front_y = sy * 0.15
        bowl = Part.makeCylinder(radius, bowl_height, FreeCAD.Vector(0, front_y, -sz / 2))
        rear = Part.makeBox(sx * 0.58, sy * 0.40, sz * 0.58)
        rear.translate(FreeCAD.Vector(-sx * 0.29, -sy * 0.38, -sz / 2))
        rim = Part.makeTorus(radius * 0.94, max(18.0, radius * 0.10), FreeCAD.Vector(0, front_y, -sz / 2 + bowl_height))
        return Part.makeCompound([bowl, rear, rim])

    if kind == "lavatory_basin":
        slab_height = max(45.0, sz * 0.30)
        slab = Part.makeBox(sx, sy, slab_height)
        slab.translate(FreeCAD.Vector(-sx / 2, -sy / 2, sz * 0.12))
        bowl_radius = min(sx, sy) * 0.28
        rim = Part.makeTorus(bowl_radius, max(16.0, bowl_radius * 0.12), FreeCAD.Vector(0, 0, sz * 0.10))
        drain = Part.makeCylinder(max(16.0, bowl_radius * 0.12), max(25.0, sz * 0.22), FreeCAD.Vector(0, 0, -sz * 0.25))
        return Part.makeCompound([slab, rim, drain])

    if kind == "ceramic_urinal_fixture":
        back = Part.makeBox(sx * 0.70, max(55.0, sy * 0.24), sz * 0.82)
        back.translate(FreeCAD.Vector(-sx * 0.35, -sy / 2, -sz * 0.41))
        cup_radius = min(sx, sy) * 0.30
        cup = Part.makeCylinder(cup_radius, max(70.0, sy * 0.42), FreeCAD.Vector(0, -sy * 0.20, -sz * 0.34), FreeCAD.Vector(0, 1, 0))
        rim = Part.makeTorus(cup_radius * 0.92, max(14.0, cup_radius * 0.12), FreeCAD.Vector(0, sy * 0.22, -sz * 0.06), FreeCAD.Vector(0, 1, 0))
        return Part.makeCompound([back, cup, rim])

    if kind == "chair_seat":
        seat = Part.makeBox(sx, sy * 0.78, sz)
        seat.translate(FreeCAD.Vector(-sx / 2, -sy * 0.39, -sz / 2))
        front = Part.makeCylinder(sy * 0.11, sx, FreeCAD.Vector(-sx / 2, sy * 0.28, -sz / 2), FreeCAD.Vector(1, 0, 0))
        return Part.makeCompound([seat, front])

    shape = Part.makeBox(sx, sy, sz)
    shape.translate(FreeCAD.Vector(-sx / 2, -sy / 2, -sz / 2))
    return shape


def _floor_shape(points: list[list[float]] | list[tuple[float, float]]) -> Any:
    import FreeCAD  # type: ignore
    import Part  # type: ignore

    vectors = [FreeCAD.Vector(float(x), float(y), 0.0) for x, y in points]
    vectors.append(vectors[0])
    face = Part.Face(Part.makePolygon(vectors))
    return face.extrude(FreeCAD.Vector(0, 0, -150))


def _set_property(obj: Any, property_type: str, name: str, value: Any) -> None:
    if name not in obj.PropertiesList:
        obj.addProperty(property_type, name, "Agentic", "Agentic CAD import provenance")
    setattr(obj, name, value)


def _apply_view_style(obj: Any, item: dict[str, Any]) -> None:
    view = getattr(obj, "ViewObject", None)
    if view is None:
        return
    color = item.get("color") or [190, 190, 185, 255]
    try:
        rgba = [float(value) for value in color]
    except (TypeError, ValueError):
        return
    if hasattr(view, "ShapeColor"):
        view.ShapeColor = (rgba[0] / 255.0, rgba[1] / 255.0, rgba[2] / 255.0)
    if hasattr(view, "Transparency") and len(rgba) >= 4:
        view.Transparency = max(0, min(90, int(100 - rgba[3] / 255.0 * 100)))


def _ensure_group(doc: Any, label: str) -> Any:
    for obj in getattr(doc, "Objects", []):
        if getattr(obj, "Label", "") == label and getattr(obj, "TypeId", "") == "App::DocumentObjectGroup":
            return obj
    group = doc.addObject("App::DocumentObjectGroup", _safe_label(label))
    group.Label = label
    return group


def _safe_label(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in str(value))
    cleaned = cleaned.strip("_") or "AgenticObject"
    if cleaned[0].isdigit():
        cleaned = f"Agentic_{cleaned}"
    return cleaned[:80]


def _print_message(message: str) -> None:
    try:
        import FreeCAD  # type: ignore

        FreeCAD.Console.PrintMessage(str(message) + "\n")
    except Exception:
        print(message)
