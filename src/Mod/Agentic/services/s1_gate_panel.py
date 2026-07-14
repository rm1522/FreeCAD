"""S1 structure-gate surface for the FreeCAD plugin Dock.

Runs the S1 gate against the active document, captures silhouette renders when
a GUI view exists (headless FreeCADCmd simply records that no render is
available, which keeps promotion blocked), and applies the user's silhouette
approval into a fail-closed stage promotion record.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SILHOUETTE_VIEWS = (("front", "viewFront"), ("left", "viewLeft"), ("isometric", "viewIsometric"))
PACKAGE_DIR_NAME = "s1_package"


def _repo_root() -> Path:
    for start in (Path(__file__).resolve(), Path.cwd().resolve()):
        for parent in (start, *start.parents):
            if (parent / "backend" / "freecad_bridge" / "s1_structure_gate.py").is_file():
                return parent
    raise FileNotFoundError("agentic-cad repo root was not found")


def _gate_module():
    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from backend.freecad_bridge import s1_structure_gate

    return s1_structure_gate


def _package_dir(document: Any) -> Path:
    file_name = str(getattr(document, "FileName", "") or "")
    if file_name:
        return Path(file_name).resolve().parent / PACKAGE_DIR_NAME
    return _repo_root() / "out" / "freecad_s1_packages" / str(document.Name)


def _capture_silhouettes(out_dir: Path) -> list[str]:
    try:
        import FreeCADGui as Gui  # type: ignore
    except ImportError:
        return []
    active = getattr(Gui, "ActiveDocument", None)
    view = getattr(active, "ActiveView", None) if active is not None else None
    if view is None or not hasattr(view, "saveImage"):
        return []
    render_dir = out_dir / "silhouettes"
    render_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[str] = []
    for name, method_name in SILHOUETTE_VIEWS:
        try:
            method = getattr(view, method_name, None)
            if callable(method):
                method()
            fit_all = getattr(view, "fitAll", None)
            if callable(fit_all):
                fit_all()
            path = render_dir / f"{name}.png"
            view.saveImage(str(path), 1200, 900, "White")
            if path.exists():
                rendered.append(str(path))
        except Exception:
            continue
    return rendered


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_s1_package(document: Any) -> dict[str, Any]:
    """Measure the S1 gate for the active document and write the review package."""
    if document is None:
        raise ValueError("No active FreeCAD document")
    gate = _gate_module()
    out_dir = _package_dir(document)
    out_dir.mkdir(parents=True, exist_ok=True)

    renders = _capture_silhouettes(out_dir)
    facts = gate.measure_s1_structure(document, source_fcstd=str(getattr(document, "FileName", "") or ""))
    gate_report = gate.evaluate_s1_gate(facts)
    approval_template = gate.build_silhouette_approval_template(gate_report, renders)

    _write_json(out_dir / "s1_structure_facts.json", facts)
    _write_json(out_dir / "s1_structure_gate_report.json", gate_report)
    _write_json(out_dir / "s1_silhouette_approval_template.json", approval_template)

    return {
        "package_dir": str(out_dir),
        "gate_report": gate_report,
        "renders": renders,
        "render_available": bool(renders),
    }


def approve_s1_silhouette(
    package_dir: str | Path,
    *,
    reviewer: str,
    rationale: str,
    approved: bool = True,
) -> dict[str, Any]:
    """Apply a silhouette review decision and write the stage promotion record."""
    gate = _gate_module()
    package_path = Path(package_dir)
    gate_report = json.loads((package_path / "s1_structure_gate_report.json").read_text(encoding="utf-8"))
    template = json.loads(
        (package_path / "s1_silhouette_approval_template.json").read_text(encoding="utf-8")
    )
    approval = {
        **template,
        "decision": "approved" if approved else "rejected",
        "approved": bool(approved),
        "reviewer": str(reviewer),
        "rationale": str(rationale),
    }
    promotion = gate.evaluate_stage_promotion(gate_report, approval)

    _write_json(package_path / "s1_silhouette_approval.json", approval)
    _write_json(package_path / "stage_promotion_report.json", promotion)
    return {
        "package_dir": str(package_path),
        "approval": approval,
        "promotion": promotion,
    }


def format_s1_package_summary(package: dict[str, Any]) -> str:
    gate_report = package.get("gate_report", {})
    lines = [
        f"S1 gate: {gate_report.get('status')}",
        f"Solids: {gate_report.get('solid_count')}  Interferences: {gate_report.get('interference_count')}",
    ]
    failed = gate_report.get("failed_checks") or []
    if failed:
        lines.append("Failed checks: " + ", ".join(str(item) for item in failed))
    renders = package.get("renders") or []
    if renders:
        lines.append(f"Silhouettes: {len(renders)} view(s)")
        lines.extend(f"  {path}" for path in renders)
    else:
        lines.append("Silhouettes: none (no GUI view available; promotion stays blocked)")
    lines.append(f"Package: {package.get('package_dir')}")
    lines.append("Next: review the silhouettes, then use Approve S1 Silhouette.")
    return "\n".join(lines)


def format_promotion_summary(result: dict[str, Any]) -> str:
    promotion = result.get("promotion", {})
    lines = [
        f"Stage promotion: {promotion.get('status')}",
        f"{promotion.get('from_stage')} -> {promotion.get('to_stage')}",
    ]
    reasons = promotion.get("reasons") or []
    if reasons:
        lines.append("Blocked reasons: " + ", ".join(str(item) for item in reasons))
    lines.append(f"Package: {result.get('package_dir')}")
    return "\n".join(lines)
