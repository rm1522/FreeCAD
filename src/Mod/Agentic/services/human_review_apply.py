"""Apply saved human-review decisions from the FreeCAD plugin."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any


def apply_saved_human_review_decisions(
    *,
    document: Any | None = None,
    decisions_path: str | Path | None = None,
    workspace_dir: str | Path | None = None,
    open_result: bool = False,
    prefer_backend: bool = True,
) -> dict[str, Any]:
    """Apply UI-saved decisions through the repo backend pipeline."""
    context = resolve_apply_context(
        document=document,
        decisions_path=decisions_path,
        workspace_dir=workspace_dir,
    )
    if prefer_backend:
        try:
            from services.api_client import AgenticApiClient

            report = AgenticApiClient().apply_freecad_human_review(context)
            report["apply_context"] = {key: str(value) for key, value in context.items()}
            report["execution_surface"] = "backend_api"
            if open_result and report.get("ok") and report.get("artifacts", {}).get("assembly_model"):
                _open_model(report["artifacts"]["assembly_model"])
            return report
        except Exception as exc:
            backend_error = str(exc)
        else:
            backend_error = ""
    else:
        backend_error = ""

    repo_root = context["repo_root"]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.freecad_bridge.fastener_review_pipeline import apply_fastener_human_review_pipeline

    report = apply_fastener_human_review_pipeline(
        candidate_report_path=context["candidate_report_path"],
        decisions_path=context["decisions_path"],
        layout_ir_path=context["layout_ir_path"],
        constraint_ir_path=context["constraint_ir_path"],
        part_ir_path=context["part_ir_path"],
        part_model_path=context["part_model_path"],
        part_manifest_path=context["part_manifest_path"],
        hardware_model_path=context["hardware_model_path"],
        hardware_manifest_path=context["hardware_manifest_path"],
        workspace_dir=context["workspace_dir"],
    )
    report["apply_context"] = {key: str(value) for key, value in context.items()}
    report["execution_surface"] = "local_import"
    if backend_error:
        report["backend_fallback_reason"] = backend_error
    if open_result and report.get("ok") and report.get("artifacts", {}).get("assembly_model"):
        _open_model(report["artifacts"]["assembly_model"])
    return report


def resolve_apply_context(
    *,
    document: Any | None = None,
    decisions_path: str | Path | None = None,
    workspace_dir: str | Path | None = None,
) -> dict[str, Path]:
    repo_root = _repo_root()
    base_dir = _base_dir(document)
    cad_root = base_dir.parent
    resolved_decisions = Path(decisions_path).expanduser().resolve() if decisions_path else _decisions_path(document, base_dir)
    resolved_workspace = Path(workspace_dir).expanduser().resolve() if workspace_dir else base_dir / "human_review_applied"
    context = {
        "repo_root": repo_root,
        "base_dir": base_dir,
        "candidate_report_path": _env_path("AGENTIC_CAD_CANDIDATE_REPORT") or base_dir / "wood_screw_candidate_report.json",
        "decisions_path": resolved_decisions,
        "layout_ir_path": _env_path("AGENTIC_CAD_ASSEMBLY_LAYOUT_IR") or base_dir / "assembly_layout_ir.json",
        "constraint_ir_path": _env_path("AGENTIC_CAD_ASSEMBLY_CONSTRAINT_IR") or base_dir / "assembly_constraint_ir.json",
        "part_ir_path": _env_path("AGENTIC_CAD_ASSEMBLY_PART_IR") or base_dir / "assembly_cad_ir.json",
        "part_model_path": _env_path("AGENTIC_CAD_PART_MODEL")
        or _first_existing(cad_root, "*/custom_part_library.FCStd"),
        "part_manifest_path": _env_path("AGENTIC_CAD_PART_MANIFEST")
        or _first_existing(cad_root, "*/custom_part_manifest.json"),
        "hardware_model_path": _env_path("AGENTIC_CAD_HARDWARE_MODEL")
        or _first_existing(cad_root, "*/hardware_library.FCStd"),
        "hardware_manifest_path": _env_path("AGENTIC_CAD_HARDWARE_MANIFEST")
        or _first_existing(cad_root, "*/hardware_library_manifest.json"),
        "workspace_dir": resolved_workspace,
    }
    _validate_context(context)
    return context


def format_apply_summary(report: dict[str, Any]) -> str:
    summary = report.get("candidate_summary", {})
    return (
        "Agentic human review apply: "
        f"{report.get('status', 'unknown')}, "
        f"place={summary.get('place', 0)}, "
        f"reject={summary.get('reject', 0)}, "
        f"ask_user={summary.get('ask_user', 0)}, "
        f"constraints={report.get('constraint_status', 'not_run')}"
    )


def _repo_root() -> Path:
    env_path = _env_path("AGENTIC_CAD_REPO_ROOT")
    if env_path:
        return _require_repo_root(env_path)
    for start in (Path(__file__).resolve(), Path.cwd().resolve()):
        for parent in (start, *start.parents):
            if (parent / "backend" / "freecad_bridge" / "fastener_review_pipeline.py").is_file():
                return parent
    raise FileNotFoundError("agentic-cad repo root was not found; set AGENTIC_CAD_REPO_ROOT")


def _base_dir(document: Any | None) -> Path:
    env_path = _env_path("AGENTIC_CAD_HUMAN_REVIEW_BASE_DIR")
    if env_path:
        return env_path
    file_name = getattr(document, "FileName", "") if document is not None else ""
    if file_name:
        parent = Path(file_name).resolve().parent
        if (parent / "wood_screw_candidate_report.json").is_file():
            return parent
        if (parent.parent / "wood_screw_candidate_report.json").is_file():
            return parent.parent
    cwd = Path.cwd().resolve()
    if (cwd / "wood_screw_candidate_report.json").is_file():
        return cwd
    raise FileNotFoundError("human-review base directory was not found")


def _decisions_path(document: Any | None, base_dir: Path) -> Path:
    env_path = _env_path("AGENTIC_CAD_HUMAN_REVIEW_DECISIONS")
    if env_path:
        return env_path
    file_name = getattr(document, "FileName", "") if document is not None else ""
    if file_name:
        candidate = Path(file_name).resolve().parent / "human_review_decisions.json"
        if candidate.is_file():
            return candidate
    return base_dir / "human_review_visualization" / "human_review_decisions.json"


def _first_existing(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"required artifact not found under {root}: {pattern}")
    return matches[0].resolve()


def _env_path(name: str) -> Path | None:
    value = os.getenv(name)
    return Path(value).expanduser().resolve() if value else None


def _require_repo_root(path: Path) -> Path:
    if not (path / "backend" / "freecad_bridge" / "fastener_review_pipeline.py").is_file():
        raise FileNotFoundError(f"invalid AGENTIC_CAD_REPO_ROOT: {path}")
    return path


def _validate_context(context: dict[str, Path]) -> None:
    for key, path in context.items():
        if key in {"workspace_dir", "base_dir", "repo_root"}:
            continue
        if not path.is_file():
            raise FileNotFoundError(f"{key} does not exist: {path}")


def _open_model(path: str | Path) -> None:
    try:
        import FreeCAD as App  # type: ignore
        import FreeCADGui as Gui  # type: ignore

        App.openDocument(str(path))
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    except Exception:
        return
