"""Machine-readable registry of safe FreeCAD plugin tools."""

from __future__ import annotations


CAPABILITIES = (
    {
        "name": "document.inspect",
        "mutates_document": False,
        "description": "Read the active document, selection, object types, and bounding boxes.",
    },
    {
        "name": "document.undo",
        "mutates_document": True,
        "description": "Undo the previous Agentic CAD document transaction.",
    },
    {
        "name": "primitive.create_box",
        "mutates_document": True,
        "description": "Create a parametric Part workbench box.",
    },
    {
        "name": "primitive.create_cylinder",
        "mutates_document": True,
        "description": "Create a parametric Part workbench cylinder.",
    },
    {
        "name": "object.update_parameters",
        "mutates_document": True,
        "description": "Update supported dimensions on an object identified by stable ID.",
    },
    {
        "name": "object.translate",
        "mutates_document": True,
        "description": "Move an object identified by stable ID by a bounded XYZ translation in millimeters.",
    },
    {
        "name": "sketch.create",
        "mutates_document": True,
        "description": "Create a Sketcher sketch on a base plane (XY, XZ, or YZ), optionally inside a PartDesign body.",
    },
    {
        "name": "sketch.add_geometry",
        "mutates_document": True,
        "description": "Add typed line/circle/arc/rectangle geometry to an existing sketch.",
    },
    {
        "name": "sketch.add_constraint",
        "mutates_document": True,
        "description": "Add typed core constraints (coincident, horizontal, vertical, distance, radius, diameter, angle, symmetric) to an existing sketch.",
    },
    {
        "name": "partdesign.create_body",
        "mutates_document": True,
        "description": "Create an empty PartDesign body that hosts sketches and features.",
    },
    {
        "name": "partdesign.pad",
        "mutates_document": True,
        "description": "Pad a sketch inside its PartDesign body by a positive length in millimeters.",
    },
    {
        "name": "partdesign.pocket",
        "mutates_document": True,
        "description": "Pocket a sketch inside its PartDesign body by a length or through all material.",
    },
    {
        "name": "partdesign.revolution",
        "mutates_document": True,
        "description": "Revolve a sketch inside its PartDesign body around a sketch axis by a bounded angle.",
    },
    {
        "name": "partdesign.hole",
        "mutates_document": True,
        "description": "Cut typed circular holes into a PartDesign body via an auto-generated sketch and pocket.",
    },
    {
        "name": "partdesign.fillet",
        "mutates_document": True,
        "description": "Fillet all edges of a PartDesign body tip feature with a positive radius.",
    },
    {
        "name": "partdesign.chamfer",
        "mutates_document": True,
        "description": "Chamfer all edges of a PartDesign body tip feature with a positive size.",
    },
    {
        "name": "partdesign.mirror",
        "mutates_document": True,
        "description": "Mirror the PartDesign body tip feature across a base origin plane (XY, XZ, YZ).",
    },
    {
        "name": "partdesign.linear_pattern",
        "mutates_document": True,
        "description": "Repeat the PartDesign body tip feature along a base axis (x, y, z) with bounded occurrences.",
    },
)


def list_capabilities() -> list[dict[str, object]]:
    """Return copies so callers cannot mutate the registry."""
    return [dict(item) for item in CAPABILITIES]
