"""S2 feature-gate surface for the FreeCAD plugin Dock.

Runs the per-feature S2 gate against the active document and writes the
fail-closed S2 -> S3 stage promotion record next to it. Unlike S1, the S2
promotion needs no separate human silhouette approval: `build_s2_promotion`
emits `ready_for_s3` only when every measured feature check passes, and S3
keeps its own strict evidence gates.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PACKAGE_DIR_NAME = "s2_package"


def _repo_root() -> Path:
    for start in (Path(__file__).resolve(), Path.cwd().resolve()):
        for parent in (start, *start.parents):
            if (parent / "backend" / "freecad_bridge" / "s2_feature_gate.py").is_file():
                return parent
    raise FileNotFoundError("agentic-cad repo root was not found")


def _gate_module():
    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from backend.freecad_bridge import s2_feature_gate

    return s2_feature_gate


def _package_dir(document: Any) -> Path:
    file_name = str(getattr(document, "FileName", "") or "")
    if file_name:
        return Path(file_name).resolve().parent / PACKAGE_DIR_NAME
    return _repo_root() / "out" / "freecad_s2_packages" / str(document.Name)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_s2_package(document: Any) -> dict[str, Any]:
    """Measure the S2 feature gate for the active document and write the package."""
    if document is None:
        raise ValueError("No active FreeCAD document")
    gate = _gate_module()
    out_dir = _package_dir(document)
    out_dir.mkdir(parents=True, exist_ok=True)

    facts = gate.measure_s2_features(document, source_fcstd=str(getattr(document, "FileName", "") or ""))
    gate_report = gate.evaluate_s2_gate(facts)
    promotion = gate.build_s2_promotion(gate_report)

    _write_json(out_dir / "s2_feature_facts.json", facts)
    _write_json(out_dir / "s2_feature_gate_report.json", gate_report)
    _write_json(out_dir / "stage_promotion_report.json", promotion)

    return {
        "package_dir": str(out_dir),
        "gate_report": gate_report,
        "promotion": promotion,
    }


def format_s2_package_summary(package: dict[str, Any]) -> str:
    gate_report = package.get("gate_report", {})
    promotion = package.get("promotion", {})
    lines = [
        f"S2 gate: {gate_report.get('status')}",
        f"Bodies: {gate_report.get('body_count')}  Features: {gate_report.get('feature_count')}",
    ]
    failed = gate_report.get("failed_checks") or []
    if failed:
        lines.append("Failed checks: " + ", ".join(str(item) for item in failed))
    lines.append(f"Stage promotion: {promotion.get('status')}")
    reasons = promotion.get("reasons") or []
    if reasons:
        lines.append("Blocked reasons: " + ", ".join(str(item) for item in reasons))
    lines.append(f"Package: {package.get('package_dir')}")
    if promotion.get("status") == "ready_for_s3":
        lines.append("Next: use this promotion record as evidence for an S3 task contract.")
    else:
        lines.append("Next: repair the failing features, then rebuild the S2 gate package.")
    return "\n".join(lines)
