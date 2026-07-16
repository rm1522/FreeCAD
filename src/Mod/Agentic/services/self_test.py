"""Self-test helpers for the external Agentic CAD FreeCAD plugin."""

from __future__ import annotations

import json
from typing import Any

from services.capability_registry import list_capabilities
from services.native_tools import get_document_context, requires_user_approval, validate_plan


SCHEMA_VERSION = "agentic_cad_plugin_self_test.v1"
REQUIRED_CAPABILITIES = frozenset(
    {
        "document.inspect",
        "document.undo",
        "primitive.create_box",
        "primitive.create_cylinder",
        "bim.create_element",
        "object.update_parameters",
        "object.translate",
        "sketch.create",
        "sketch.add_geometry",
        "sketch.add_constraint",
        "partdesign.create_body",
        "partdesign.pad",
        "partdesign.pocket",
        "partdesign.revolution",
        "partdesign.hole",
        "partdesign.fillet",
        "partdesign.chamfer",
        "partdesign.mirror",
        "partdesign.linear_pattern",
    }
)


def _plan(operation_type: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "freecad_tool_plan.v0",
        "plan_id": f"self_test_{operation_type.replace('.', '_')}",
        "status": "ready",
        "operations": [{"type": operation_type, "arguments": arguments or {}}],
    }


def run_self_test(*, include_document_context: bool = True) -> dict[str, Any]:
    """Return a machine-readable plugin self-test report."""
    capabilities = list_capabilities()
    capability_names = {str(item["name"]) for item in capabilities}
    inspect_plan = _plan("document.inspect")
    create_plan = _plan(
        "primitive.create_box",
        {"length_mm": 80.0, "width_mm": 50.0, "height_mm": 20.0},
    )
    unsafe_plan = {
        "schema_version": "freecad_tool_plan.v0",
        "plan_id": "self_test_unsafe",
        "status": "ready",
        "operations": [{"type": "python.eval", "arguments": {"code": "pass"}}],
    }
    checks = [
        {
            "name": "capabilities_present",
            "passed": REQUIRED_CAPABILITIES.issubset(capability_names),
        },
        {
            "name": "inspect_does_not_require_approval",
            "passed": requires_user_approval(inspect_plan) is False,
        },
        {
            "name": "mutation_requires_approval",
            "passed": requires_user_approval(create_plan) is True,
        },
    ]
    try:
        validate_plan(unsafe_plan)
        unsafe_rejected = False
    except ValueError:
        unsafe_rejected = True
    checks.append({"name": "unsafe_operation_rejected", "passed": unsafe_rejected})

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "capabilities": capabilities,
        "checks": checks,
    }
    if include_document_context:
        try:
            context = get_document_context()
            report["document_context"] = {
                "document": context.get("document"),
                "object_count": len(context.get("objects", [])),
                "selection_count": len(context.get("selection", [])),
            }
        except Exception as exc:
            report["document_context_error"] = str(exc)
    return json.loads(json.dumps(report))


def format_self_test_summary(report: dict[str, Any]) -> str:
    """Format a compact user-facing summary for FreeCAD consoles/dialogs."""
    lines = [f"Agentic CAD plugin self-test: {report.get('status')}"]
    for check in report.get("checks", []):
        marker = "PASS" if check.get("passed") else "FAIL"
        lines.append(f"{marker}: {check.get('name')}")
    context = report.get("document_context")
    if isinstance(context, dict):
        lines.append(
            "Document: "
            f"objects={context.get('object_count')} selection={context.get('selection_count')}"
        )
    if report.get("document_context_error"):
        lines.append(f"Document context error: {report['document_context_error']}")
    return "\n".join(lines)
