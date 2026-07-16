"""Execute allow-listed typed operations inside a FreeCAD document transaction."""

from __future__ import annotations

import math
import json
import os
import uuid
from typing import Any

from services.capability_registry import CAPABILITIES


ALLOWED_OPERATIONS = {str(item["name"]) for item in CAPABILITIES}
MUTATING_OPERATIONS = {
    str(item["name"]) for item in CAPABILITIES if bool(item.get("mutates_document"))
}
PARAMETER_PROPERTIES = {
    "length": "Length",
    "width": "Width",
    "height": "Height",
    "radius": "Radius",
}
MAX_TRANSLATION_MM = 1_000_000.0
MAX_SKETCH_COORDINATE_MM = 1_000_000.0
TARGET_REQUIRED_OPERATIONS = {
    "object.update_parameters",
    "object.translate",
    "sketch.add_geometry",
    "sketch.add_constraint",
    "partdesign.pad",
    "partdesign.pocket",
    "partdesign.revolution",
    "partdesign.hole",
    "partdesign.fillet",
    "partdesign.chamfer",
    "partdesign.mirror",
    "partdesign.linear_pattern",
    "techdraw.add_view",
    "techdraw.add_dimension",
    "techdraw.add_bom_table",
    "techdraw.add_balloon",
    "techdraw.add_section_view",
    "techdraw.add_detail_view",
    "techdraw.add_pmi_note",
}
REVOLUTION_AXES = {"v_axis": "V_Axis", "h_axis": "H_Axis"}
PATTERN_AXES = {"x": "X_Axis", "y": "Y_Axis", "z": "Z_Axis"}
MAX_PATTERN_OCCURRENCES = 64
ALIAS_REF_PREFIX = "@alias:"
CREATION_OPERATIONS = {
    "primitive.create_box",
    "primitive.create_cylinder",
    "bim.create_element",
    "sketch.create",
    "partdesign.create_body",
    "partdesign.pad",
    "partdesign.pocket",
    "partdesign.revolution",
    "partdesign.hole",
    "partdesign.fillet",
    "partdesign.chamfer",
    "partdesign.mirror",
    "partdesign.linear_pattern",
    "techdraw.create_page",
    "techdraw.add_view",
    "techdraw.add_dimension",
    "techdraw.add_bom_table",
    "techdraw.add_balloon",
    "techdraw.add_section_view",
    "techdraw.add_detail_view",
    "techdraw.add_pmi_note",
}
SKETCH_PLANE_NORMALS = {
    "XY": (0.0, 0.0, 1.0),
    "XZ": (0.0, -1.0, 0.0),
    "YZ": (1.0, 0.0, 0.0),
}
SKETCH_PLANES = ("XY", "XZ", "YZ")
SKETCH_POINT_CODES = {"start": 1, "end": 2, "center": 3}
SKETCH_GEOMETRY_KINDS = ("line", "circle", "arc", "rectangle")
SKETCH_CONSTRAINT_KINDS = (
    "coincident",
    "horizontal",
    "vertical",
    "distance",
    "distance_x",
    "distance_y",
    "radius",
    "diameter",
    "angle",
    "symmetric",
)
TECHDRAW_DIMENSION_TYPES = ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter")
MAX_TECHDRAW_BOM_ROWS = 256
MAX_TECHDRAW_PMI_TEXT_LENGTH = 160
TECHDRAW_PMI_NOTE_TYPES = ("datum", "feature_control_frame", "tolerance_note", "inspection_note")
TECHDRAW_DIRECTIONS = {
    "front": (0.0, 0.0, 1.0),
    "top": (0.0, 1.0, 0.0),
    "right": (1.0, 0.0, 0.0),
    "isometric": (1.0, 1.0, 1.0),
}
MAX_IFC_TYPE_LENGTH = 80


def validate_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Reject unknown or malformed operations before touching the document."""
    if plan.get("schema_version") != "freecad_tool_plan.v0":
        raise ValueError("Unsupported FreeCAD tool plan schema")
    if plan.get("status") != "ready":
        raise ValueError("Only ready plans can be executed")
    operations = plan.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("The plan contains no operations")
    declared_aliases: set[str] = set()
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("Operation must be an object")
        operation_type = operation.get("type")
        if operation_type not in ALLOWED_OPERATIONS:
            raise ValueError(f"Operation is not allow-listed: {operation_type}")
        if operation_type in TARGET_REQUIRED_OPERATIONS and not operation.get("target"):
            raise ValueError(f"Operation target is required: {operation_type}")
        arguments = operation.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise ValueError("Operation arguments must be an object")
        _validate_operation_alias(operation, operation_type, arguments, declared_aliases)
        if operation_type == "sketch.create" and arguments.get("plane") not in SKETCH_PLANES:
            raise ValueError(f"Sketch plane must be one of {SKETCH_PLANES}")
        if operation_type == "sketch.add_geometry":
            _validate_sketch_geometry_arguments(arguments)
        if operation_type == "sketch.add_constraint":
            _validate_sketch_constraint_arguments(arguments)
        if operation_type.startswith("partdesign."):
            _validate_partdesign_arguments(operation_type, arguments)
        if operation_type == "bim.create_element":
            _validate_bim_element_arguments(arguments)
        if operation_type.startswith("techdraw."):
            _validate_techdraw_arguments(operation_type, arguments)
        for key, value in arguments.items():
            if key == "translation_mm":
                _validate_translation(value)
                continue
            if key == "section_origin_mm":
                continue
            if key == "plane_offset_mm":
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or abs(float(value)) > MAX_SKETCH_COORDINATE_MM:
                    raise ValueError("plane_offset_mm must be a bounded finite number")
                continue
            if key.endswith("_mm") and (not isinstance(value, (int, float)) or value <= 0):
                raise ValueError(f"Dimension must be positive: {key}")
        parameters = arguments.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise ValueError("Operation parameters must be an object")
        for key, value in parameters.items():
            if key not in PARAMETER_PROPERTIES:
                raise ValueError(f"Unsupported parameter: {key}")
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"Parameter must be positive: {key}")
    return operations


def requires_user_approval(plan: dict[str, Any]) -> bool:
    """Return whether a valid plan mutates the FreeCAD document."""
    return any(operation["type"] in MUTATING_OPERATIONS for operation in validate_plan(plan))


def _validate_bim_element_arguments(arguments: dict[str, Any]) -> None:
    ifc_type = arguments.get("ifc_type")
    if not isinstance(ifc_type, str) or not ifc_type.startswith("Ifc") or len(ifc_type) > MAX_IFC_TYPE_LENGTH:
        raise ValueError("bim.create_element requires a bounded IFC entity name starting with Ifc")
    predefined_type = arguments.get("predefined_type", "NOTDEFINED")
    if not isinstance(predefined_type, str) or not predefined_type.strip() or len(predefined_type) > MAX_IFC_TYPE_LENGTH:
        raise ValueError("bim.create_element predefined_type must be a bounded non-empty string")
    evidence_refs = arguments.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        raise ValueError("bim.create_element requires source evidence refs")


def _shape_payload(obj: Any) -> dict[str, Any] | None:
    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        return None
    bbox = shape.BoundBox
    dimensions = (bbox.XLength, bbox.YLength, bbox.ZLength)
    if any(not math.isfinite(float(value)) or abs(float(value)) > 1_000_000_000 for value in dimensions):
        return None
    return {
        "valid": bool(shape.isValid()),
        "bbox_mm": [round(float(value), 3) for value in dimensions],
        "volume_mm3": round(float(shape.Volume), 3),
    }


def _object_payload(obj: Any) -> dict[str, Any]:
    stable_id = getattr(obj, "AgenticStableId", "")
    payload = {
        "name": obj.Name,
        "label": obj.Label,
        "type_id": obj.TypeId,
        "stable_id": stable_id or obj.Name,
        "shape": _shape_payload(obj),
    }
    if hasattr(obj, "IfcType"):
        payload["ifc_type"] = str(obj.IfcType)
    if hasattr(obj, "PredefinedType"):
        payload["predefined_type"] = str(obj.PredefinedType)
    if hasattr(obj, "AgenticBIMKind"):
        payload["bim_kind"] = str(obj.AgenticBIMKind)
    return payload


def get_document_context() -> dict[str, Any]:
    """Read the active document and GUI selection for planner grounding."""
    import FreeCAD  # type: ignore
    try:
        import FreeCADGui as Gui  # type: ignore
    except ImportError:
        Gui = None
    if Gui is not None and not hasattr(Gui, "Selection"):
        Gui = None

    document = FreeCAD.ActiveDocument
    if document is None:
        return {"document": None, "objects": [], "selection": []}

    selected_names: set[str] = set()
    if Gui:
        for selected in Gui.Selection.getSelection():
            candidate = selected
            if not getattr(candidate, "AgenticStableId", ""):
                tip = getattr(candidate, "Tip", None)
                if tip is not None and getattr(tip, "AgenticStableId", ""):
                    candidate = tip
            selected_names.add(candidate.Name)

    objects = [_object_payload(obj) for obj in document.Objects]
    return {
        "document": {
            "name": document.Name,
            "label": document.Label,
            "file_name": getattr(document, "FileName", ""),
        },
        "objects": objects,
        "selection": [item for item in objects if item["name"] in selected_names],
    }


def _attach_agent_metadata(obj: Any, stable_id: str, plan_id: str) -> None:
    if "AgenticStableId" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "AgenticStableId", "Agentic", "Stable agent object ID")
    if "AgenticPlanId" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "AgenticPlanId", "Agentic", "Plan that created this object")
    obj.AgenticStableId = stable_id
    obj.AgenticPlanId = plan_id


def _attach_evidence_metadata(obj: Any, arguments: dict[str, Any]) -> None:
    evidence_refs = arguments.get("evidence_refs")
    if evidence_refs is not None:
        if "AgenticEvidenceRefs" not in obj.PropertiesList:
            obj.addProperty("App::PropertyString", "AgenticEvidenceRefs", "Agentic", "Source evidence references")
        obj.AgenticEvidenceRefs = json.dumps(evidence_refs, ensure_ascii=False, sort_keys=True)
    bim_kind = arguments.get("bim_kind")
    if bim_kind:
        if "AgenticBIMKind" not in obj.PropertiesList:
            obj.addProperty("App::PropertyString", "AgenticBIMKind", "Agentic", "Evidence-derived BIM category")
        obj.AgenticBIMKind = str(bim_kind)
    if arguments.get("preview_only") is True:
        if "AgenticPreviewOnly" not in obj.PropertiesList:
            obj.addProperty("App::PropertyBool", "AgenticPreviewOnly", "Agentic", "Marks provisional preview geometry")
        obj.AgenticPreviewOnly = True


def _ensure_part_objects_registered() -> None:
    """Load the Part module so FreeCADCmd registers Part::Box/Cylinder types."""
    import Part  # type: ignore  # noqa: F401


def _create_box(document: Any, arguments: dict[str, Any], plan_id: str) -> Any:
    _ensure_part_objects_registered()
    suffix = uuid.uuid4().hex[:8]
    feature = document.addObject("Part::Box", f"AgenticBox_{suffix}")
    feature.Label = arguments.get("label") or "Agentic Box"
    feature.Length = float(arguments["length_mm"])
    feature.Width = float(arguments["width_mm"])
    feature.Height = float(arguments["height_mm"])
    _attach_agent_metadata(feature, str(arguments.get("stable_id") or f"agentic-box-{suffix}"), plan_id)
    _attach_evidence_metadata(feature, arguments)
    return feature


def _create_bim_element(document: Any, arguments: dict[str, Any], plan_id: str) -> Any:
    _ensure_part_objects_registered()
    import Part  # type: ignore

    suffix = uuid.uuid4().hex[:8]
    feature = document.addObject("Part::Feature", f"AgenticBIMElement_{suffix}")
    feature.Label = arguments.get("label") or "Agentic BIM Element"
    feature.Shape = Part.makeBox(
        float(arguments["length_mm"]),
        float(arguments["width_mm"]),
        float(arguments["height_mm"]),
    )
    feature.addProperty("App::PropertyString", "IfcType", "IFC", "IFC entity type")
    feature.addProperty("App::PropertyString", "PredefinedType", "IFC", "IFC predefined type")
    feature.addProperty("App::PropertyMap", "IfcProperties", "IFC", "Typed IFC property values")
    feature.IfcType = str(arguments["ifc_type"])
    feature.PredefinedType = str(arguments.get("predefined_type") or "NOTDEFINED")
    feature.IfcProperties = {
        "AgenticSource": "typed_bim_create_element",
        "BIMKind": str(arguments.get("bim_kind") or "generic"),
    }
    _attach_agent_metadata(feature, str(arguments.get("stable_id") or f"agentic-bim-{suffix}"), plan_id)
    _attach_evidence_metadata(feature, arguments)
    return feature


def _create_cylinder(document: Any, arguments: dict[str, Any], plan_id: str) -> Any:
    _ensure_part_objects_registered()
    suffix = uuid.uuid4().hex[:8]
    feature = document.addObject("Part::Cylinder", f"AgenticCylinder_{suffix}")
    feature.Label = arguments.get("label") or "Agentic Cylinder"
    feature.Radius = float(arguments["radius_mm"])
    feature.Height = float(arguments["height_mm"])
    _attach_agent_metadata(feature, f"agentic-cylinder-{suffix}", plan_id)
    return feature


def _find_target(document: Any, stable_id: str) -> Any:
    for obj in document.Objects:
        if obj.Name == stable_id or getattr(obj, "AgenticStableId", "") == stable_id:
            return obj
    raise ValueError(f"Target object no longer exists: {stable_id}")


def _update_parameters(document: Any, operation: dict[str, Any]) -> tuple[Any, dict[str, float]]:
    target = _find_target(document, str(operation.get("target") or ""))
    changed = {}
    for parameter, value in operation["arguments"]["parameters"].items():
        property_name = PARAMETER_PROPERTIES[parameter]
        if property_name not in target.PropertiesList:
            raise ValueError(f"{target.Label} does not support {parameter}")
        setattr(target, property_name, float(value))
        changed[parameter] = float(value)
    return target, changed


def _translate_object(document: Any, operation: dict[str, Any]) -> tuple[Any, list[float]]:
    target = _find_target(document, str(operation.get("target") or ""))
    translation = [float(value) for value in operation["arguments"]["translation_mm"]]
    import FreeCAD  # type: ignore

    placement = target.Placement
    placement.Base = placement.Base + FreeCAD.Vector(*translation)
    target.Placement = placement
    return target, translation


def _plane_rotation(plane: str) -> Any:
    import FreeCAD  # type: ignore

    if plane == "XZ":
        return FreeCAD.Rotation(FreeCAD.Vector(1.0, 0.0, 0.0), 90.0)
    if plane == "YZ":
        return FreeCAD.Rotation(FreeCAD.Vector(1.0, 1.0, 1.0), 120.0)
    return FreeCAD.Rotation(FreeCAD.Vector(0.0, 0.0, 1.0), 0.0)


def _ensure_sketcher_registered() -> None:
    """Load the Sketcher module so FreeCADCmd registers Sketcher::SketchObject."""
    import Sketcher  # type: ignore  # noqa: F401


def _ensure_partdesign_registered() -> None:
    """Load the PartDesign module so FreeCADCmd registers PartDesign object types."""
    try:
        import _PartDesign  # type: ignore  # noqa: F401
    except ImportError:
        try:
            import PartDesign  # type: ignore  # noqa: F401
        except ImportError:
            return


def _ensure_techdraw_registered() -> None:
    """Load the TechDraw module so FreeCADCmd registers drawing object types."""
    import TechDraw  # type: ignore  # noqa: F401


def _ensure_spreadsheet_registered() -> None:
    """Load the Spreadsheet module so FreeCADCmd registers Spreadsheet::Sheet."""
    import Spreadsheet  # type: ignore  # noqa: F401


def _create_sketch(document: Any, arguments: dict[str, Any], plan_id: str) -> Any:
    _ensure_sketcher_registered()
    suffix = uuid.uuid4().hex[:8]
    sketch = document.addObject("Sketcher::SketchObject", f"AgenticSketch_{suffix}")
    sketch.Label = arguments.get("label") or "Agentic Sketch"
    placement = sketch.Placement
    placement.Rotation = _plane_rotation(str(arguments.get("plane")))
    sketch.Placement = placement
    body_target = arguments.get("body_target")
    if body_target:
        body = _find_target(document, str(body_target))
        add_object = getattr(body, "addObject", None)
        if not callable(add_object):
            raise ValueError(f"body_target cannot contain a sketch: {body.Label}")
        add_object(sketch)
    _attach_agent_metadata(sketch, f"agentic-sketch-{suffix}", plan_id)
    return sketch


def _sketch_target(document: Any, operation: dict[str, Any]) -> Any:
    target = _find_target(document, str(operation.get("target") or ""))
    if not str(getattr(target, "TypeId", "")).startswith("Sketcher::"):
        raise ValueError(f"Target is not a sketch: {target.Label}")
    return target


def _sketch_vector(point: list[Any]) -> Any:
    import FreeCAD  # type: ignore

    return FreeCAD.Vector(float(point[0]), float(point[1]), 0.0)


def _sketch_normal() -> Any:
    import FreeCAD  # type: ignore

    return FreeCAD.Vector(0.0, 0.0, 1.0)


def _add_one_geometry(sketch: Any, spec: dict[str, Any]) -> list[int]:
    import Part  # type: ignore

    kind = spec["kind"]
    if kind == "line":
        segment = Part.LineSegment(_sketch_vector(spec["start"]), _sketch_vector(spec["end"]))
        return [int(sketch.addGeometry(segment, False))]
    if kind == "circle":
        circle = Part.Circle(_sketch_vector(spec["center"]), _sketch_normal(), float(spec["radius_mm"]))
        return [int(sketch.addGeometry(circle, False))]
    if kind == "arc":
        base_circle = Part.Circle(
            _sketch_vector(spec["center"]),
            _sketch_normal(),
            float(spec["radius_mm"]),
        )
        arc = Part.ArcOfCircle(
            base_circle,
            math.radians(float(spec["start_angle_deg"])),
            math.radians(float(spec["end_angle_deg"])),
        )
        return [int(sketch.addGeometry(arc, False))]
    if kind == "rectangle":
        return _add_rectangle(sketch, spec)
    raise ValueError(f"Unsupported sketch geometry kind: {kind}")


def _add_rectangle(sketch: Any, spec: dict[str, Any]) -> list[int]:
    import Part  # type: ignore
    import Sketcher  # type: ignore

    x0, y0 = (float(value) for value in spec["corner"])
    x1 = x0 + float(spec["width_mm"])
    y1 = y0 + float(spec["height_mm"])
    corners = ([x0, y0], [x1, y0], [x1, y1], [x0, y1])
    indices: list[int] = []
    for start, end in zip(corners, corners[1:] + corners[:1]):
        segment = Part.LineSegment(_sketch_vector(start), _sketch_vector(end))
        indices.append(int(sketch.addGeometry(segment, False)))
    end_point = SKETCH_POINT_CODES["end"]
    start_point = SKETCH_POINT_CODES["start"]
    for first, second in zip(indices, indices[1:] + indices[:1]):
        sketch.addConstraint(Sketcher.Constraint("Coincident", first, end_point, second, start_point))
    sketch.addConstraint(Sketcher.Constraint("Horizontal", indices[0]))
    sketch.addConstraint(Sketcher.Constraint("Horizontal", indices[2]))
    sketch.addConstraint(Sketcher.Constraint("Vertical", indices[1]))
    sketch.addConstraint(Sketcher.Constraint("Vertical", indices[3]))
    return indices


def _add_sketch_geometry(document: Any, operation: dict[str, Any]) -> tuple[Any, list[int]]:
    sketch = _sketch_target(document, operation)
    indices: list[int] = []
    for spec in operation["arguments"]["geometry"]:
        indices.extend(_add_one_geometry(sketch, spec))
    return sketch, indices


def _add_one_constraint(sketch: Any, spec: dict[str, Any]) -> None:
    import Sketcher  # type: ignore

    kind = spec["kind"]
    codes = SKETCH_POINT_CODES
    if kind == "coincident":
        first, second = spec["first"], spec["second"]
        sketch.addConstraint(
            Sketcher.Constraint("Coincident", first["index"], codes[first["point"]], second["index"], codes[second["point"]])
        )
    elif kind in {"horizontal", "vertical"}:
        sketch.addConstraint(Sketcher.Constraint(kind.capitalize(), spec["index"]))
    elif kind == "distance":
        if "index" in spec:
            sketch.addConstraint(Sketcher.Constraint("Distance", spec["index"], float(spec["value_mm"])))
        else:
            first, second = spec["first"], spec["second"]
            sketch.addConstraint(
                Sketcher.Constraint(
                    "Distance",
                    first["index"],
                    codes[first["point"]],
                    second["index"],
                    codes[second["point"]],
                    float(spec["value_mm"]),
                )
            )
    elif kind in {"distance_x", "distance_y"}:
        constraint_name = "DistanceX" if kind == "distance_x" else "DistanceY"
        first, second = spec["first"], spec["second"]
        sketch.addConstraint(
            Sketcher.Constraint(
                constraint_name,
                first["index"],
                codes[first["point"]],
                second["index"],
                codes[second["point"]],
                float(spec["value_mm"]),
            )
        )
    elif kind in {"radius", "diameter"}:
        sketch.addConstraint(Sketcher.Constraint(kind.capitalize(), spec["index"], float(spec["value_mm"])))
    elif kind == "angle":
        sketch.addConstraint(
            Sketcher.Constraint("Angle", spec["first_index"], spec["second_index"], math.radians(float(spec["value_deg"])))
        )
    elif kind == "symmetric":
        first, second = spec["first"], spec["second"]
        sketch.addConstraint(
            Sketcher.Constraint(
                "Symmetric",
                first["index"],
                codes[first["point"]],
                second["index"],
                codes[second["point"]],
                spec["reference_index"],
            )
        )
    else:
        raise ValueError(f"Unsupported sketch constraint kind: {kind}")


def _add_sketch_constraints(document: Any, operation: dict[str, Any]) -> tuple[Any, int]:
    sketch = _sketch_target(document, operation)
    count = 0
    for spec in operation["arguments"]["constraints"]:
        _add_one_constraint(sketch, spec)
        count += 1
    return sketch, count


def _create_partdesign_body(document: Any, arguments: dict[str, Any], plan_id: str) -> Any:
    _ensure_partdesign_registered()
    suffix = uuid.uuid4().hex[:8]
    body = document.addObject("PartDesign::Body", f"AgenticBody_{suffix}")
    body.Label = arguments.get("label") or "Agentic Body"
    _attach_agent_metadata(body, f"agentic-body-{suffix}", plan_id)
    return body


def _find_body_of_sketch(document: Any, sketch: Any) -> Any:
    for obj in document.Objects:
        if str(getattr(obj, "TypeId", "")) == "PartDesign::Body" and sketch in (getattr(obj, "Group", None) or []):
            return obj
    raise ValueError(f"Sketch is not inside a PartDesign body: {sketch.Label}")


def _new_body_feature(document: Any, body: Any, type_id: str, name: str) -> Any:
    new_object = getattr(body, "newObject", None)
    if callable(new_object):
        return new_object(type_id, name)
    feature = document.addObject(type_id, name)
    body.addObject(feature)
    return feature


def _create_pad(document: Any, operation: dict[str, Any], plan_id: str) -> Any:
    sketch = _sketch_target(document, operation)
    body = _find_body_of_sketch(document, sketch)
    arguments = operation["arguments"]
    suffix = uuid.uuid4().hex[:8]
    feature = _new_body_feature(document, body, "PartDesign::Pad", f"AgenticPad_{suffix}")
    feature.Profile = sketch
    feature.Length = float(arguments["length_mm"])
    if arguments.get("symmetric"):
        feature.Midplane = True
    if arguments.get("reversed"):
        feature.Reversed = True
    feature.Label = arguments.get("label") or "Agentic Pad"
    _attach_agent_metadata(feature, f"agentic-pad-{suffix}", plan_id)
    return feature


def _create_pocket(document: Any, operation: dict[str, Any], plan_id: str) -> Any:
    sketch = _sketch_target(document, operation)
    body = _find_body_of_sketch(document, sketch)
    arguments = operation["arguments"]
    suffix = uuid.uuid4().hex[:8]
    feature = _new_body_feature(document, body, "PartDesign::Pocket", f"AgenticPocket_{suffix}")
    feature.Profile = sketch
    if arguments.get("through_all"):
        feature.Type = "ThroughAll"
    else:
        feature.Length = float(arguments["length_mm"])
    if arguments.get("reversed"):
        feature.Reversed = True
    feature.Label = arguments.get("label") or "Agentic Pocket"
    _attach_agent_metadata(feature, f"agentic-pocket-{suffix}", plan_id)
    return feature


def _create_revolution(document: Any, operation: dict[str, Any], plan_id: str) -> Any:
    sketch = _sketch_target(document, operation)
    body = _find_body_of_sketch(document, sketch)
    arguments = operation["arguments"]
    suffix = uuid.uuid4().hex[:8]
    feature = _new_body_feature(document, body, "PartDesign::Revolution", f"AgenticRevolution_{suffix}")
    feature.Profile = sketch
    feature.ReferenceAxis = (sketch, [REVOLUTION_AXES[arguments.get("axis", "v_axis")]])
    feature.Angle = float(arguments["angle_deg"])
    feature.Label = arguments.get("label") or "Agentic Revolution"
    _attach_agent_metadata(feature, f"agentic-revolution-{suffix}", plan_id)
    return feature


def _create_hole(document: Any, operation: dict[str, Any], plan_id: str) -> tuple[Any, Any]:
    import FreeCAD  # type: ignore

    body = _find_target(document, str(operation.get("target") or ""))
    if str(getattr(body, "TypeId", "")) != "PartDesign::Body":
        raise ValueError(f"Hole target must be a PartDesign body: {body.Label}")
    arguments = operation["arguments"]
    plane = str(arguments["plane"])
    sketch = _create_sketch(
        document,
        {"plane": plane, "label": "Agentic Hole Sketch", "body_target": str(operation["target"])},
        plan_id,
    )
    offset = float(arguments.get("plane_offset_mm") or 0.0)
    if offset:
        normal = SKETCH_PLANE_NORMALS[plane]
        placement = sketch.Placement
        placement.Base = placement.Base + FreeCAD.Vector(*(component * offset for component in normal))
        sketch.Placement = placement
    radius = float(arguments["diameter_mm"]) / 2.0
    for position in arguments["positions"]:
        _add_one_geometry(sketch, {"kind": "circle", "center": position, "radius_mm": radius})
    pocket_operation = {
        "type": "partdesign.pocket",
        "target": sketch.AgenticStableId,
        "arguments": {
            "through_all": bool(arguments.get("through_all")),
            "length_mm": arguments.get("depth_mm"),
            "reversed": arguments.get("reversed"),
            "label": arguments.get("label") or "Agentic Hole",
        },
    }
    feature = _create_pocket(document, pocket_operation, plan_id)
    return feature, sketch


def _body_target(document: Any, operation: dict[str, Any]) -> Any:
    body = _find_target(document, str(operation.get("target") or ""))
    if str(getattr(body, "TypeId", "")) != "PartDesign::Body":
        raise ValueError(f"Target must be a PartDesign body: {body.Label}")
    return body


def _body_tip(body: Any) -> Any:
    tip = getattr(body, "Tip", None)
    if tip is None:
        raise ValueError(f"Body has no features to modify: {body.Label}")
    return tip


def _origin_feature(body: Any, role: str) -> Any:
    origin = getattr(body, "Origin", None)
    for feature in getattr(origin, "OriginFeatures", None) or []:
        if str(getattr(feature, "Role", "")) == role:
            return feature
    raise ValueError(f"Body origin feature not found: {role}")


def _tip_edge_names(tip: Any) -> list[str]:
    edges = getattr(getattr(tip, "Shape", None), "Edges", None) or []
    if not edges:
        raise ValueError(f"Tip feature has no edges to dress up: {tip.Label}")
    return [f"Edge{index}" for index in range(1, len(edges) + 1)]


def _create_dressup(document: Any, operation: dict[str, Any], plan_id: str, *, kind: str) -> Any:
    body = _body_target(document, operation)
    tip = _body_tip(body)
    arguments = operation["arguments"]
    suffix = uuid.uuid4().hex[:8]
    type_id = "PartDesign::Fillet" if kind == "fillet" else "PartDesign::Chamfer"
    feature = _new_body_feature(document, body, type_id, f"Agentic{kind.capitalize()}_{suffix}")
    feature.Base = (tip, _tip_edge_names(tip))
    if kind == "fillet":
        feature.Radius = float(arguments["radius_mm"])
    else:
        feature.Size = float(arguments["size_mm"])
    feature.Label = arguments.get("label") or f"Agentic {kind.capitalize()}"
    _attach_agent_metadata(feature, f"agentic-{kind}-{suffix}", plan_id)
    return feature


def _create_mirror(document: Any, operation: dict[str, Any], plan_id: str) -> Any:
    body = _body_target(document, operation)
    tip = _body_tip(body)
    arguments = operation["arguments"]
    suffix = uuid.uuid4().hex[:8]
    feature = _new_body_feature(document, body, "PartDesign::Mirrored", f"AgenticMirror_{suffix}")
    feature.Originals = [tip]
    feature.MirrorPlane = (_origin_feature(body, f"{arguments['plane']}_Plane"), [""])
    feature.Label = arguments.get("label") or "Agentic Mirror"
    # FreeCAD does not advance the body tip for transformed features the way it
    # does for sketch-based/dressup features; without this the body keeps the
    # pre-mirror shape after save/reload.
    body.Tip = feature
    _attach_agent_metadata(feature, f"agentic-mirror-{suffix}", plan_id)
    return feature


def _create_linear_pattern(document: Any, operation: dict[str, Any], plan_id: str) -> Any:
    body = _body_target(document, operation)
    tip = _body_tip(body)
    arguments = operation["arguments"]
    suffix = uuid.uuid4().hex[:8]
    feature = _new_body_feature(document, body, "PartDesign::LinearPattern", f"AgenticPattern_{suffix}")
    feature.Originals = [tip]
    feature.Direction = (_origin_feature(body, PATTERN_AXES[arguments["axis"]]), [""])
    feature.Length = float(arguments["length_mm"])
    feature.Occurrences = int(arguments["occurrences"])
    feature.Label = arguments.get("label") or "Agentic Linear Pattern"
    # See _create_mirror: transformed features do not advance the body tip.
    body.Tip = feature
    _attach_agent_metadata(feature, f"agentic-pattern-{suffix}", plan_id)
    return feature


def _create_techdraw_page(document: Any, arguments: dict[str, Any], plan_id: str) -> Any:
    _ensure_techdraw_registered()
    suffix = uuid.uuid4().hex[:8]
    page = document.addObject("TechDraw::DrawPage", f"AgenticPage_{suffix}")
    page.Label = arguments.get("label") or "Agentic Drawing Page"
    template = document.addObject("TechDraw::DrawSVGTemplate", f"AgenticTemplate_{suffix}")
    template.Label = f"{page.Label} Template"
    template.Template = _techdraw_template_path(arguments)
    page.Template = template
    if "scale" in arguments:
        page.Scale = float(arguments["scale"])
    _attach_agent_metadata(page, f"agentic-techdraw-page-{suffix}", plan_id)
    _attach_agent_metadata(template, f"agentic-techdraw-template-{suffix}", plan_id)
    return page


def _techdraw_template_path(arguments: dict[str, Any]) -> str:
    import FreeCAD  # type: ignore

    explicit_path = arguments.get("template_path")
    if explicit_path:
        template_path = str(explicit_path)
    else:
        resource_dir_getter = getattr(FreeCAD, "getResourceDir", None)
        resource_dir = str(resource_dir_getter() if callable(resource_dir_getter) else "")
        if not resource_dir:
            return "Default_Template_A4_Landscape.svg"
        template_path = os.path.join(
            resource_dir,
            "Mod",
            "TechDraw",
            "Templates",
            "Default_Template_A4_Landscape.svg",
        )
    if not template_path.endswith(".svg"):
        raise ValueError("TechDraw template_path must point to an SVG template")
    if os.path.isabs(template_path) and not os.path.exists(template_path):
        raise FileNotFoundError(f"TechDraw template was not found: {template_path}")
    return template_path


def _techdraw_page_target(document: Any, stable_id: str) -> Any:
    page = _find_target(document, stable_id)
    if str(getattr(page, "TypeId", "")) != "TechDraw::DrawPage":
        raise ValueError(f"Target is not a TechDraw page: {page.Label}")
    return page


def _techdraw_view_target(document: Any, stable_id: str) -> Any:
    view = _find_target(document, stable_id)
    if str(getattr(view, "TypeId", "")) != "TechDraw::DrawViewPart":
        raise ValueError(f"Target is not a TechDraw projected view: {view.Label}")
    return view


def _techdraw_direction(value: Any) -> Any:
    import FreeCAD  # type: ignore

    if isinstance(value, str):
        components = TECHDRAW_DIRECTIONS[value]
    else:
        components = value
    return FreeCAD.Vector(float(components[0]), float(components[1]), float(components[2]))


def _create_techdraw_view(document: Any, operation: dict[str, Any], plan_id: str) -> Any:
    _ensure_techdraw_registered()
    page = _techdraw_page_target(document, str(operation.get("target") or ""))
    arguments = operation["arguments"]
    source = _find_target(document, str(arguments["source_target"]))
    if getattr(source, "Shape", None) is None or source.Shape.isNull():
        raise ValueError(f"TechDraw view source has no measurable shape: {source.Label}")
    suffix = uuid.uuid4().hex[:8]
    view = document.addObject("TechDraw::DrawViewPart", f"AgenticView_{suffix}")
    view.Label = arguments.get("label") or "Agentic Drawing View"
    page.addView(view)
    view.Source = [source]
    view.Direction = _techdraw_direction(arguments.get("direction", "front"))
    view.X = float(arguments.get("x_mm", 50.0))
    view.Y = float(arguments.get("y_mm", 80.0))
    if "scale" in arguments:
        view.Scale = float(arguments["scale"])
    _attach_agent_metadata(view, f"agentic-techdraw-view-{suffix}", plan_id)
    return view


def _find_page_for_techdraw_view(document: Any, view: Any) -> Any:
    for candidate in document.Objects:
        if str(getattr(candidate, "TypeId", "")) != "TechDraw::DrawPage":
            continue
        if view in (getattr(candidate, "Views", None) or []):
            return candidate
    raise ValueError(f"TechDraw view is not on a page: {view.Label}")


def _create_techdraw_dimension(document: Any, operation: dict[str, Any], plan_id: str) -> Any:
    _ensure_techdraw_registered()
    view = _techdraw_view_target(document, str(operation.get("target") or ""))
    arguments = operation["arguments"]
    page_target = arguments.get("page_target")
    page = _techdraw_page_target(document, str(page_target)) if page_target else _find_page_for_techdraw_view(document, view)
    suffix = uuid.uuid4().hex[:8]
    dimension = document.addObject("TechDraw::DrawViewDimension", f"AgenticDimension_{suffix}")
    dimension.Label = arguments.get("label") or "Agentic Drawing Dimension"
    page.addView(dimension)
    dimension.Type = arguments.get("dimension_type", "Distance")
    if "measure_type" in arguments:
        dimension.MeasureType = arguments["measure_type"]
    dimension.References2D = [(view, arguments.get("edge_name", "Edge1"))]
    _attach_agent_metadata(dimension, f"agentic-techdraw-dimension-{suffix}", plan_id)
    return dimension


def _spreadsheet_cell(column_index: int, row_index: int) -> str:
    column = ""
    value = column_index
    while value:
        value, remainder = divmod(value - 1, 26)
        column = chr(65 + remainder) + column
    return f"{column}{row_index}"


def _set_spreadsheet_cell(sheet: Any, column_index: int, row_index: int, value: Any) -> None:
    cell = _spreadsheet_cell(column_index, row_index)
    setter = getattr(sheet, "set", None)
    if callable(setter):
        setter(cell, str(value))
        return
    cells = getattr(sheet, "Cells", None)
    if cells is None:
        cells = {}
        setattr(sheet, "Cells", cells)
    cells[cell] = str(value)


def _create_techdraw_bom_table(document: Any, operation: dict[str, Any], plan_id: str) -> tuple[Any, Any]:
    _ensure_techdraw_registered()
    _ensure_spreadsheet_registered()
    page = _techdraw_page_target(document, str(operation.get("target") or ""))
    arguments = operation["arguments"]
    suffix = uuid.uuid4().hex[:8]
    sheet = document.addObject("Spreadsheet::Sheet", f"AgenticBOM_{suffix}")
    sheet.Label = arguments.get("label") or "Agentic BOM"
    headers = ["Item", "Part No", "Description", "Qty"]
    for column_index, header in enumerate(headers, start=1):
        _set_spreadsheet_cell(sheet, column_index, 1, header)
    for row_index, item in enumerate(arguments["items"], start=2):
        _set_spreadsheet_cell(sheet, 1, row_index, item["item_no"])
        _set_spreadsheet_cell(sheet, 2, row_index, item.get("part_no", ""))
        _set_spreadsheet_cell(sheet, 3, row_index, item.get("description", ""))
        _set_spreadsheet_cell(sheet, 4, row_index, item["quantity"])
    recompute = getattr(sheet, "recompute", None)
    if callable(recompute):
        recompute()
    view = document.addObject("TechDraw::DrawViewSpreadsheet", f"AgenticBOMView_{suffix}")
    view.Label = arguments.get("view_label") or f"{sheet.Label} View"
    page.addView(view)
    view.Source = sheet
    view.X = float(arguments.get("x_mm", 180.0))
    view.Y = float(arguments.get("y_mm", 40.0))
    _attach_agent_metadata(sheet, f"agentic-techdraw-bom-source-{suffix}", plan_id)
    _attach_agent_metadata(view, f"agentic-techdraw-bom-table-{suffix}", plan_id)
    return view, sheet


def _create_techdraw_balloon(document: Any, operation: dict[str, Any], plan_id: str) -> Any:
    _ensure_techdraw_registered()
    view = _techdraw_view_target(document, str(operation.get("target") or ""))
    arguments = operation["arguments"]
    page_target = arguments.get("page_target")
    page = _techdraw_page_target(document, str(page_target)) if page_target else _find_page_for_techdraw_view(document, view)
    suffix = uuid.uuid4().hex[:8]
    balloon = document.addObject("TechDraw::DrawViewBalloon", f"AgenticBalloon_{suffix}")
    balloon.Label = arguments.get("label") or f"Balloon {arguments['item_no']}"
    page.addView(balloon)
    balloon.SourceView = view
    balloon.Text = str(arguments["item_no"])
    balloon.OriginX = float(arguments.get("origin_x_mm", arguments.get("x_mm", 0.0)))
    balloon.OriginY = float(arguments.get("origin_y_mm", arguments.get("y_mm", 0.0)))
    balloon.X = float(arguments.get("x_mm", 70.0))
    balloon.Y = float(arguments.get("y_mm", 110.0))
    if "bubble_shape" in arguments:
        balloon.BubbleShape = arguments["bubble_shape"]
    if "end_type" in arguments:
        balloon.EndType = arguments["end_type"]
    _attach_agent_metadata(balloon, f"agentic-techdraw-balloon-{suffix}", plan_id)
    return balloon


def _create_techdraw_section_view(document: Any, operation: dict[str, Any], plan_id: str) -> Any:
    _ensure_techdraw_registered()
    base_view = _techdraw_view_target(document, str(operation.get("target") or ""))
    arguments = operation["arguments"]
    page_target = arguments.get("page_target")
    page = _techdraw_page_target(document, str(page_target)) if page_target else _find_page_for_techdraw_view(document, base_view)
    source = getattr(base_view, "Source", None) or []
    if not source:
        raise ValueError(f"Section base view has no source: {base_view.Label}")
    suffix = uuid.uuid4().hex[:8]
    section = document.addObject("TechDraw::DrawViewSection", f"AgenticSection_{suffix}")
    section.Label = arguments.get("label") or "Agentic Section View"
    page.addView(section)
    section.Source = list(source)
    section.BaseView = base_view
    section.Direction = _techdraw_direction(arguments.get("direction", "top"))
    section.SectionNormal = _techdraw_direction(arguments.get("section_normal", arguments.get("direction", "top")))
    section.SectionOrigin = tuple(float(value) for value in arguments["section_origin_mm"])
    section.X = float(arguments.get("x_mm", 50.0))
    section.Y = float(arguments.get("y_mm", 180.0))
    if "scale" in arguments:
        section.Scale = float(arguments["scale"])
    _attach_agent_metadata(section, f"agentic-techdraw-section-{suffix}", plan_id)
    return section


def _create_techdraw_detail_view(document: Any, operation: dict[str, Any], plan_id: str) -> Any:
    _ensure_techdraw_registered()
    base_view = _techdraw_view_target(document, str(operation.get("target") or ""))
    arguments = operation["arguments"]
    page_target = arguments.get("page_target")
    page = _techdraw_page_target(document, str(page_target)) if page_target else _find_page_for_techdraw_view(document, base_view)
    suffix = uuid.uuid4().hex[:8]
    detail = document.addObject("TechDraw::DrawViewDetail", f"AgenticDetail_{suffix}")
    detail.Label = arguments.get("label") or "Agentic Detail View"
    detail.BaseView = base_view
    detail.Direction = getattr(base_view, "Direction", _techdraw_direction("front"))
    if hasattr(base_view, "XDirection"):
        detail.XDirection = base_view.XDirection
    page.addView(detail)
    detail.X = float(arguments.get("x_mm", 150.0))
    detail.Y = float(arguments.get("y_mm", 180.0))
    if "anchor_x_mm" in arguments:
        detail.AnchorPoint = (float(arguments["anchor_x_mm"]), float(arguments.get("anchor_y_mm", 0.0)), 0.0)
    if "radius_mm" in arguments:
        detail.Radius = float(arguments["radius_mm"])
    if "scale" in arguments:
        detail.Scale = float(arguments["scale"])
    _attach_agent_metadata(detail, f"agentic-techdraw-detail-{suffix}", plan_id)
    return detail


def _set_pmi_text(annotation: Any, text: str) -> None:
    try:
        annotation.Text = [text]
    except Exception:
        annotation.Text = text


def _pmi_text(annotation: Any) -> str:
    text = getattr(annotation, "Text", "")
    if isinstance(text, (list, tuple)):
        return "\n".join(str(item) for item in text)
    return str(text)


def _create_techdraw_pmi_note(document: Any, operation: dict[str, Any], plan_id: str) -> Any:
    _ensure_techdraw_registered()
    page = _techdraw_page_target(document, str(operation.get("target") or ""))
    arguments = operation["arguments"]
    suffix = uuid.uuid4().hex[:8]
    annotation = document.addObject("TechDraw::DrawViewAnnotation", f"AgenticPMI_{suffix}")
    annotation.Label = arguments.get("label") or "Agentic PMI Note"
    page.addView(annotation)
    _set_pmi_text(annotation, str(arguments["text"]))
    annotation.X = float(arguments.get("x_mm", 120.0))
    annotation.Y = float(arguments.get("y_mm", 40.0))
    if "font_size_mm" in arguments:
        try:
            annotation.TextSize = float(arguments["font_size_mm"])
        except Exception:
            pass
    if "source_view" in arguments:
        try:
            annotation.SourceView = _techdraw_view_target(document, str(arguments["source_view"]))
        except Exception:
            pass
    _attach_agent_metadata(annotation, str(arguments.get("stable_id") or f"agentic-techdraw-pmi-{suffix}"), plan_id)
    return annotation


def _sketch_payload(obj: Any) -> dict[str, Any]:
    geometry = getattr(obj, "Geometry", None) or []
    constraints = getattr(obj, "Constraints", None) or []
    solver_status: int | None = None
    solve = getattr(obj, "solve", None)
    if callable(solve):
        solver_status = int(solve())
    return {
        "geometry_count": len(geometry),
        "constraint_count": len(constraints),
        "solver_status": solver_status,
    }


def _is_sketch(obj: Any) -> bool:
    return str(getattr(obj, "TypeId", "")).startswith("Sketcher::")


def _is_body(obj: Any) -> bool:
    return str(getattr(obj, "TypeId", "")) == "PartDesign::Body"


def _is_techdraw(obj: Any) -> bool:
    return str(getattr(obj, "TypeId", "")).startswith("TechDraw::")


def _is_spreadsheet(obj: Any) -> bool:
    return str(getattr(obj, "TypeId", "")) == "Spreadsheet::Sheet"


def _techdraw_payload(obj: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"type_id": str(getattr(obj, "TypeId", ""))}
    if payload["type_id"] == "TechDraw::DrawPage":
        payload["view_count"] = len(getattr(obj, "Views", None) or [])
    elif payload["type_id"] == "TechDraw::DrawViewPart":
        payload["source_count"] = len(getattr(obj, "Source", None) or [])
        payload["state"] = [str(item) for item in (getattr(obj, "State", None) or [])]
    elif payload["type_id"] == "TechDraw::DrawViewDimension":
        payload["dimension_type"] = str(getattr(obj, "Type", ""))
        payload["reference_count"] = len(getattr(obj, "References2D", None) or [])
        payload["state"] = [str(item) for item in (getattr(obj, "State", None) or [])]
    elif payload["type_id"] == "TechDraw::DrawViewSpreadsheet":
        payload["has_source"] = getattr(obj, "Source", None) is not None
    elif payload["type_id"] == "TechDraw::DrawViewBalloon":
        payload["text"] = str(getattr(obj, "Text", ""))
        payload["has_source_view"] = getattr(obj, "SourceView", None) is not None
    elif payload["type_id"] == "TechDraw::DrawViewSection":
        payload["has_base_view"] = getattr(obj, "BaseView", None) is not None
        payload["source_count"] = len(getattr(obj, "Source", None) or [])
        payload["state"] = [str(item) for item in (getattr(obj, "State", None) or [])]
    elif payload["type_id"] == "TechDraw::DrawViewDetail":
        payload["has_base_view"] = getattr(obj, "BaseView", None) is not None
        payload["state"] = [str(item) for item in (getattr(obj, "State", None) or [])]
    elif payload["type_id"] == "TechDraw::DrawViewAnnotation":
        payload["text"] = _pmi_text(obj)
        payload["has_text"] = bool(payload["text"].strip())
    return payload


def _verify_objects(objects: list[Any]) -> list[dict[str, Any]]:
    evidence = []
    for obj in objects:
        if _is_body(obj):
            evidence.append({"object": _object_payload(obj), "checks": {"body_created": True}})
            continue
        if _is_techdraw(obj):
            evidence.append({"object": _object_payload(obj), "checks": {"techdraw_object_created": True}, "techdraw": _techdraw_payload(obj)})
            continue
        if _is_spreadsheet(obj):
            cells = getattr(obj, "Cells", None) or {}
            evidence.append({"object": _object_payload(obj), "checks": {"spreadsheet_created": True}, "spreadsheet": {"cell_count": len(cells)}})
            continue
        if _is_sketch(obj):
            payload = _sketch_payload(obj)
            if payload["solver_status"] not in (None, 0):
                raise RuntimeError(f"Sketch constraints failed to solve: {obj.Label}")
            evidence.append(
                {
                    "object": _object_payload(obj),
                    "checks": {"sketch_solved": payload["solver_status"] in (None, 0)},
                    "sketch": payload,
                }
            )
            continue
        shape = _shape_payload(obj)
        if shape is None or not shape["valid"] or shape["volume_mm3"] <= 0:
            raise RuntimeError(f"FreeCAD produced an invalid shape: {obj.Label}")
        evidence.append({"object": _object_payload(obj), "checks": {"shape_valid": True, "positive_volume": True}})
    return evidence


def execute_plan(plan: dict[str, Any], *, approved: bool = False) -> dict[str, Any]:
    """Execute one plan atomically and return measured FreeCAD evidence."""
    import FreeCAD  # type: ignore
    operations = validate_plan(plan)
    if any(operation["type"] in MUTATING_OPERATIONS for operation in operations) and not approved:
        raise PermissionError("Mutating FreeCAD plans require explicit user approval")
    document = FreeCAD.ActiveDocument or FreeCAD.newDocument("AgenticCAD")
    if document.UndoMode == 0:
        document.UndoMode = 1

    if len(operations) == 1 and operations[0]["type"] == "document.inspect":
        context = get_document_context()
        return {"status": "succeeded", "summary": f"{len(context['objects'])} objects", "context": context, "evidence": []}
    if len(operations) == 1 and operations[0]["type"] == "document.undo":
        document.undo()
        document.recompute()
        _safe_update_gui()
        return {"status": "succeeded", "summary": "Previous transaction undone", "context": get_document_context(), "evidence": []}

    changed_objects = []
    changes = []
    plan_aliases: dict[str, str] = {}
    document.openTransaction(f"Agentic {plan['plan_id']}")
    try:
        for operation in operations:
            operation = _resolve_operation_aliases(operation, plan_aliases)
            operation_type = operation["type"]
            if operation_type == "primitive.create_box":
                obj = _create_box(document, operation["arguments"], plan["plan_id"])
                changed_objects.append(obj)
                changes.append({"stable_id": obj.AgenticStableId, "created": "box"})
            elif operation_type == "primitive.create_cylinder":
                obj = _create_cylinder(document, operation["arguments"], plan["plan_id"])
                changed_objects.append(obj)
                changes.append({"stable_id": obj.AgenticStableId, "created": "cylinder"})
            elif operation_type == "bim.create_element":
                obj = _create_bim_element(document, operation["arguments"], plan["plan_id"])
                changed_objects.append(obj)
                changes.append({"stable_id": obj.AgenticStableId, "created": "bim_element", "ifc_type": obj.IfcType})
            elif operation_type == "object.update_parameters":
                obj, changed = _update_parameters(document, operation)
                changed_objects.append(obj)
                changes.append({"stable_id": operation["target"], "parameters": changed})
            elif operation_type == "object.translate":
                obj, translation = _translate_object(document, operation)
                changed_objects.append(obj)
                changes.append({"stable_id": operation["target"], "translation_mm": translation})
            elif operation_type == "sketch.create":
                obj = _create_sketch(document, operation["arguments"], plan["plan_id"])
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "sketch",
                        "plane": operation["arguments"]["plane"],
                    }
                )
            elif operation_type == "sketch.add_geometry":
                obj, indices = _add_sketch_geometry(document, operation)
                changed_objects.append(obj)
                changes.append({"stable_id": operation["target"], "geometry_indices": indices})
            elif operation_type == "sketch.add_constraint":
                obj, constraint_count = _add_sketch_constraints(document, operation)
                changed_objects.append(obj)
                changes.append({"stable_id": operation["target"], "constraints_added": constraint_count})
            elif operation_type == "partdesign.create_body":
                obj = _create_partdesign_body(document, operation["arguments"], plan["plan_id"])
                changed_objects.append(obj)
                changes.append({"stable_id": obj.AgenticStableId, "created": "body"})
            elif operation_type == "partdesign.pad":
                obj = _create_pad(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "pad",
                        "profile": operation["target"],
                        "length_mm": float(operation["arguments"]["length_mm"]),
                    }
                )
            elif operation_type == "partdesign.pocket":
                obj = _create_pocket(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changes.append({"stable_id": obj.AgenticStableId, "created": "pocket", "profile": operation["target"]})
            elif operation_type == "partdesign.revolution":
                obj = _create_revolution(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "revolution",
                        "profile": operation["target"],
                        "angle_deg": float(operation["arguments"]["angle_deg"]),
                    }
                )
            elif operation_type in {"partdesign.fillet", "partdesign.chamfer"}:
                kind = operation_type.rsplit(".", 1)[1]
                obj = _create_dressup(document, operation, plan["plan_id"], kind=kind)
                changed_objects.append(obj)
                changes.append({"stable_id": obj.AgenticStableId, "created": kind, "body": operation["target"]})
            elif operation_type == "partdesign.mirror":
                obj = _create_mirror(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "mirror",
                        "body": operation["target"],
                        "plane": operation["arguments"]["plane"],
                    }
                )
            elif operation_type == "partdesign.linear_pattern":
                obj = _create_linear_pattern(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "linear_pattern",
                        "body": operation["target"],
                        "occurrences": int(operation["arguments"]["occurrences"]),
                    }
                )
            elif operation_type == "partdesign.hole":
                obj, hole_sketch = _create_hole(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changed_objects.append(hole_sketch)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "hole",
                        "body": operation["target"],
                        "hole_count": len(operation["arguments"]["positions"]),
                        "diameter_mm": float(operation["arguments"]["diameter_mm"]),
                    }
                )
            elif operation_type == "techdraw.create_page":
                obj = _create_techdraw_page(document, operation["arguments"], plan["plan_id"])
                changed_objects.append(obj)
                changes.append({"stable_id": obj.AgenticStableId, "created": "techdraw_page"})
            elif operation_type == "techdraw.add_view":
                obj = _create_techdraw_view(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "techdraw_view",
                        "page": operation["target"],
                        "source": operation["arguments"]["source_target"],
                    }
                )
            elif operation_type == "techdraw.add_dimension":
                obj = _create_techdraw_dimension(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "techdraw_dimension",
                        "view": operation["target"],
                        "dimension_type": operation["arguments"].get("dimension_type", "Distance"),
                        "edge_name": operation["arguments"].get("edge_name", "Edge1"),
                    }
                )
            elif operation_type == "techdraw.add_bom_table":
                obj, sheet = _create_techdraw_bom_table(document, operation, plan["plan_id"])
                changed_objects.append(sheet)
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "source_stable_id": sheet.AgenticStableId,
                        "created": "techdraw_bom_table",
                        "page": operation["target"],
                        "row_count": len(operation["arguments"]["items"]),
                    }
                )
            elif operation_type == "techdraw.add_balloon":
                obj = _create_techdraw_balloon(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "techdraw_balloon",
                        "view": operation["target"],
                        "item_no": str(operation["arguments"]["item_no"]),
                    }
                )
            elif operation_type == "techdraw.add_section_view":
                obj = _create_techdraw_section_view(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "techdraw_section_view",
                        "base_view": operation["target"],
                    }
                )
            elif operation_type == "techdraw.add_detail_view":
                obj = _create_techdraw_detail_view(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "techdraw_detail_view",
                        "base_view": operation["target"],
                    }
                )
            elif operation_type == "techdraw.add_pmi_note":
                obj = _create_techdraw_pmi_note(document, operation, plan["plan_id"])
                changed_objects.append(obj)
                changes.append(
                    {
                        "stable_id": obj.AgenticStableId,
                        "created": "techdraw_pmi_note",
                        "page": operation["target"],
                        "pmi_note_type": operation["arguments"].get("note_type", "tolerance_note"),
                    }
                )
            else:
                raise ValueError(f"Operation cannot be mixed into a mutation plan: {operation_type}")
            alias = operation.get("alias")
            if alias:
                plan_aliases[str(alias)] = str(obj.AgenticStableId)
        document.recompute()
        evidence = _verify_objects(changed_objects)
        document.commitTransaction()
    except Exception:
        document.abortTransaction()
        document.recompute()
        raise

    _safe_update_gui()
    return {
        "status": "succeeded",
        "summary": f"Executed {len(operations)} typed operation(s)",
        "changed": changes,
        "evidence": evidence,
        "context": get_document_context(),
    }


def _safe_update_gui() -> None:
    """Refresh FreeCAD GUI without touching camera/view C++ methods.

    FreeCADCmd does not need this. In the macOS GUI, direct activeView camera
    calls can be brittle when the Start page and a 3D document coexist, so the
    plugin keeps mutation correctness separate from optional visual framing.
    """
    try:
        import FreeCADGui as Gui  # type: ignore

        update = getattr(Gui, "updateGui", None)
        if callable(update):
            update()
    except Exception:
        return


def _validate_translation(value: Any) -> None:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("translation_mm must be a 3-element list")
    for component in value:
        if not isinstance(component, (int, float)):
            raise ValueError("translation_mm components must be numeric")
        if not math.isfinite(float(component)) or abs(float(component)) > MAX_TRANSLATION_MM:
            raise ValueError("translation_mm component is out of range")
    if not any(float(component) != 0.0 for component in value):
        raise ValueError("translation_mm must not be a zero vector")


def _validate_operation_alias(
    operation: dict[str, Any],
    operation_type: str,
    arguments: dict[str, Any],
    declared_aliases: set[str],
) -> None:
    """Statically validate in-plan alias declarations and references.

    Aliases let a later operation target an object created earlier in the same
    plan (`"target": "@alias:plate_sketch"`). References must point to an
    alias declared by an earlier creation operation, so broken plans fail
    before any FreeCAD transaction opens.
    """
    for reference in (
        operation.get("target"),
        arguments.get("body_target"),
        arguments.get("source_target"),
        arguments.get("page_target"),
    ):
        if isinstance(reference, str) and reference.startswith(ALIAS_REF_PREFIX):
            name = reference[len(ALIAS_REF_PREFIX) :]
            if name not in declared_aliases:
                raise ValueError(f"Alias is referenced before it is created: {name}")
    alias = operation.get("alias")
    if alias is None:
        return
    if not isinstance(alias, str) or not alias.strip():
        raise ValueError("Operation alias must be a non-empty string")
    if operation_type not in CREATION_OPERATIONS:
        raise ValueError(f"Only creation operations may declare an alias: {operation_type}")
    if alias in declared_aliases:
        raise ValueError(f"Duplicate operation alias: {alias}")
    declared_aliases.add(alias)


def _resolve_operation_aliases(operation: dict[str, Any], plan_aliases: dict[str, str]) -> dict[str, Any]:
    resolved = dict(operation)
    resolved["arguments"] = dict(operation.get("arguments") or {})

    def _resolve(value: Any) -> Any:
        if isinstance(value, str) and value.startswith(ALIAS_REF_PREFIX):
            name = value[len(ALIAS_REF_PREFIX) :]
            if name not in plan_aliases:
                raise ValueError(f"Alias did not resolve to a created object: {name}")
            return plan_aliases[name]
        return value

    if "target" in resolved:
        resolved["target"] = _resolve(resolved["target"])
    if "body_target" in resolved["arguments"]:
        resolved["arguments"]["body_target"] = _resolve(resolved["arguments"]["body_target"])
    if "source_target" in resolved["arguments"]:
        resolved["arguments"]["source_target"] = _resolve(resolved["arguments"]["source_target"])
    if "source_view" in resolved["arguments"]:
        resolved["arguments"]["source_view"] = _resolve(resolved["arguments"]["source_view"])
    if "page_target" in resolved["arguments"]:
        resolved["arguments"]["page_target"] = _resolve(resolved["arguments"]["page_target"])
    return resolved


def _validate_sketch_point(value: Any, field: str) -> None:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{field} must be a 2-element [x, y] list")
    for component in value:
        if not isinstance(component, (int, float)) or isinstance(component, bool):
            raise ValueError(f"{field} components must be numeric")
        if not math.isfinite(float(component)) or abs(float(component)) > MAX_SKETCH_COORDINATE_MM:
            raise ValueError(f"{field} component is out of range")


def _validate_positive_mm(spec: dict[str, Any], key: str) -> None:
    value = spec.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
        raise ValueError(f"{key} must be a positive finite number")


def _validate_geometry_index(value: Any, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a non-negative geometry index")


def _validate_point_ref(value: Any, field: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object with index and point")
    _validate_geometry_index(value.get("index"), f"{field}.index")
    if value.get("point") not in SKETCH_POINT_CODES:
        raise ValueError(f"{field}.point must be one of {sorted(SKETCH_POINT_CODES)}")


def _validate_sketch_geometry_arguments(arguments: dict[str, Any]) -> None:
    geometry = arguments.get("geometry")
    if not isinstance(geometry, list) or not geometry:
        raise ValueError("sketch.add_geometry requires a non-empty geometry list")
    for spec in geometry:
        if not isinstance(spec, dict):
            raise ValueError("Geometry entries must be objects")
        kind = spec.get("kind")
        if kind not in SKETCH_GEOMETRY_KINDS:
            raise ValueError(f"Unsupported sketch geometry kind: {kind}")
        if kind == "line":
            _validate_sketch_point(spec.get("start"), "line.start")
            _validate_sketch_point(spec.get("end"), "line.end")
            if [float(v) for v in spec["start"]] == [float(v) for v in spec["end"]]:
                raise ValueError("line start and end must differ")
        elif kind == "circle":
            _validate_sketch_point(spec.get("center"), "circle.center")
            _validate_positive_mm(spec, "radius_mm")
        elif kind == "arc":
            _validate_sketch_point(spec.get("center"), "arc.center")
            _validate_positive_mm(spec, "radius_mm")
            for key in ("start_angle_deg", "end_angle_deg"):
                value = spec.get(key)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
                    raise ValueError(f"{key} must be a finite number")
            if float(spec["start_angle_deg"]) == float(spec["end_angle_deg"]):
                raise ValueError("arc start and end angles must differ")
        elif kind == "rectangle":
            _validate_sketch_point(spec.get("corner"), "rectangle.corner")
            _validate_positive_mm(spec, "width_mm")
            _validate_positive_mm(spec, "height_mm")


def _validate_sketch_constraint_arguments(arguments: dict[str, Any]) -> None:
    constraints = arguments.get("constraints")
    if not isinstance(constraints, list) or not constraints:
        raise ValueError("sketch.add_constraint requires a non-empty constraints list")
    for spec in constraints:
        if not isinstance(spec, dict):
            raise ValueError("Constraint entries must be objects")
        kind = spec.get("kind")
        if kind not in SKETCH_CONSTRAINT_KINDS:
            raise ValueError(f"Unsupported sketch constraint kind: {kind}")
        if kind == "coincident":
            _validate_point_ref(spec.get("first"), "coincident.first")
            _validate_point_ref(spec.get("second"), "coincident.second")
        elif kind in {"horizontal", "vertical"}:
            _validate_geometry_index(spec.get("index"), f"{kind}.index")
        elif kind == "distance":
            if "index" in spec:
                _validate_geometry_index(spec.get("index"), "distance.index")
            else:
                _validate_point_ref(spec.get("first"), "distance.first")
                _validate_point_ref(spec.get("second"), "distance.second")
            _validate_positive_mm(spec, "value_mm")
        elif kind in {"distance_x", "distance_y"}:
            _validate_point_ref(spec.get("first"), f"{kind}.first")
            _validate_point_ref(spec.get("second"), f"{kind}.second")
            value = spec.get("value_mm")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value == 0:
                raise ValueError("value_mm must be a non-zero finite number")
        elif kind in {"radius", "diameter"}:
            _validate_geometry_index(spec.get("index"), f"{kind}.index")
            _validate_positive_mm(spec, "value_mm")
        elif kind == "angle":
            _validate_geometry_index(spec.get("first_index"), "angle.first_index")
            _validate_geometry_index(spec.get("second_index"), "angle.second_index")
            value = spec.get("value_deg")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
                raise ValueError("value_deg must be a finite number")
            if not 0.0 < abs(float(value)) < 360.0:
                raise ValueError("value_deg must be between 0 and 360 degrees exclusive")
        elif kind == "symmetric":
            _validate_point_ref(spec.get("first"), "symmetric.first")
            _validate_point_ref(spec.get("second"), "symmetric.second")
            _validate_geometry_index(spec.get("reference_index"), "symmetric.reference_index")


def _validate_partdesign_arguments(operation_type: str, arguments: dict[str, Any]) -> None:
    if operation_type == "partdesign.pad":
        _validate_positive_mm(arguments, "length_mm")
    elif operation_type == "partdesign.pocket":
        if not arguments.get("through_all"):
            _validate_positive_mm(arguments, "length_mm")
    elif operation_type == "partdesign.revolution":
        angle = arguments.get("angle_deg")
        if not isinstance(angle, (int, float)) or isinstance(angle, bool) or not math.isfinite(float(angle)):
            raise ValueError("angle_deg must be a finite number")
        if not 0.0 < float(angle) <= 360.0:
            raise ValueError("angle_deg must be within (0, 360]")
        axis = arguments.get("axis", "v_axis")
        if axis not in REVOLUTION_AXES:
            raise ValueError(f"axis must be one of {sorted(REVOLUTION_AXES)}")
    elif operation_type == "partdesign.hole":
        if arguments.get("plane") not in SKETCH_PLANES:
            raise ValueError(f"Hole plane must be one of {SKETCH_PLANES}")
        positions = arguments.get("positions")
        if not isinstance(positions, list) or not positions:
            raise ValueError("partdesign.hole requires a non-empty positions list")
        for position in positions:
            _validate_sketch_point(position, "hole.position")
        _validate_positive_mm(arguments, "diameter_mm")
        if not arguments.get("through_all"):
            _validate_positive_mm(arguments, "depth_mm")
    elif operation_type == "partdesign.fillet":
        _validate_positive_mm(arguments, "radius_mm")
    elif operation_type == "partdesign.chamfer":
        _validate_positive_mm(arguments, "size_mm")
    elif operation_type == "partdesign.mirror":
        if arguments.get("plane") not in SKETCH_PLANES:
            raise ValueError(f"Mirror plane must be one of {SKETCH_PLANES}")
    elif operation_type == "partdesign.linear_pattern":
        if arguments.get("axis") not in PATTERN_AXES:
            raise ValueError(f"Pattern axis must be one of {sorted(PATTERN_AXES)}")
        _validate_positive_mm(arguments, "length_mm")
        occurrences = arguments.get("occurrences")
        if not isinstance(occurrences, int) or isinstance(occurrences, bool) or not 2 <= occurrences <= MAX_PATTERN_OCCURRENCES:
            raise ValueError(f"occurrences must be an integer in [2, {MAX_PATTERN_OCCURRENCES}]")


def _validate_techdraw_direction(value: Any) -> None:
    if isinstance(value, str):
        if value not in TECHDRAW_DIRECTIONS:
            raise ValueError(f"TechDraw direction must be one of {sorted(TECHDRAW_DIRECTIONS)}")
        return
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("TechDraw direction must be a named direction or 3-element vector")
    for component in value:
        if not isinstance(component, (int, float)) or isinstance(component, bool) or not math.isfinite(float(component)):
            raise ValueError("TechDraw direction vector components must be finite numbers")
    if not any(float(component) != 0.0 for component in value):
        raise ValueError("TechDraw direction vector must not be zero")


def _validate_optional_positive_number(arguments: dict[str, Any], key: str) -> None:
    if key not in arguments:
        return
    value = arguments.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
        raise ValueError(f"{key} must be a positive finite number")


def _validate_techdraw_bom_items(arguments: dict[str, Any]) -> None:
    items = arguments.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("techdraw.add_bom_table requires a non-empty items list")
    if len(items) > MAX_TECHDRAW_BOM_ROWS:
        raise ValueError(f"techdraw.add_bom_table supports at most {MAX_TECHDRAW_BOM_ROWS} rows")
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("BOM item entries must be objects")
        item_no = item.get("item_no")
        if not isinstance(item_no, (str, int)) or not str(item_no).strip():
            raise ValueError("BOM item_no must be a non-empty string or integer")
        item_key = str(item_no)
        if item_key in seen:
            raise ValueError(f"duplicate BOM item_no: {item_key}")
        seen.add(item_key)
        quantity = item.get("quantity")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError("BOM quantity must be a positive integer")
        for optional_key in ("part_no", "description"):
            if optional_key in item and not isinstance(item[optional_key], str):
                raise ValueError(f"BOM {optional_key} must be a string")


def _validate_techdraw_arguments(operation_type: str, arguments: dict[str, Any]) -> None:
    if operation_type == "techdraw.create_page":
        _validate_optional_positive_number(arguments, "scale")
    elif operation_type == "techdraw.add_view":
        if not isinstance(arguments.get("source_target"), str) or not arguments["source_target"].strip():
            raise ValueError("techdraw.add_view requires source_target")
        _validate_techdraw_direction(arguments.get("direction", "front"))
        _validate_optional_positive_number(arguments, "scale")
    elif operation_type == "techdraw.add_dimension":
        dimension_type = arguments.get("dimension_type", "Distance")
        if dimension_type not in TECHDRAW_DIMENSION_TYPES:
            raise ValueError(f"dimension_type must be one of {list(TECHDRAW_DIMENSION_TYPES)}")
        edge_name = arguments.get("edge_name", "Edge1")
        if not isinstance(edge_name, str) or not edge_name.startswith("Edge"):
            raise ValueError("edge_name must be a TechDraw edge name such as Edge1")
        page_target = arguments.get("page_target")
        if page_target is not None and (not isinstance(page_target, str) or not page_target.strip()):
            raise ValueError("page_target must be a non-empty string when provided")
    elif operation_type == "techdraw.add_bom_table":
        _validate_techdraw_bom_items(arguments)
    elif operation_type == "techdraw.add_balloon":
        item_no = arguments.get("item_no")
        if not isinstance(item_no, (str, int)) or not str(item_no).strip():
            raise ValueError("techdraw.add_balloon requires item_no")
        page_target = arguments.get("page_target")
        if page_target is not None and (not isinstance(page_target, str) or not page_target.strip()):
            raise ValueError("page_target must be a non-empty string when provided")
        for key in ("x_mm", "y_mm", "origin_x_mm", "origin_y_mm"):
            if key in arguments and (not isinstance(arguments[key], (int, float)) or isinstance(arguments[key], bool) or not math.isfinite(float(arguments[key]))):
                raise ValueError(f"{key} must be a finite number")
    elif operation_type == "techdraw.add_section_view":
        origin = arguments.get("section_origin_mm")
        if not isinstance(origin, list) or len(origin) != 3:
            raise ValueError("techdraw.add_section_view requires section_origin_mm as a 3-vector")
        for component in origin:
            if not isinstance(component, (int, float)) or isinstance(component, bool) or not math.isfinite(float(component)):
                raise ValueError("section_origin_mm components must be finite numbers")
        _validate_techdraw_direction(arguments.get("direction", "top"))
        _validate_techdraw_direction(arguments.get("section_normal", arguments.get("direction", "top")))
        _validate_optional_positive_number(arguments, "scale")
        page_target = arguments.get("page_target")
        if page_target is not None and (not isinstance(page_target, str) or not page_target.strip()):
            raise ValueError("page_target must be a non-empty string when provided")
    elif operation_type == "techdraw.add_detail_view":
        _validate_optional_positive_number(arguments, "scale")
        _validate_optional_positive_number(arguments, "radius_mm")
        page_target = arguments.get("page_target")
        if page_target is not None and (not isinstance(page_target, str) or not page_target.strip()):
            raise ValueError("page_target must be a non-empty string when provided")
        for key in ("anchor_x_mm", "anchor_y_mm"):
            if key in arguments and (not isinstance(arguments[key], (int, float)) or isinstance(arguments[key], bool) or not math.isfinite(float(arguments[key]))):
                raise ValueError(f"{key} must be a finite number")
    elif operation_type == "techdraw.add_pmi_note":
        text = arguments.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("techdraw.add_pmi_note requires non-empty text")
        if len(text) > MAX_TECHDRAW_PMI_TEXT_LENGTH:
            raise ValueError(f"techdraw.add_pmi_note text is limited to {MAX_TECHDRAW_PMI_TEXT_LENGTH} characters")
        note_type = arguments.get("note_type", "tolerance_note")
        if note_type not in TECHDRAW_PMI_NOTE_TYPES:
            raise ValueError(f"note_type must be one of {list(TECHDRAW_PMI_NOTE_TYPES)}")
        for key in ("x_mm", "y_mm", "font_size_mm"):
            if key in arguments and (not isinstance(arguments[key], (int, float)) or isinstance(arguments[key], bool) or not math.isfinite(float(arguments[key]))):
                raise ValueError(f"{key} must be a finite number")
        source_view = arguments.get("source_view")
        if source_view is not None and (not isinstance(source_view, str) or not source_view.strip()):
            raise ValueError("source_view must be a non-empty string when provided")
