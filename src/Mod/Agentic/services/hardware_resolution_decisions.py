"""FreeCAD plugin helpers for action-level hardware resolution decisions."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from services.fastener_reports import (
    build_hardware_resolution_plan_for_workspace,
    resolve_fastener_context,
)


DEFAULT_DECISIONS_FILENAME = "hardware_resolution_decisions.json"
DEFAULT_FASTENER_REJECT_FILENAME = "human_review_decisions_from_resolution.json"
DEFAULT_INPUT_REQUESTS_FILENAME = "hardware_resolution_input_requests.json"
DEFAULT_INPUT_TEMPLATE_FILENAME = "hardware_resolution_input_submission_template.json"
DEFAULT_INPUT_DRAFT_REPORT_FILENAME = "hardware_resolution_input_draft_report.json"
DEFAULT_INPUT_DRAFT_TEMPLATE_FILENAME = "hardware_resolution_input_draft_template.json"
DEFAULT_INPUT_BLOCKER_PACKET_FILENAME = "hardware_resolution_blocker_packet.json"
DEFAULT_INPUT_ANSWER_CANDIDATES_FILENAME = "hardware_resolution_answer_candidates.json"
DEFAULT_INPUT_EVIDENCE_PACK_FILENAME = "hardware_resolution_evidence_pack.json"
DEFAULT_INPUT_ANSWER_SELECTION_TEMPLATE_FILENAME = "hardware_resolution_answer_selection_template.json"
DEFAULT_INPUT_ANSWER_SELECTION_APPLY_REPORT_FILENAME = "hardware_resolution_answer_selection_apply_report.json"
DEFAULT_INPUT_ANSWER_PREFLIGHT_REPORT_FILENAME = "hardware_resolution_answer_preflight_report.json"
DEFAULT_INPUT_GUARDED_SUBMISSION_DIRNAME = "hardware_resolution_guarded_submission"
DEFAULT_INPUT_MANUAL_COMPLETION_TEMPLATE_FILENAME = "hardware_resolution_manual_completion_template.json"
DEFAULT_INPUT_MANUAL_COMPLETION_REVIEW_TEMPLATE_FILENAME = "hardware_resolution_manual_completion_review_template.json"
DEFAULT_INPUT_MANUAL_COMPLETION_EVIDENCE_DRAFT_REPORT_FILENAME = (
    "hardware_resolution_manual_completion_evidence_draft_report.json"
)
DEFAULT_INPUT_HITL_QUESTION_PACKET_FILENAME = "hardware_resolution_hitl_question_packet.json"
DEFAULT_INPUT_HITL_ANSWER_TEMPLATE_FILENAME = "hardware_resolution_hitl_answer_template.json"
DEFAULT_INPUT_HITL_ANSWER_PATCH_TEMPLATE_FILENAME = "hardware_resolution_hitl_answer_patch_template.json"
DEFAULT_INPUT_HITL_EVIDENCE_REVIEW_PACKET_FILENAME = "hardware_resolution_hitl_evidence_review_packet.json"
DEFAULT_INPUT_HITL_ANSWER_PATCH_FILENAME = "hardware_resolution_hitl_answer_patch.json"
DEFAULT_INPUT_HITL_ANSWER_PATCH_PREFLIGHT_REPORT_FILENAME = (
    "hardware_resolution_hitl_answer_patch_preflight_report.json"
)
DEFAULT_INPUT_HITL_SOURCE_ASSERTION_PACKET_FILENAME = "hardware_resolution_hitl_source_assertion_packet.json"
DEFAULT_INPUT_HITL_SOURCE_ASSERTION_RESPONSE_TEMPLATE_FILENAME = (
    "hardware_resolution_hitl_source_assertion_response_template.json"
)
DEFAULT_INPUT_HITL_SOURCE_ASSERTION_RESPONSE_APPLY_REPORT_FILENAME = (
    "hardware_resolution_hitl_source_assertion_response_apply_report.json"
)
DEFAULT_INPUT_HITL_SOURCE_ASSERTION_DISPOSITION_REPORT_FILENAME = (
    "hardware_resolution_hitl_source_assertion_disposition_report.json"
)
DEFAULT_INPUT_HITL_ANSWER_PATCH_APPLY_REPORT_FILENAME = "hardware_resolution_hitl_answer_patch_apply_report.json"
DEFAULT_INPUT_HITL_ANSWER_APPLY_REPORT_FILENAME = "hardware_resolution_hitl_answer_apply_report.json"
DEFAULT_INPUT_HITL_GUARDED_SUBMISSION_DIRNAME = "hardware_resolution_hitl_guarded_submission"
DEFAULT_INPUT_HITL_PATCH_GUARDED_SUBMISSION_DIRNAME = "hardware_resolution_hitl_patch_guarded_submission"
DEFAULT_INPUT_HITL_SOURCE_RESPONSE_GUARDED_SUBMISSION_DIRNAME = (
    "hardware_resolution_hitl_source_response_guarded_submission"
)
DEFAULT_INPUT_MANUAL_COMPLETION_APPLY_REPORT_FILENAME = "hardware_resolution_manual_completion_apply_report.json"
DEFAULT_INPUT_MANUAL_COMPLETION_PREFLIGHT_REPORT_FILENAME = "hardware_resolution_manual_completion_preflight_report.json"
DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME = "hardware_resolution_blocker_response_template.json"
DEFAULT_INPUT_BLOCKER_RESPONSE_APPLY_REPORT_FILENAME = "hardware_resolution_blocker_response_apply_report.json"
DEFAULT_INPUT_CONFIRMATION_REQUESTS_FILENAME = "hardware_resolution_input_confirmation_requests.json"
DEFAULT_INPUT_CONFIRMATION_REPORT_FILENAME = "hardware_resolution_input_confirmation_report.json"
DEFAULT_INPUT_CONFIRMED_TEMPLATE_FILENAME = "hardware_resolution_input_confirmed_template.json"
DEFAULT_STATUS_REPORT_FILENAME = "hardware_resolution_status_report.json"
DEFAULT_PIPELINE_QUEUE_FILENAME = "hardware_resolution_pipeline_queue.json"
DEFAULT_PIPELINE_EXECUTION_REPORT_FILENAME = "hardware_resolution_pipeline_execution_report.json"
DEFAULT_REGENERATION_DIRNAME = "hardware_resolution_regeneration"
DEFAULT_LAYOUT_PATCH_CANDIDATES_FILENAME = "hardware_layout_patch_candidates.json"
DEFAULT_LAYOUT_PATCH_CONTACT_PROBE_DIRNAME = "layout_patch_contact_probe"
DEFAULT_LAYOUT_PATCH_MERGE_REPORT_FILENAME = "hardware_layout_patch_merge_report.json"
DEFAULT_LAYOUT_PATCH_DOWNSTREAM_DIRNAME = "layout_patch_downstream_regeneration"


def build_resolution_status_report_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write the current decision status report for hardware resolution."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_decisions import (
        apply_hardware_resolution_decisions,
        load_hardware_resolution_decisions,
        save_hardware_resolution_decision_report,
    )

    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    decisions_path = _decisions_path(context, None)
    report = apply_hardware_resolution_decisions(
        _read_json(plan_path),
        load_hardware_resolution_decisions(decisions_path),
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_STATUS_REPORT_FILENAME
    )
    save_hardware_resolution_decision_report(report, destination)
    return {
        "schema_version": "agentic_hardware_resolution_status_command.v1",
        "status": "hardware_resolution_status_report_written",
        "report_status": report.get("status"),
        "summary": report.get("summary", {}),
        "actions": report.get("actions", []),
        "artifacts": {
            "hardware_resolution_plan": str(plan_path),
            "hardware_resolution_decisions": str(decisions_path) if decisions_path.is_file() else None,
            "hardware_resolution_status_report": str(destination),
        },
    }


def build_resolution_pipeline_queue_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write the downstream task queue for ready hardware resolution decisions."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_decisions import (
        load_hardware_resolution_decisions,
    )
    from backend.freecad_bridge.hardware_resolution_pipeline import (
        build_hardware_resolution_pipeline_queue,
        save_hardware_resolution_pipeline_queue,
    )

    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    decisions_path = _decisions_path(context, None)
    queue = build_hardware_resolution_pipeline_queue(
        _read_json(plan_path),
        load_hardware_resolution_decisions(decisions_path),
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_PIPELINE_QUEUE_FILENAME
    )
    save_hardware_resolution_pipeline_queue(queue, destination)
    return {
        "schema_version": "agentic_hardware_resolution_pipeline_queue_command.v1",
        "status": "hardware_resolution_pipeline_queue_written",
        "queue_status": queue.get("status"),
        "summary": queue.get("summary", {}),
        "tasks": queue.get("tasks", []),
        "blocked_actions": queue.get("blocked_actions", []),
        "artifacts": {
            "hardware_resolution_plan": str(plan_path),
            "hardware_resolution_decisions": str(decisions_path) if decisions_path.is_file() else None,
            "hardware_resolution_pipeline_queue": str(destination),
        },
    }


def build_resolution_input_requests_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write fillable requests for remaining source/spec inputs."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_inputs import (
        build_hardware_resolution_input_requests,
        save_hardware_resolution_input_requests,
    )

    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    decisions_path = _decisions_path(context, None)
    request_pack = build_hardware_resolution_input_requests(
        _read_json(plan_path),
        decisions=_read_json(decisions_path) if decisions_path.is_file() else None,
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_REQUESTS_FILENAME
    )
    save_hardware_resolution_input_requests(request_pack, destination)
    return {
        "schema_version": "agentic_hardware_resolution_input_command.v1",
        "status": "hardware_resolution_input_requests_written",
        "request_status": request_pack.get("status"),
        "summary": request_pack.get("summary", {}),
        "requests": request_pack.get("requests", []),
        "artifacts": {
            "hardware_resolution_plan": str(plan_path),
            "hardware_resolution_decisions": str(decisions_path) if decisions_path.is_file() else None,
            "hardware_resolution_input_requests": str(destination),
        },
    }


def execute_resolution_pipeline_queue_for_workspace(
    *,
    document: Any | None = None,
    queue_path: str | Path | None = None,
    output_path: str | Path | None = None,
    workspace_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Execute ready hardware-resolution queue tasks and write an execution report."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_pipeline_executor import (
        execute_hardware_resolution_pipeline_queue,
        save_hardware_resolution_pipeline_execution_report,
    )

    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    resolved_queue_path = (
        Path(queue_path).expanduser().resolve()
        if queue_path
        else context["base_dir"] / DEFAULT_PIPELINE_QUEUE_FILENAME
    )
    if not resolved_queue_path.is_file():
        built = build_resolution_pipeline_queue_for_workspace(document=document)
        resolved_queue_path = Path(built["artifacts"]["hardware_resolution_pipeline_queue"]).resolve()
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_PIPELINE_EXECUTION_REPORT_FILENAME
    )
    cad_root = context["base_dir"].parent
    report = execute_hardware_resolution_pipeline_queue(
        queue=_read_json(resolved_queue_path),
        resolution_plan=_read_json(plan_path),
        base_dir=context["base_dir"],
        human_review_plan_path=_review_plan_path(context),
        candidate_report_path=context["base_dir"] / "wood_screw_candidate_report.json",
        layout_ir_path=context["base_dir"] / "assembly_layout_ir.json",
        constraint_ir_path=context["base_dir"] / "assembly_constraint_ir.json",
        part_ir_path=context["base_dir"] / "assembly_cad_ir.json",
        part_model_path=_optional_first_existing(cad_root, "*/custom_part_library.FCStd"),
        part_manifest_path=_optional_first_existing(cad_root, "*/custom_part_manifest.json"),
        hardware_model_path=_optional_first_existing(cad_root, "*/hardware_library.FCStd"),
        hardware_manifest_path=_optional_first_existing(cad_root, "*/hardware_library_manifest.json"),
        workspace_dir=Path(workspace_dir).expanduser().resolve() if workspace_dir else None,
    )
    save_hardware_resolution_pipeline_execution_report(report, destination)
    return {
        "schema_version": "agentic_hardware_resolution_pipeline_execution_command.v1",
        "status": "hardware_resolution_pipeline_execution_report_written",
        "execution_status": report.get("status"),
        "summary": report.get("summary", {}),
        "task_results": report.get("task_results", []),
        "blocked_actions": report.get("blocked_actions", []),
        "artifacts": {
            "hardware_resolution_plan": str(plan_path),
            "hardware_resolution_pipeline_queue": str(resolved_queue_path),
            "hardware_resolution_pipeline_execution_report": str(destination),
            **report.get("artifacts", {}),
        },
    }


def prepare_resolution_regeneration_inputs_for_workspace(
    *,
    document: Any | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Prepare source/spec regeneration artifacts from staged queue execution outputs."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_regeneration import (
        load_source_evidence_ledger,
        load_spec_patch_queue,
        prepare_hardware_resolution_regeneration_inputs,
    )

    destination = (
        Path(output_dir).expanduser().resolve()
        if output_dir
        else context["base_dir"] / DEFAULT_REGENERATION_DIRNAME
    )
    report = prepare_hardware_resolution_regeneration_inputs(
        hardware_ir=_read_json(context["base_dir"] / "assembly_hardware_ir.json"),
        source_evidence_ledger=load_source_evidence_ledger(
            context["base_dir"] / "hardware_source_evidence_ledger.json"
        ),
        spec_patch_queue=load_spec_patch_queue(
            context["base_dir"] / "hardware_spec_patch_queue.json"
        ),
        output_dir=destination,
    )
    return {
        "schema_version": "agentic_hardware_resolution_regeneration_prep_command.v1",
        "status": "hardware_resolution_regeneration_prep_report_written",
        "prep_status": report.get("status"),
        "summary": report.get("summary", {}),
        "next_steps": report.get("next_steps", []),
        "artifacts": report.get("artifacts", {}),
    }


def check_resolution_regeneration_readiness_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Check whether prepared regeneration artifacts may proceed to FreeCAD generation."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_regeneration_executor import (
        check_hardware_resolution_regeneration_readiness,
        save_hardware_resolution_regeneration_check_report,
    )

    regen_dir = context["base_dir"] / DEFAULT_REGENERATION_DIRNAME
    prep_path = regen_dir / "hardware_resolution_regeneration_prep_report.json"
    if not prep_path.is_file():
        built = prepare_resolution_regeneration_inputs_for_workspace(document=document)
        prep_path = Path(built["artifacts"]["hardware_resolution_regeneration_prep_report"]).resolve()
    placement_path = regen_dir / "hardware_source_evidence_placement_requests.json"
    patched_ir_path = regen_dir / "assembly_hardware_ir.spec_patched.json"
    report = check_hardware_resolution_regeneration_readiness(
        prep_report=_read_json(prep_path),
        assembly_layout_ir=_read_json(context["base_dir"] / "assembly_layout_ir.json")
        if placement_path.is_file() else None,
        placement_request_pack=_read_json(placement_path) if placement_path.is_file() else None,
        hardware_ir_spec_patched=_read_json(patched_ir_path) if patched_ir_path.is_file() else None,
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else regen_dir / "hardware_resolution_regeneration_check_report.json"
    )
    save_hardware_resolution_regeneration_check_report(report, destination)
    return {
        "schema_version": "agentic_hardware_resolution_regeneration_check_command.v1",
        "status": "hardware_resolution_regeneration_check_report_written",
        "check_status": report.get("status"),
        "summary": report.get("summary", {}),
        "blocking_reasons": report.get("blocking_reasons", []),
        "next_steps": report.get("next_steps", []),
        "artifacts": {
            "hardware_resolution_regeneration_prep_report": str(prep_path),
            "hardware_resolution_regeneration_check_report": str(destination),
        },
    }


def execute_resolution_regeneration_for_workspace(
    *,
    document: Any | None = None,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Execute FreeCAD hardware regeneration when readiness checks pass."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_regeneration_apply import (
        execute_hardware_resolution_regeneration,
        save_hardware_resolution_regeneration_execution_report,
    )

    regen_dir = context["base_dir"] / DEFAULT_REGENERATION_DIRNAME
    check_path = regen_dir / "hardware_resolution_regeneration_check_report.json"
    if not check_path.is_file():
        built = check_resolution_regeneration_readiness_for_workspace(document=document)
        check_path = Path(built["artifacts"]["hardware_resolution_regeneration_check_report"]).resolve()
    patched_ir_path = regen_dir / "assembly_hardware_ir.spec_patched.json"
    hardware_ir_path = patched_ir_path if patched_ir_path.is_file() else context["base_dir"] / "assembly_hardware_ir.json"
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else regen_dir / "hardware_resolution_regeneration_execution_report.json"
    )
    report = execute_hardware_resolution_regeneration(
        check_report=_read_json(check_path),
        hardware_ir=_read_json(hardware_ir_path),
        output_dir=Path(output_dir).expanduser().resolve() if output_dir else regen_dir / "freecad_generation",
    )
    save_hardware_resolution_regeneration_execution_report(report, destination)
    return {
        "schema_version": "agentic_hardware_resolution_regeneration_execution_command.v1",
        "status": "hardware_resolution_regeneration_execution_report_written",
        "execution_status": report.get("status"),
        "ok": report.get("ok", False),
        "summary": report.get("summary", {}),
        "blocking_reasons": report.get("blocking_reasons", []),
        "artifacts": {
            "hardware_resolution_regeneration_check_report": str(check_path),
            "hardware_resolution_regeneration_execution_report": str(destination),
            **report.get("artifacts", {}),
        },
    }


def build_resolution_layout_patch_candidates_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build non-committing assembly-layout patch candidates for contact probing."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_layout_patch import (
        build_hardware_layout_patch_candidates,
        empty_placement_target_report,
        save_hardware_layout_patch_candidates,
    )

    regen_dir = context["base_dir"] / DEFAULT_REGENERATION_DIRNAME
    check_path = regen_dir / "hardware_resolution_regeneration_check_report.json"
    if not check_path.is_file():
        built = check_resolution_regeneration_readiness_for_workspace(document=document)
        check_path = Path(built["artifacts"]["hardware_resolution_regeneration_check_report"]).resolve()
    check_report = _read_json(check_path)
    placement_report = check_report.get("placement_target_report")
    if not isinstance(placement_report, dict):
        placement_report = empty_placement_target_report()
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else regen_dir / DEFAULT_LAYOUT_PATCH_CANDIDATES_FILENAME
    )
    report = build_hardware_layout_patch_candidates(
        placement_target_report=placement_report,
        assembly_layout_ir=_read_json(context["base_dir"] / "assembly_layout_ir.json"),
    )
    save_hardware_layout_patch_candidates(report, destination)
    return {
        "schema_version": "agentic_hardware_layout_patch_candidates_command.v1",
        "status": "hardware_layout_patch_candidates_written",
        "candidate_status": report.get("status"),
        "summary": report.get("summary", {}),
        "candidates": report.get("candidates", []),
        "blocked_items": report.get("blocked_items", []),
        "artifacts": {
            "hardware_resolution_regeneration_check_report": str(check_path),
            "hardware_layout_patch_candidates": str(destination),
        },
    }


def probe_resolution_layout_patch_contacts_for_workspace(
    *,
    document: Any | None = None,
    workspace_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run FreeCAD contact/collision probing for current layout patch candidates."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_contact_probe import (
        generate_hardware_layout_patch_contact_probe,
    )

    regen_dir = context["base_dir"] / DEFAULT_REGENERATION_DIRNAME
    candidates_path = regen_dir / DEFAULT_LAYOUT_PATCH_CANDIDATES_FILENAME
    if not candidates_path.is_file():
        built = build_resolution_layout_patch_candidates_for_workspace(document=document)
        candidates_path = Path(built["artifacts"]["hardware_layout_patch_candidates"]).resolve()
    cad_root = context["base_dir"].parent
    destination = (
        Path(workspace_dir).expanduser().resolve()
        if workspace_dir
        else regen_dir / DEFAULT_LAYOUT_PATCH_CONTACT_PROBE_DIRNAME
    )
    result = generate_hardware_layout_patch_contact_probe(
        assembly_model_path=context["base_dir"] / "assembly_candidate.FCStd",
        hardware_model_path=_first_existing(cad_root, "*/hardware_library.FCStd"),
        hardware_manifest_path=_first_existing(cad_root, "*/hardware_library_manifest.json"),
        layout_patch_candidates=_read_json(candidates_path),
        workspace_dir=destination,
    )
    return {
        "schema_version": "agentic_hardware_layout_patch_contact_probe_command.v1",
        "status": "hardware_layout_patch_contact_probe_written",
        "probe_status": result.get("status"),
        "ok": result.get("ok", False),
        "summary": result.get("summary", {}),
        "artifacts": result.get("artifacts", {}),
    }


def merge_resolution_layout_patch_candidates_for_workspace(
    *,
    document: Any | None = None,
    approved: bool = False,
    approver: str = "freecad-ui",
    output_report_path: str | Path | None = None,
    output_layout_path: str | Path | None = None,
) -> dict[str, Any]:
    """Merge probe-approved layout candidates only after explicit approval."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_layout_merge import (
        merge_approved_hardware_layout_patch_candidates,
        save_hardware_layout_patch_merge_outputs,
    )

    regen_dir = context["base_dir"] / DEFAULT_REGENERATION_DIRNAME
    candidates_path = regen_dir / DEFAULT_LAYOUT_PATCH_CANDIDATES_FILENAME
    if not candidates_path.is_file():
        built = build_resolution_layout_patch_candidates_for_workspace(document=document)
        candidates_path = Path(built["artifacts"]["hardware_layout_patch_candidates"]).resolve()
    contact_report_path = (
        regen_dir
        / DEFAULT_LAYOUT_PATCH_CONTACT_PROBE_DIRNAME
        / "hardware_layout_patch_contact_probe_report.json"
    )
    if not contact_report_path.is_file():
        built = probe_resolution_layout_patch_contacts_for_workspace(document=document)
        contact_report_path = Path(built["artifacts"]["contact_probe_report"]).resolve()
    report = merge_approved_hardware_layout_patch_candidates(
        assembly_layout_ir=_read_json(context["base_dir"] / "assembly_layout_ir.json"),
        layout_patch_candidates=_read_json(candidates_path),
        contact_probe_report=_read_json(contact_report_path),
        approved=approved,
        approver=approver,
    )
    artifacts = save_hardware_layout_patch_merge_outputs(
        report,
        report_path=(
            Path(output_report_path).expanduser().resolve()
            if output_report_path
            else regen_dir / DEFAULT_LAYOUT_PATCH_MERGE_REPORT_FILENAME
        ),
        merged_layout_path=Path(output_layout_path).expanduser().resolve() if output_layout_path else None,
    )
    return {
        "schema_version": "agentic_hardware_layout_patch_merge_command.v1",
        "status": "hardware_layout_patch_merge_report_written",
        "merge_status": report.get("status"),
        "ok": report.get("ok", False),
        "summary": report.get("summary", {}),
        "artifacts": artifacts,
    }


def regenerate_resolution_layout_patch_assembly_for_workspace(
    *,
    document: Any | None = None,
    workspace_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Regenerate assembly artifacts from an approved layout patch merge."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_layout_regeneration import (
        regenerate_assembly_from_layout_patch_merge,
    )

    regen_dir = context["base_dir"] / DEFAULT_REGENERATION_DIRNAME
    merge_path = regen_dir / DEFAULT_LAYOUT_PATCH_MERGE_REPORT_FILENAME
    if not merge_path.is_file():
        built = merge_resolution_layout_patch_candidates_for_workspace(document=document, approved=False)
        merge_path = Path(built["artifacts"]["hardware_layout_patch_merge_report"]).resolve()
    cad_root = context["base_dir"].parent
    destination = (
        Path(workspace_dir).expanduser().resolve()
        if workspace_dir
        else regen_dir / DEFAULT_LAYOUT_PATCH_DOWNSTREAM_DIRNAME
    )
    result = regenerate_assembly_from_layout_patch_merge(
        merge_report=_read_json(merge_path),
        part_ir=_read_json(context["base_dir"] / "assembly_cad_ir.json"),
        constraint_ir=_read_json(context["base_dir"] / "assembly_constraint_ir.json"),
        part_model_path=_first_existing(cad_root, "*/custom_part_library.FCStd"),
        part_manifest_path=_first_existing(cad_root, "*/custom_part_manifest.json"),
        hardware_model_path=_first_existing(cad_root, "*/hardware_library.FCStd"),
        hardware_manifest_path=_first_existing(cad_root, "*/hardware_library_manifest.json"),
        workspace_dir=destination,
    )
    return {
        "schema_version": "agentic_hardware_layout_patch_downstream_regeneration_command.v1",
        "status": "hardware_layout_patch_downstream_regeneration_report_written",
        "regeneration_status": result.get("status"),
        "ok": result.get("ok", False),
        "summary": result.get("summary", {}),
        "blocking_reasons": result.get("blocking_reasons", []),
        "artifacts": result.get("artifacts", {}),
    }


def build_resolution_input_submission_template_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a fillable JSON template for pending input requests."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_input_submission import (
        build_hardware_resolution_input_submission_template,
        save_hardware_resolution_input_submission_template,
    )

    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    template = build_hardware_resolution_input_submission_template(_read_json(requests_path))
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_TEMPLATE_FILENAME
    )
    save_hardware_resolution_input_submission_template(template, destination)
    return {
        "schema_version": "agentic_hardware_resolution_input_command.v1",
        "status": "hardware_resolution_input_submission_template_written",
        "template_status": template.get("status"),
        "submission_count": len(template.get("submissions", [])),
        "artifacts": {
            "hardware_resolution_input_requests": str(requests_path),
            "hardware_resolution_input_submission_template": str(destination),
        },
    }


def build_resolution_input_drafts_for_workspace(
    *,
    document: Any | None = None,
    output_report_path: str | Path | None = None,
    output_template_path: str | Path | None = None,
    evidence_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    """Build conservative draft submissions from local source facts."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_input_draft import (
        build_hardware_resolution_input_draft_report,
        save_hardware_resolution_input_draft_report,
        save_hardware_resolution_input_draft_template,
    )

    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    resolved_evidence_paths = _default_input_draft_evidence_paths(context["repo_root"], evidence_paths)
    report = build_hardware_resolution_input_draft_report(
        input_requests=_read_json(requests_path),
        evidence_documents=[
            _read_json(path)
            for path in resolved_evidence_paths
            if Path(path).is_file()
        ],
    )
    report_destination = (
        Path(output_report_path).expanduser().resolve()
        if output_report_path
        else context["base_dir"] / DEFAULT_INPUT_DRAFT_REPORT_FILENAME
    )
    template_destination = (
        Path(output_template_path).expanduser().resolve()
        if output_template_path
        else context["base_dir"] / DEFAULT_INPUT_DRAFT_TEMPLATE_FILENAME
    )
    save_hardware_resolution_input_draft_report(report, report_destination)
    save_hardware_resolution_input_draft_template(report, template_destination)
    return {
        "schema_version": "agentic_hardware_resolution_input_draft_command.v1",
        "status": "hardware_resolution_input_draft_written",
        "draft_status": report.get("status"),
        "summary": report.get("summary", {}),
        "items": report.get("items", []),
        "artifacts": {
            "hardware_resolution_input_requests": str(requests_path),
            "hardware_resolution_input_draft_report": str(report_destination),
            "hardware_resolution_input_draft_template": str(template_destination),
            "evidence_paths": [str(path) for path in resolved_evidence_paths],
        },
    }


def build_resolution_blocker_packet_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a UI-facing packet for blocked source/spec inputs."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_blocker_packet import (
        build_hardware_resolution_blocker_packet,
        save_hardware_resolution_blocker_packet,
    )

    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    draft_path = context["base_dir"] / DEFAULT_INPUT_DRAFT_REPORT_FILENAME
    if not draft_path.is_file():
        built = build_resolution_input_drafts_for_workspace(document=document)
        draft_path = Path(built["artifacts"]["hardware_resolution_input_draft_report"]).resolve()
    packet = build_hardware_resolution_blocker_packet(
        input_requests=_read_json(requests_path),
        draft_report=_read_json(draft_path),
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    )
    save_hardware_resolution_blocker_packet(packet, destination)
    return {
        "schema_version": "agentic_hardware_resolution_blocker_packet_command.v1",
        "status": "hardware_resolution_blocker_packet_written",
        "packet_status": packet.get("status"),
        "summary": packet.get("summary", {}),
        "items": packet.get("items", []),
        "artifacts": {
            "hardware_resolution_input_requests": str(requests_path),
            "hardware_resolution_input_draft_report": str(draft_path),
            "hardware_resolution_blocker_packet": str(destination),
        },
    }


def build_resolution_answer_candidates_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
    evidence_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    """Write non-committing answer candidates for the current blocker packet."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_answer_candidates import (
        build_hardware_resolution_answer_candidates,
        save_hardware_resolution_answer_candidates,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    resolved_evidence_paths = _default_input_draft_evidence_paths(context["repo_root"], evidence_paths)
    candidate_pack = build_hardware_resolution_answer_candidates(
        blocker_packet=_read_json(packet_path),
        evidence_documents=[
            _read_json(path)
            for path in resolved_evidence_paths
            if Path(path).is_file()
        ],
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_ANSWER_CANDIDATES_FILENAME
    )
    save_hardware_resolution_answer_candidates(candidate_pack, destination)
    return {
        "schema_version": "agentic_hardware_resolution_answer_candidates_command.v1",
        "status": "hardware_resolution_answer_candidates_written",
        "candidate_status": candidate_pack.get("status"),
        "summary": candidate_pack.get("summary", {}),
        "items": candidate_pack.get("items", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_answer_candidates": str(destination),
            "evidence_paths": [str(path) for path in resolved_evidence_paths],
        },
    }


def build_resolution_blocker_response_template_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a fillable response template from the current blocker packet."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_blocker_response import (
        build_hardware_resolution_blocker_response_template,
        save_hardware_resolution_blocker_response_template,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    template = build_hardware_resolution_blocker_response_template(_read_json(packet_path))
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME
    )
    save_hardware_resolution_blocker_response_template(template, destination)
    return {
        "schema_version": "agentic_hardware_resolution_blocker_response_command.v1",
        "status": "hardware_resolution_blocker_response_template_written",
        "response_status": template.get("status"),
        "response_count": len(template.get("responses", [])),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_blocker_response_template": str(destination),
        },
    }


def build_resolution_manual_completion_template_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a source-backed manual completion template for blocker requests."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_manual_completion import (
        build_hardware_resolution_manual_completion_template,
        save_hardware_resolution_manual_completion_template,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    template = build_hardware_resolution_manual_completion_template(_read_json(packet_path))
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_MANUAL_COMPLETION_TEMPLATE_FILENAME
    )
    save_hardware_resolution_manual_completion_template(template, destination)
    return {
        "schema_version": "agentic_hardware_resolution_manual_completion_command.v1",
        "status": "hardware_resolution_manual_completion_template_written",
        "completion_status": template.get("status"),
        "completion_count": len(template.get("completions", [])),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_manual_completion_template": str(destination),
        },
    }


def apply_resolution_manual_completion_for_workspace(
    *,
    document: Any | None = None,
    manual_template_path: str | Path | None = None,
    response_template_path: str | Path | None = None,
    output_report_path: str | Path | None = None,
    output_response_template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Copy source-backed manual completions into the blocker response template."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_manual_completion import (
        apply_hardware_resolution_manual_completion_to_blocker_response_template,
        save_hardware_resolution_manual_completion_apply_report,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    manual_path = _manual_completion_template_path(context, manual_template_path)
    if not manual_path.is_file():
        built = build_resolution_manual_completion_template_for_workspace(document=document)
        manual_path = Path(built["artifacts"]["hardware_resolution_manual_completion_template"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_blocker_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_blocker_response_template"]).resolve()
    report = apply_hardware_resolution_manual_completion_to_blocker_response_template(
        blocker_packet=_read_json(packet_path),
        manual_completion_template=_read_json(manual_path),
        response_template=_read_json(response_path),
    )
    report_destination = (
        Path(output_report_path).expanduser().resolve()
        if output_report_path
        else context["base_dir"] / DEFAULT_INPUT_MANUAL_COMPLETION_APPLY_REPORT_FILENAME
    )
    response_destination = (
        Path(output_response_template_path).expanduser().resolve()
        if output_response_template_path
        else response_path
    )
    artifacts = save_hardware_resolution_manual_completion_apply_report(
        report,
        report_path=report_destination,
        response_template_path=response_destination,
    )
    return {
        "schema_version": "agentic_hardware_resolution_manual_completion_command.v1",
        "status": "hardware_resolution_manual_completion_applied",
        "apply_status": report.get("status"),
        "summary": report.get("summary", {}),
        "applied_completions": report.get("applied_completions", []),
        "invalid_completions": report.get("invalid_completions", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_manual_completion_template": str(manual_path),
            **artifacts,
        },
    }


def preflight_resolution_manual_completion_for_workspace(
    *,
    document: Any | None = None,
    manual_template_path: str | Path | None = None,
    response_template_path: str | Path | None = None,
    submission_template_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Preflight manual source/spec completions through submission validation."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_manual_completion import (
        preflight_hardware_resolution_manual_completion,
        save_hardware_resolution_manual_completion_preflight_report,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    manual_path = _manual_completion_template_path(context, manual_template_path)
    if not manual_path.is_file():
        built = build_resolution_manual_completion_template_for_workspace(document=document)
        manual_path = Path(built["artifacts"]["hardware_resolution_manual_completion_template"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_blocker_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_blocker_response_template"]).resolve()
    submission_path = (
        Path(submission_template_path).expanduser().resolve()
        if submission_template_path
        else context["base_dir"] / DEFAULT_INPUT_TEMPLATE_FILENAME
    )
    if not submission_path.is_file():
        built = build_resolution_input_submission_template_for_workspace(document=document)
        submission_path = Path(built["artifacts"]["hardware_resolution_input_submission_template"]).resolve()
    report = preflight_hardware_resolution_manual_completion(
        blocker_packet=_read_json(packet_path),
        input_requests=_read_json(requests_path),
        manual_completion_template=_read_json(manual_path),
        response_template=_read_json(response_path),
        submission_template=_read_json(submission_path),
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_MANUAL_COMPLETION_PREFLIGHT_REPORT_FILENAME
    )
    save_hardware_resolution_manual_completion_preflight_report(report, destination)
    return {
        "schema_version": "agentic_hardware_resolution_manual_completion_preflight_command.v1",
        "status": "hardware_resolution_manual_completion_preflight_written",
        "preflight_status": report.get("status"),
        "ok_to_submit": report.get("ok_to_submit", False),
        "summary": report.get("summary", {}),
        "next_actions": report.get("next_actions", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_input_requests": str(requests_path),
            "hardware_resolution_manual_completion_template": str(manual_path),
            "hardware_resolution_blocker_response_template": str(response_path),
            "hardware_resolution_input_submission_template": str(submission_path),
            "hardware_resolution_manual_completion_preflight_report": str(destination),
        },
    }


def build_resolution_evidence_pack_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a non-committing evidence pack for blocked source/spec inputs."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_evidence_pack import (
        build_hardware_resolution_evidence_pack,
        save_hardware_resolution_evidence_pack,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    candidates_path = context["base_dir"] / DEFAULT_INPUT_ANSWER_CANDIDATES_FILENAME
    if not candidates_path.is_file():
        built = build_resolution_answer_candidates_for_workspace(document=document)
        candidates_path = Path(built["artifacts"]["hardware_resolution_answer_candidates"]).resolve()
    pack = build_hardware_resolution_evidence_pack(
        blocker_packet=_read_json(packet_path),
        answer_candidates=_read_json(candidates_path),
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_EVIDENCE_PACK_FILENAME
    )
    save_hardware_resolution_evidence_pack(pack, destination)
    return {
        "schema_version": "agentic_hardware_resolution_evidence_pack_command.v1",
        "status": "hardware_resolution_evidence_pack_written",
        "pack_status": pack.get("status"),
        "summary": pack.get("summary", {}),
        "items": pack.get("items", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_answer_candidates": str(candidates_path),
            "hardware_resolution_evidence_pack": str(destination),
        },
    }


def draft_resolution_manual_completion_from_evidence_pack_for_workspace(
    *,
    document: Any | None = None,
    manual_template_path: str | Path | None = None,
    evidence_pack_path: str | Path | None = None,
    output_report_path: str | Path | None = None,
    output_review_template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a review-only manual completion draft from the evidence pack."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_manual_completion import (
        draft_hardware_resolution_manual_completion_from_evidence_pack,
        save_hardware_resolution_manual_completion_evidence_draft_report,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    manual_path = _manual_completion_template_path(context, manual_template_path)
    if not manual_path.is_file():
        built = build_resolution_manual_completion_template_for_workspace(document=document)
        manual_path = Path(built["artifacts"]["hardware_resolution_manual_completion_template"]).resolve()
    evidence_path = (
        Path(evidence_pack_path).expanduser().resolve()
        if evidence_pack_path
        else context["base_dir"] / DEFAULT_INPUT_EVIDENCE_PACK_FILENAME
    )
    if not evidence_path.is_file():
        built = build_resolution_evidence_pack_for_workspace(document=document)
        evidence_path = Path(built["artifacts"]["hardware_resolution_evidence_pack"]).resolve()
    report = draft_hardware_resolution_manual_completion_from_evidence_pack(
        blocker_packet=_read_json(packet_path),
        manual_completion_template=_read_json(manual_path),
        evidence_pack=_read_json(evidence_path),
    )
    report_destination = (
        Path(output_report_path).expanduser().resolve()
        if output_report_path
        else context["base_dir"] / DEFAULT_INPUT_MANUAL_COMPLETION_EVIDENCE_DRAFT_REPORT_FILENAME
    )
    template_destination = (
        Path(output_review_template_path).expanduser().resolve()
        if output_review_template_path
        else context["base_dir"] / DEFAULT_INPUT_MANUAL_COMPLETION_REVIEW_TEMPLATE_FILENAME
    )
    artifacts = save_hardware_resolution_manual_completion_evidence_draft_report(
        report,
        report_path=report_destination,
        manual_template_path=template_destination,
    )
    return {
        "schema_version": "agentic_hardware_resolution_manual_completion_evidence_draft_command.v1",
        "status": "hardware_resolution_manual_completion_evidence_draft_written",
        "draft_status": report.get("status"),
        "summary": report.get("summary", {}),
        "drafted_completions": report.get("drafted_completions", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_manual_completion_template": str(manual_path),
            "hardware_resolution_evidence_pack": str(evidence_path),
            **artifacts,
        },
    }


def build_resolution_hitl_question_packet_for_workspace(
    *,
    document: Any | None = None,
    manual_template_path: str | Path | None = None,
    evidence_pack_path: str | Path | None = None,
    output_packet_path: str | Path | None = None,
    output_answer_template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write HITL questions and a fillable answer template for manual review."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_hitl_questions import (
        build_hardware_resolution_hitl_answer_template,
        build_hardware_resolution_hitl_question_packet,
        save_hardware_resolution_hitl_answer_template,
        save_hardware_resolution_hitl_question_packet,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    manual_path = _manual_completion_template_path(context, manual_template_path)
    if not manual_path.is_file():
        built = draft_resolution_manual_completion_from_evidence_pack_for_workspace(document=document)
        manual_path = Path(built["artifacts"]["hardware_resolution_manual_completion_review_template"]).resolve()
    evidence_path = (
        Path(evidence_pack_path).expanduser().resolve()
        if evidence_pack_path
        else context["base_dir"] / DEFAULT_INPUT_EVIDENCE_PACK_FILENAME
    )
    if not evidence_path.is_file():
        built = build_resolution_evidence_pack_for_workspace(document=document)
        evidence_path = Path(built["artifacts"]["hardware_resolution_evidence_pack"]).resolve()
    question_packet = build_hardware_resolution_hitl_question_packet(
        blocker_packet=_read_json(packet_path),
        manual_completion_template=_read_json(manual_path),
        evidence_pack=_read_json(evidence_path),
    )
    answer_template = build_hardware_resolution_hitl_answer_template(question_packet)
    packet_destination = (
        Path(output_packet_path).expanduser().resolve()
        if output_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_QUESTION_PACKET_FILENAME
    )
    answer_destination = (
        Path(output_answer_template_path).expanduser().resolve()
        if output_answer_template_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_TEMPLATE_FILENAME
    )
    save_hardware_resolution_hitl_question_packet(question_packet, packet_destination)
    save_hardware_resolution_hitl_answer_template(answer_template, answer_destination)
    return {
        "schema_version": "agentic_hardware_resolution_hitl_question_packet_command.v1",
        "status": "hardware_resolution_hitl_question_packet_written",
        "question_status": question_packet.get("status"),
        "summary": question_packet.get("summary", {}),
        "items": question_packet.get("items", []),
        "questions": question_packet.get("questions", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_manual_completion_review_template": str(manual_path),
            "hardware_resolution_evidence_pack": str(evidence_path),
            "hardware_resolution_hitl_question_packet": str(packet_destination),
            "hardware_resolution_hitl_answer_template": str(answer_destination),
        },
    }


def build_resolution_hitl_answer_patch_template_for_workspace(
    *,
    document: Any | None = None,
    question_packet_path: str | Path | None = None,
    answer_template_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a focused HITL answer patch template for unanswered rows."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_hitl_questions import (
        build_hardware_resolution_hitl_answer_patch_template,
        save_hardware_resolution_hitl_answer_patch_template,
    )

    question_path = (
        Path(question_packet_path).expanduser().resolve()
        if question_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_QUESTION_PACKET_FILENAME
    )
    if not question_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        question_path = Path(built["artifacts"]["hardware_resolution_hitl_question_packet"]).resolve()
    answer_path = (
        Path(answer_template_path).expanduser().resolve()
        if answer_template_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_TEMPLATE_FILENAME
    )
    if not answer_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        answer_path = Path(built["artifacts"]["hardware_resolution_hitl_answer_template"]).resolve()
    template = build_hardware_resolution_hitl_answer_patch_template(
        question_packet=_read_json(question_path),
        answer_template=_read_json(answer_path),
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_PATCH_TEMPLATE_FILENAME
    )
    save_hardware_resolution_hitl_answer_patch_template(template, destination)
    return {
        "schema_version": "agentic_hardware_resolution_hitl_answer_patch_template_command.v1",
        "status": "hardware_resolution_hitl_answer_patch_template_written",
        "patch_template_status": template.get("status"),
        "summary": template.get("summary", {}),
        "patch_instructions": template.get("patch_instructions", []),
        "artifacts": {
            "hardware_resolution_hitl_question_packet": str(question_path),
            "hardware_resolution_hitl_answer_template": str(answer_path),
            "hardware_resolution_hitl_answer_patch_template": str(destination),
        },
    }


def build_resolution_hitl_evidence_review_packet_for_workspace(
    *,
    document: Any | None = None,
    blocker_packet_path: str | Path | None = None,
    question_packet_path: str | Path | None = None,
    answer_template_path: str | Path | None = None,
    evidence_pack_path: str | Path | None = None,
    manual_template_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a non-committing source evidence review packet for unanswered HITL rows."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_hitl_questions import (
        build_hardware_resolution_hitl_evidence_review_packet,
        save_hardware_resolution_hitl_evidence_review_packet,
    )

    blocker_path = (
        Path(blocker_packet_path).expanduser().resolve()
        if blocker_packet_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    )
    if not blocker_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        blocker_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    question_path = (
        Path(question_packet_path).expanduser().resolve()
        if question_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_QUESTION_PACKET_FILENAME
    )
    if not question_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        question_path = Path(built["artifacts"]["hardware_resolution_hitl_question_packet"]).resolve()
    answer_path = (
        Path(answer_template_path).expanduser().resolve()
        if answer_template_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_TEMPLATE_FILENAME
    )
    if not answer_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        answer_path = Path(built["artifacts"]["hardware_resolution_hitl_answer_template"]).resolve()
    evidence_path = (
        Path(evidence_pack_path).expanduser().resolve()
        if evidence_pack_path
        else context["base_dir"] / DEFAULT_INPUT_EVIDENCE_PACK_FILENAME
    )
    if not evidence_path.is_file():
        built = build_resolution_evidence_pack_for_workspace(document=document)
        evidence_path = Path(built["artifacts"]["hardware_resolution_evidence_pack"]).resolve()
    manual_path = _manual_completion_template_path(context, manual_template_path)
    if not manual_path.is_file():
        built = draft_resolution_manual_completion_from_evidence_pack_for_workspace(document=document)
        manual_path = Path(built["artifacts"]["hardware_resolution_manual_completion_review_template"]).resolve()
    packet = build_hardware_resolution_hitl_evidence_review_packet(
        blocker_packet=_read_json(blocker_path),
        question_packet=_read_json(question_path),
        answer_template=_read_json(answer_path),
        evidence_pack=_read_json(evidence_path),
        manual_completion_template=_read_json(manual_path),
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_EVIDENCE_REVIEW_PACKET_FILENAME
    )
    save_hardware_resolution_hitl_evidence_review_packet(packet, destination)
    return {
        "schema_version": "agentic_hardware_resolution_hitl_evidence_review_command.v1",
        "status": "hardware_resolution_hitl_evidence_review_packet_written",
        "review_status": packet.get("status"),
        "summary": packet.get("summary", {}),
        "review_items": packet.get("review_items", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(blocker_path),
            "hardware_resolution_hitl_question_packet": str(question_path),
            "hardware_resolution_hitl_answer_template": str(answer_path),
            "hardware_resolution_evidence_pack": str(evidence_path),
            "hardware_resolution_manual_completion_review_template": str(manual_path),
            "hardware_resolution_hitl_evidence_review_packet": str(destination),
        },
    }


def patch_resolution_hitl_answer_template_for_workspace(
    *,
    document: Any | None = None,
    question_packet_path: str | Path | None = None,
    answer_template_path: str | Path | None = None,
    answer_patch_path: str | Path | None = None,
    output_report_path: str | Path | None = None,
    output_answer_template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Patch the HITL answer template from selected options or explicit answers."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_hitl_questions import (
        apply_hardware_resolution_hitl_answer_patch_to_template,
        save_hardware_resolution_hitl_answer_patch_apply_report,
    )

    question_path = (
        Path(question_packet_path).expanduser().resolve()
        if question_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_QUESTION_PACKET_FILENAME
    )
    if not question_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        question_path = Path(built["artifacts"]["hardware_resolution_hitl_question_packet"]).resolve()
    answer_path = (
        Path(answer_template_path).expanduser().resolve()
        if answer_template_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_TEMPLATE_FILENAME
    )
    if not answer_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        answer_path = Path(built["artifacts"]["hardware_resolution_hitl_answer_template"]).resolve()
    patch_path = (
        Path(answer_patch_path).expanduser().resolve()
        if answer_patch_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_PATCH_FILENAME
    )
    if not patch_path.is_file():
        raise FileNotFoundError(
            f"Create {patch_path} before patching HITL answers. "
            "It must use schema hardware_resolution_hitl_answer_patch.v1."
        )
    report = apply_hardware_resolution_hitl_answer_patch_to_template(
        question_packet=_read_json(question_path),
        answer_template=_read_json(answer_path),
        answer_patch=_read_json(patch_path),
    )
    report_destination = (
        Path(output_report_path).expanduser().resolve()
        if output_report_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_PATCH_APPLY_REPORT_FILENAME
    )
    answer_destination = (
        Path(output_answer_template_path).expanduser().resolve()
        if output_answer_template_path
        else answer_path
    )
    artifacts = save_hardware_resolution_hitl_answer_patch_apply_report(
        report,
        report_path=report_destination,
        answer_template_path=answer_destination if report.get("status") != "invalid" else None,
    )
    return {
        "schema_version": "agentic_hardware_resolution_hitl_answer_patch_command.v1",
        "status": "hardware_resolution_hitl_answer_template_patched",
        "patch_status": report.get("status"),
        "summary": report.get("summary", {}),
        "applied_patches": report.get("applied_patches", []),
        "invalid_patches": report.get("invalid_patches", []),
        "artifacts": {
            "hardware_resolution_hitl_question_packet": str(question_path),
            "hardware_resolution_hitl_answer_template": str(answer_path),
            "hardware_resolution_hitl_answer_patch": str(patch_path),
            **artifacts,
        },
    }


def preflight_resolution_hitl_answer_patch_for_workspace(
    *,
    document: Any | None = None,
    evidence_review_packet_path: str | Path | None = None,
    answer_patch_path: str | Path | None = None,
    output_report_path: str | Path | None = None,
) -> dict[str, Any]:
    """Preflight a HITL answer patch before it edits the answer template."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_hitl_questions import (
        preflight_hardware_resolution_hitl_answer_patch_against_review,
        save_hardware_resolution_hitl_answer_patch_preflight_report,
    )

    review_path = (
        Path(evidence_review_packet_path).expanduser().resolve()
        if evidence_review_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_EVIDENCE_REVIEW_PACKET_FILENAME
    )
    if not review_path.is_file():
        built = build_resolution_hitl_evidence_review_packet_for_workspace(document=document)
        review_path = Path(built["artifacts"]["hardware_resolution_hitl_evidence_review_packet"]).resolve()
    patch_path = (
        Path(answer_patch_path).expanduser().resolve()
        if answer_patch_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_PATCH_FILENAME
    )
    if not patch_path.is_file():
        raise FileNotFoundError(
            f"Create {patch_path} before preflighting HITL answer patches. "
            "It must use schema hardware_resolution_hitl_answer_patch.v1."
        )
    report = preflight_hardware_resolution_hitl_answer_patch_against_review(
        evidence_review_packet=_read_json(review_path),
        answer_patch=_read_json(patch_path),
    )
    destination = (
        Path(output_report_path).expanduser().resolve()
        if output_report_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_PATCH_PREFLIGHT_REPORT_FILENAME
    )
    save_hardware_resolution_hitl_answer_patch_preflight_report(report, destination)
    return {
        "schema_version": "agentic_hardware_resolution_hitl_answer_patch_preflight_command.v1",
        "status": "hardware_resolution_hitl_answer_patch_preflight_written",
        "preflight_status": report.get("status"),
        "ok_to_apply_patch": report.get("ok_to_apply_patch"),
        "summary": report.get("summary", {}),
        "valid_patches": report.get("valid_patches", []),
        "invalid_patches": report.get("invalid_patches", []),
        "warning_patches": report.get("warning_patches", []),
        "source_assertions": report.get("source_assertions", []),
        "missing_rationale_pairs": report.get("missing_rationale_pairs", []),
        "next_actions": report.get("next_actions", []),
        "artifacts": {
            "hardware_resolution_hitl_evidence_review_packet": str(review_path),
            "hardware_resolution_hitl_answer_patch": str(patch_path),
            "hardware_resolution_hitl_answer_patch_preflight_report": str(destination),
        },
    }


def build_resolution_hitl_source_assertion_packet_for_workspace(
    *,
    document: Any | None = None,
    evidence_review_packet_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a reviewer work packet for remaining source-backed assertions."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_hitl_questions import (
        build_hardware_resolution_hitl_source_assertion_packet,
        save_hardware_resolution_hitl_source_assertion_packet,
    )

    review_path = (
        Path(evidence_review_packet_path).expanduser().resolve()
        if evidence_review_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_EVIDENCE_REVIEW_PACKET_FILENAME
    )
    if not review_path.is_file():
        built = build_resolution_hitl_evidence_review_packet_for_workspace(document=document)
        review_path = Path(built["artifacts"]["hardware_resolution_hitl_evidence_review_packet"]).resolve()
    packet = build_hardware_resolution_hitl_source_assertion_packet(_read_json(review_path))
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_SOURCE_ASSERTION_PACKET_FILENAME
    )
    save_hardware_resolution_hitl_source_assertion_packet(packet, destination)
    return {
        "schema_version": "agentic_hardware_resolution_hitl_source_assertion_command.v1",
        "status": "hardware_resolution_hitl_source_assertion_packet_written",
        "assertion_status": packet.get("status"),
        "summary": packet.get("summary", {}),
        "assertion_items": packet.get("assertion_items", []),
        "artifacts": {
            "hardware_resolution_hitl_evidence_review_packet": str(review_path),
            "hardware_resolution_hitl_source_assertion_packet": str(destination),
        },
    }


def build_resolution_hitl_source_assertion_response_template_for_workspace(
    *,
    document: Any | None = None,
    source_assertion_packet_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a fillable response template for source assertion review."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_hitl_questions import (
        build_hardware_resolution_hitl_source_assertion_response_template,
        save_hardware_resolution_hitl_source_assertion_response_template,
    )

    packet_path = (
        Path(source_assertion_packet_path).expanduser().resolve()
        if source_assertion_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_SOURCE_ASSERTION_PACKET_FILENAME
    )
    if not packet_path.is_file():
        built = build_resolution_hitl_source_assertion_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_hitl_source_assertion_packet"]).resolve()
    packet = _read_json(packet_path)
    template = build_hardware_resolution_hitl_source_assertion_response_template(packet)
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_SOURCE_ASSERTION_RESPONSE_TEMPLATE_FILENAME
    )
    save_hardware_resolution_hitl_source_assertion_response_template(template, destination, packet)
    return {
        "schema_version": "agentic_hardware_resolution_hitl_source_assertion_response_template_command.v1",
        "status": "hardware_resolution_hitl_source_assertion_response_template_written",
        "response_template_status": template.get("status"),
        "response_count": len(template.get("responses", [])),
        "responses": template.get("responses", []),
        "artifacts": {
            "hardware_resolution_hitl_source_assertion_packet": str(packet_path),
            "hardware_resolution_hitl_source_assertion_response_template": str(destination),
        },
    }


def build_resolution_hitl_source_assertion_disposition_report_for_workspace(
    *,
    document: Any | None = None,
    source_assertion_packet_path: str | Path | None = None,
    response_template_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a fail-closed readiness/blocker disposition report for source responses."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_hitl_questions import (
        build_hardware_resolution_hitl_source_assertion_disposition_report,
        save_hardware_resolution_hitl_source_assertion_disposition_report,
    )

    packet_path = (
        Path(source_assertion_packet_path).expanduser().resolve()
        if source_assertion_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_SOURCE_ASSERTION_PACKET_FILENAME
    )
    if not packet_path.is_file():
        built = build_resolution_hitl_source_assertion_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_hitl_source_assertion_packet"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_SOURCE_ASSERTION_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_hitl_source_assertion_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_hitl_source_assertion_response_template"]).resolve()
    report = build_hardware_resolution_hitl_source_assertion_disposition_report(
        source_assertion_packet=_read_json(packet_path),
        response_template=_read_json(response_path),
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_SOURCE_ASSERTION_DISPOSITION_REPORT_FILENAME
    )
    save_hardware_resolution_hitl_source_assertion_disposition_report(report, destination)
    return {
        "schema_version": "agentic_hardware_resolution_hitl_source_assertion_disposition_command.v1",
        "status": "hardware_resolution_hitl_source_assertion_disposition_report_written",
        "disposition_status": report.get("status"),
        "summary": report.get("summary", {}),
        "items": report.get("items", []),
        "next_actions": report.get("next_actions", []),
        "artifacts": {
            "hardware_resolution_hitl_source_assertion_packet": str(packet_path),
            "hardware_resolution_hitl_source_assertion_response_template": str(response_path),
            "hardware_resolution_hitl_source_assertion_disposition_report": str(destination),
        },
    }


def apply_resolution_hitl_source_assertion_response_for_workspace(
    *,
    document: Any | None = None,
    source_assertion_packet_path: str | Path | None = None,
    response_template_path: str | Path | None = None,
    output_report_path: str | Path | None = None,
    output_answer_patch_path: str | Path | None = None,
) -> dict[str, Any]:
    """Convert filled source assertion responses into a HITL answer patch file."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_hitl_questions import (
        apply_hardware_resolution_hitl_source_assertion_response_to_patch,
        save_hardware_resolution_hitl_source_assertion_response_apply_report,
    )

    packet_path = (
        Path(source_assertion_packet_path).expanduser().resolve()
        if source_assertion_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_SOURCE_ASSERTION_PACKET_FILENAME
    )
    if not packet_path.is_file():
        built = build_resolution_hitl_source_assertion_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_hitl_source_assertion_packet"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_SOURCE_ASSERTION_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_hitl_source_assertion_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_hitl_source_assertion_response_template"]).resolve()
    report = apply_hardware_resolution_hitl_source_assertion_response_to_patch(
        source_assertion_packet=_read_json(packet_path),
        response_template=_read_json(response_path),
    )
    report_destination = (
        Path(output_report_path).expanduser().resolve()
        if output_report_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_SOURCE_ASSERTION_RESPONSE_APPLY_REPORT_FILENAME
    )
    answer_patch_destination = (
        Path(output_answer_patch_path).expanduser().resolve()
        if output_answer_patch_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_PATCH_FILENAME
    )
    artifacts = save_hardware_resolution_hitl_source_assertion_response_apply_report(
        report,
        report_path=report_destination,
        answer_patch_path=answer_patch_destination,
    )
    return {
        "schema_version": "agentic_hardware_resolution_hitl_source_assertion_response_apply_command.v1",
        "status": "hardware_resolution_hitl_source_assertion_response_applied",
        "apply_status": report.get("status"),
        "summary": report.get("summary", {}),
        "applied_responses": report.get("applied_responses", []),
        "skipped_responses": report.get("skipped_responses", []),
        "invalid_responses": report.get("invalid_responses", []),
        "artifacts": {
            "hardware_resolution_hitl_source_assertion_packet": str(packet_path),
            "hardware_resolution_hitl_source_assertion_response_template": str(response_path),
            **artifacts,
        },
    }


def apply_resolution_hitl_answers_for_workspace(
    *,
    document: Any | None = None,
    question_packet_path: str | Path | None = None,
    answer_template_path: str | Path | None = None,
    manual_template_path: str | Path | None = None,
    output_report_path: str | Path | None = None,
    output_manual_template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Apply HITL answers to the manual completion review template."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_hitl_questions import (
        apply_hardware_resolution_hitl_answers_to_manual_completion_template,
        save_hardware_resolution_hitl_answer_apply_report,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    question_path = (
        Path(question_packet_path).expanduser().resolve()
        if question_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_QUESTION_PACKET_FILENAME
    )
    if not question_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        question_path = Path(built["artifacts"]["hardware_resolution_hitl_question_packet"]).resolve()
    answer_path = (
        Path(answer_template_path).expanduser().resolve()
        if answer_template_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_TEMPLATE_FILENAME
    )
    if not answer_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        answer_path = Path(built["artifacts"]["hardware_resolution_hitl_answer_template"]).resolve()
    manual_path = _manual_completion_template_path(context, manual_template_path)
    if not manual_path.is_file():
        built = draft_resolution_manual_completion_from_evidence_pack_for_workspace(document=document)
        manual_path = Path(built["artifacts"]["hardware_resolution_manual_completion_review_template"]).resolve()
    report = apply_hardware_resolution_hitl_answers_to_manual_completion_template(
        blocker_packet=_read_json(packet_path),
        question_packet=_read_json(question_path),
        answer_template=_read_json(answer_path),
        manual_completion_template=_read_json(manual_path),
    )
    report_destination = (
        Path(output_report_path).expanduser().resolve()
        if output_report_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_APPLY_REPORT_FILENAME
    )
    manual_destination = (
        Path(output_manual_template_path).expanduser().resolve()
        if output_manual_template_path
        else context["base_dir"] / DEFAULT_INPUT_MANUAL_COMPLETION_REVIEW_TEMPLATE_FILENAME
    )
    artifacts = save_hardware_resolution_hitl_answer_apply_report(
        report,
        report_path=report_destination,
        manual_template_path=manual_destination,
    )
    return {
        "schema_version": "agentic_hardware_resolution_hitl_answer_apply_command.v1",
        "status": "hardware_resolution_hitl_answers_applied",
        "apply_status": report.get("status"),
        "summary": report.get("summary", {}),
        "completion_readiness": report.get("completion_readiness", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_hitl_question_packet": str(question_path),
            "hardware_resolution_hitl_answer_template": str(answer_path),
            "hardware_resolution_manual_completion_review_template": str(manual_path),
            **artifacts,
        },
    }


def run_guarded_hitl_submission_for_workspace(
    *,
    document: Any | None = None,
    question_packet_path: str | Path | None = None,
    answer_template_path: str | Path | None = None,
    manual_template_path: str | Path | None = None,
    response_template_path: str | Path | None = None,
    submission_template_path: str | Path | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    """Run guarded submission after applying HITL answers."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_decisions import (
        empty_hardware_resolution_decisions,
        load_hardware_resolution_decisions,
    )
    from backend.freecad_bridge.hardware_resolution_guarded_submission import (
        run_guarded_hardware_resolution_submission_from_hitl_answers,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    question_path = (
        Path(question_packet_path).expanduser().resolve()
        if question_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_QUESTION_PACKET_FILENAME
    )
    if not question_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        question_path = Path(built["artifacts"]["hardware_resolution_hitl_question_packet"]).resolve()
    answer_path = (
        Path(answer_template_path).expanduser().resolve()
        if answer_template_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_TEMPLATE_FILENAME
    )
    if not answer_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        answer_path = Path(built["artifacts"]["hardware_resolution_hitl_answer_template"]).resolve()
    manual_path = _manual_completion_template_path(context, manual_template_path)
    if not manual_path.is_file():
        built = draft_resolution_manual_completion_from_evidence_pack_for_workspace(document=document)
        manual_path = Path(built["artifacts"]["hardware_resolution_manual_completion_review_template"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_blocker_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_blocker_response_template"]).resolve()
    submission_path = (
        Path(submission_template_path).expanduser().resolve()
        if submission_template_path
        else context["base_dir"] / DEFAULT_INPUT_TEMPLATE_FILENAME
    )
    if not submission_path.is_file():
        built = build_resolution_input_submission_template_for_workspace(document=document)
        submission_path = Path(built["artifacts"]["hardware_resolution_input_submission_template"]).resolve()
    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    decisions_path = _decisions_path(context, None)
    decisions = (
        load_hardware_resolution_decisions(decisions_path)
        if decisions_path.is_file()
        else empty_hardware_resolution_decisions()
    )
    report = run_guarded_hardware_resolution_submission_from_hitl_answers(
        blocker_packet=_read_json(packet_path),
        input_requests=_read_json(requests_path),
        question_packet=_read_json(question_path),
        answer_template=_read_json(answer_path),
        manual_completion_template=_read_json(manual_path),
        response_template=_read_json(response_path),
        submission_template=_read_json(submission_path),
        resolution_plan=_read_json(plan_path),
        decisions=decisions,
        hardware_ir=_read_json(context["base_dir"] / "assembly_hardware_ir.json"),
        assembly_layout_ir=_read_json(context["base_dir"] / "assembly_layout_ir.json"),
        base_dir=context["base_dir"],
        approved=approved,
        part_ir=_read_json(context["base_dir"] / "assembly_cad_ir.json")
        if (context["base_dir"] / "assembly_cad_ir.json").is_file() else None,
        constraint_ir=_read_json(context["base_dir"] / "assembly_constraint_validation_report.json")
        if (context["base_dir"] / "assembly_constraint_validation_report.json").is_file() else None,
    )
    return {
        "schema_version": "agentic_hardware_resolution_hitl_guarded_submission_command.v1",
        "status": "hardware_resolution_hitl_guarded_submission_written",
        "guarded_status": report.get("status"),
        "ok": report.get("ok", False),
        "summary": report.get("summary", {}),
        "next_actions": report.get("next_actions", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_input_requests": str(requests_path),
            "hardware_resolution_hitl_question_packet": str(question_path),
            "hardware_resolution_hitl_answer_template": str(answer_path),
            "hardware_resolution_manual_completion_review_template": str(manual_path),
            "hardware_resolution_blocker_response_template": str(response_path),
            "hardware_resolution_input_submission_template": str(submission_path),
            "hardware_resolution_hitl_guarded_submission_report": report.get("artifacts", {}).get(
                "hitl_guarded_submission_report"
            ),
        },
    }


def run_guarded_hitl_patch_submission_for_workspace(
    *,
    document: Any | None = None,
    question_packet_path: str | Path | None = None,
    answer_template_path: str | Path | None = None,
    answer_patch_path: str | Path | None = None,
    manual_template_path: str | Path | None = None,
    response_template_path: str | Path | None = None,
    submission_template_path: str | Path | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    """Patch HITL answers, then run guarded submission if preflight passes."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_decisions import (
        empty_hardware_resolution_decisions,
        load_hardware_resolution_decisions,
    )
    from backend.freecad_bridge.hardware_resolution_guarded_submission import (
        run_guarded_hardware_resolution_submission_from_hitl_patch,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    question_path = (
        Path(question_packet_path).expanduser().resolve()
        if question_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_QUESTION_PACKET_FILENAME
    )
    if not question_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        question_path = Path(built["artifacts"]["hardware_resolution_hitl_question_packet"]).resolve()
    answer_path = (
        Path(answer_template_path).expanduser().resolve()
        if answer_template_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_TEMPLATE_FILENAME
    )
    if not answer_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        answer_path = Path(built["artifacts"]["hardware_resolution_hitl_answer_template"]).resolve()
    patch_path = (
        Path(answer_patch_path).expanduser().resolve()
        if answer_patch_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_PATCH_FILENAME
    )
    if not patch_path.is_file():
        raise FileNotFoundError(
            f"Create {patch_path} before running guarded HITL patch submission. "
            "It must use schema hardware_resolution_hitl_answer_patch.v1."
        )
    manual_path = _manual_completion_template_path(context, manual_template_path)
    if not manual_path.is_file():
        built = draft_resolution_manual_completion_from_evidence_pack_for_workspace(document=document)
        manual_path = Path(built["artifacts"]["hardware_resolution_manual_completion_review_template"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_blocker_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_blocker_response_template"]).resolve()
    submission_path = (
        Path(submission_template_path).expanduser().resolve()
        if submission_template_path
        else context["base_dir"] / DEFAULT_INPUT_TEMPLATE_FILENAME
    )
    if not submission_path.is_file():
        built = build_resolution_input_submission_template_for_workspace(document=document)
        submission_path = Path(built["artifacts"]["hardware_resolution_input_submission_template"]).resolve()
    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    decisions_path = _decisions_path(context, None)
    decisions = (
        load_hardware_resolution_decisions(decisions_path)
        if decisions_path.is_file()
        else empty_hardware_resolution_decisions()
    )
    report = run_guarded_hardware_resolution_submission_from_hitl_patch(
        blocker_packet=_read_json(packet_path),
        input_requests=_read_json(requests_path),
        question_packet=_read_json(question_path),
        answer_template=_read_json(answer_path),
        answer_patch=_read_json(patch_path),
        manual_completion_template=_read_json(manual_path),
        response_template=_read_json(response_path),
        submission_template=_read_json(submission_path),
        resolution_plan=_read_json(plan_path),
        decisions=decisions,
        hardware_ir=_read_json(context["base_dir"] / "assembly_hardware_ir.json"),
        assembly_layout_ir=_read_json(context["base_dir"] / "assembly_layout_ir.json"),
        base_dir=context["base_dir"],
        approved=approved,
        part_ir=_read_json(context["base_dir"] / "assembly_cad_ir.json")
        if (context["base_dir"] / "assembly_cad_ir.json").is_file() else None,
        constraint_ir=_read_json(context["base_dir"] / "assembly_constraint_validation_report.json")
        if (context["base_dir"] / "assembly_constraint_validation_report.json").is_file() else None,
    )
    return {
        "schema_version": "agentic_hardware_resolution_hitl_patch_guarded_submission_command.v1",
        "status": "hardware_resolution_hitl_patch_guarded_submission_written",
        "guarded_status": report.get("status"),
        "ok": report.get("ok", False),
        "summary": report.get("summary", {}),
        "next_actions": report.get("next_actions", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_input_requests": str(requests_path),
            "hardware_resolution_hitl_question_packet": str(question_path),
            "hardware_resolution_hitl_answer_template": str(answer_path),
            "hardware_resolution_hitl_answer_patch": str(patch_path),
            "hardware_resolution_manual_completion_review_template": str(manual_path),
            "hardware_resolution_blocker_response_template": str(response_path),
            "hardware_resolution_input_submission_template": str(submission_path),
            "hardware_resolution_hitl_patch_guarded_submission_report": report.get("artifacts", {}).get(
                "hitl_patch_guarded_submission_report"
            ),
        },
    }


def run_guarded_hitl_source_response_submission_for_workspace(
    *,
    document: Any | None = None,
    question_packet_path: str | Path | None = None,
    answer_template_path: str | Path | None = None,
    source_assertion_packet_path: str | Path | None = None,
    source_response_template_path: str | Path | None = None,
    manual_template_path: str | Path | None = None,
    response_template_path: str | Path | None = None,
    submission_template_path: str | Path | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    """Apply source assertion responses and then run guarded HITL patch submission if safe."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_decisions import (
        empty_hardware_resolution_decisions,
        load_hardware_resolution_decisions,
    )
    from backend.freecad_bridge.hardware_resolution_guarded_submission import (
        run_guarded_hardware_resolution_submission_from_source_assertion_response,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    question_path = (
        Path(question_packet_path).expanduser().resolve()
        if question_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_QUESTION_PACKET_FILENAME
    )
    if not question_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        question_path = Path(built["artifacts"]["hardware_resolution_hitl_question_packet"]).resolve()
    answer_path = (
        Path(answer_template_path).expanduser().resolve()
        if answer_template_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_ANSWER_TEMPLATE_FILENAME
    )
    if not answer_path.is_file():
        built = build_resolution_hitl_question_packet_for_workspace(document=document)
        answer_path = Path(built["artifacts"]["hardware_resolution_hitl_answer_template"]).resolve()
    source_packet_path = (
        Path(source_assertion_packet_path).expanduser().resolve()
        if source_assertion_packet_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_SOURCE_ASSERTION_PACKET_FILENAME
    )
    if not source_packet_path.is_file():
        built = build_resolution_hitl_source_assertion_packet_for_workspace(document=document)
        source_packet_path = Path(built["artifacts"]["hardware_resolution_hitl_source_assertion_packet"]).resolve()
    source_response_path = (
        Path(source_response_template_path).expanduser().resolve()
        if source_response_template_path
        else context["base_dir"] / DEFAULT_INPUT_HITL_SOURCE_ASSERTION_RESPONSE_TEMPLATE_FILENAME
    )
    if not source_response_path.is_file():
        built = build_resolution_hitl_source_assertion_response_template_for_workspace(document=document)
        source_response_path = Path(
            built["artifacts"]["hardware_resolution_hitl_source_assertion_response_template"]
        ).resolve()
    manual_path = _manual_completion_template_path(context, manual_template_path)
    if not manual_path.is_file():
        built = draft_resolution_manual_completion_from_evidence_pack_for_workspace(document=document)
        manual_path = Path(built["artifacts"]["hardware_resolution_manual_completion_review_template"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_blocker_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_blocker_response_template"]).resolve()
    submission_path = (
        Path(submission_template_path).expanduser().resolve()
        if submission_template_path
        else context["base_dir"] / DEFAULT_INPUT_TEMPLATE_FILENAME
    )
    if not submission_path.is_file():
        built = build_resolution_input_submission_template_for_workspace(document=document)
        submission_path = Path(built["artifacts"]["hardware_resolution_input_submission_template"]).resolve()
    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    decisions_path = _decisions_path(context, None)
    decisions = (
        load_hardware_resolution_decisions(decisions_path)
        if decisions_path.is_file()
        else empty_hardware_resolution_decisions()
    )
    report = run_guarded_hardware_resolution_submission_from_source_assertion_response(
        blocker_packet=_read_json(packet_path),
        input_requests=_read_json(requests_path),
        question_packet=_read_json(question_path),
        answer_template=_read_json(answer_path),
        source_assertion_packet=_read_json(source_packet_path),
        source_assertion_response_template=_read_json(source_response_path),
        manual_completion_template=_read_json(manual_path),
        response_template=_read_json(response_path),
        submission_template=_read_json(submission_path),
        resolution_plan=_read_json(plan_path),
        decisions=decisions,
        hardware_ir=_read_json(context["base_dir"] / "assembly_hardware_ir.json"),
        assembly_layout_ir=_read_json(context["base_dir"] / "assembly_layout_ir.json"),
        base_dir=context["base_dir"],
        approved=approved,
        part_ir=_read_json(context["base_dir"] / "assembly_cad_ir.json")
        if (context["base_dir"] / "assembly_cad_ir.json").is_file() else None,
        constraint_ir=_read_json(context["base_dir"] / "assembly_constraint_validation_report.json")
        if (context["base_dir"] / "assembly_constraint_validation_report.json").is_file() else None,
    )
    return {
        "schema_version": "agentic_hardware_resolution_hitl_source_response_guarded_submission_command.v1",
        "status": "hardware_resolution_hitl_source_response_guarded_submission_written",
        "guarded_status": report.get("status"),
        "ok": report.get("ok", False),
        "summary": report.get("summary", {}),
        "next_actions": report.get("next_actions", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_input_requests": str(requests_path),
            "hardware_resolution_hitl_question_packet": str(question_path),
            "hardware_resolution_hitl_answer_template": str(answer_path),
            "hardware_resolution_hitl_source_assertion_packet": str(source_packet_path),
            "hardware_resolution_hitl_source_assertion_response_template": str(source_response_path),
            "hardware_resolution_manual_completion_review_template": str(manual_path),
            "hardware_resolution_blocker_response_template": str(response_path),
            "hardware_resolution_input_submission_template": str(submission_path),
            "hardware_resolution_hitl_source_response_guarded_submission_report": report.get("artifacts", {}).get(
                "hitl_source_response_guarded_submission_report"
            ),
        },
    }


def build_resolution_answer_selection_template_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write a fillable selection template from current answer candidates."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_answer_selection import (
        build_hardware_resolution_answer_selection_template,
        save_hardware_resolution_answer_selection_template,
    )

    candidates_path = context["base_dir"] / DEFAULT_INPUT_ANSWER_CANDIDATES_FILENAME
    if not candidates_path.is_file():
        built = build_resolution_answer_candidates_for_workspace(document=document)
        candidates_path = Path(built["artifacts"]["hardware_resolution_answer_candidates"]).resolve()
    template = build_hardware_resolution_answer_selection_template(_read_json(candidates_path))
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_ANSWER_SELECTION_TEMPLATE_FILENAME
    )
    save_hardware_resolution_answer_selection_template(template, destination)
    return {
        "schema_version": "agentic_hardware_resolution_answer_selection_command.v1",
        "status": "hardware_resolution_answer_selection_template_written",
        "selection_status": template.get("status"),
        "selection_count": len(template.get("selections", [])),
        "artifacts": {
            "hardware_resolution_answer_candidates": str(candidates_path),
            "hardware_resolution_answer_selection_template": str(destination),
        },
    }


def apply_resolution_answer_selection_for_workspace(
    *,
    document: Any | None = None,
    selection_template_path: str | Path | None = None,
    response_template_path: str | Path | None = None,
    output_report_path: str | Path | None = None,
    output_response_template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Copy selected answer candidates into the blocker response template."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_answer_selection import (
        apply_hardware_resolution_answer_selection_to_blocker_response_template,
        save_hardware_resolution_answer_selection_apply_report,
    )

    candidates_path = context["base_dir"] / DEFAULT_INPUT_ANSWER_CANDIDATES_FILENAME
    if not candidates_path.is_file():
        built = build_resolution_answer_candidates_for_workspace(document=document)
        candidates_path = Path(built["artifacts"]["hardware_resolution_answer_candidates"]).resolve()
    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    selection_path = (
        Path(selection_template_path).expanduser().resolve()
        if selection_template_path
        else context["base_dir"] / DEFAULT_INPUT_ANSWER_SELECTION_TEMPLATE_FILENAME
    )
    if not selection_path.is_file():
        built = build_resolution_answer_selection_template_for_workspace(document=document)
        selection_path = Path(built["artifacts"]["hardware_resolution_answer_selection_template"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_blocker_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_blocker_response_template"]).resolve()
    report = apply_hardware_resolution_answer_selection_to_blocker_response_template(
        answer_candidates=_read_json(candidates_path),
        blocker_packet=_read_json(packet_path),
        selection_template=_read_json(selection_path),
        response_template=_read_json(response_path),
    )
    report_destination = (
        Path(output_report_path).expanduser().resolve()
        if output_report_path
        else context["base_dir"] / DEFAULT_INPUT_ANSWER_SELECTION_APPLY_REPORT_FILENAME
    )
    response_destination = (
        Path(output_response_template_path).expanduser().resolve()
        if output_response_template_path
        else response_path
    )
    artifacts = save_hardware_resolution_answer_selection_apply_report(
        report,
        report_path=report_destination,
        response_template_path=response_destination,
    )
    return {
        "schema_version": "agentic_hardware_resolution_answer_selection_command.v1",
        "status": "hardware_resolution_answer_selection_applied",
        "apply_status": report.get("status"),
        "summary": report.get("summary", {}),
        "applied_selections": report.get("applied_selections", []),
        "invalid_selections": report.get("invalid_selections", []),
        "artifacts": {
            "hardware_resolution_answer_candidates": str(candidates_path),
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_answer_selection_template": str(selection_path),
            **artifacts,
        },
    }


def preflight_resolution_answer_selection_for_workspace(
    *,
    document: Any | None = None,
    selection_template_path: str | Path | None = None,
    response_template_path: str | Path | None = None,
    submission_template_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Preflight selected answer candidates through submission validation."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_answer_preflight import (
        preflight_hardware_resolution_answer_selection,
        save_hardware_resolution_answer_preflight_report,
    )

    candidates_path = context["base_dir"] / DEFAULT_INPUT_ANSWER_CANDIDATES_FILENAME
    if not candidates_path.is_file():
        built = build_resolution_answer_candidates_for_workspace(document=document)
        candidates_path = Path(built["artifacts"]["hardware_resolution_answer_candidates"]).resolve()
    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    selection_path = (
        Path(selection_template_path).expanduser().resolve()
        if selection_template_path
        else context["base_dir"] / DEFAULT_INPUT_ANSWER_SELECTION_TEMPLATE_FILENAME
    )
    if not selection_path.is_file():
        built = build_resolution_answer_selection_template_for_workspace(document=document)
        selection_path = Path(built["artifacts"]["hardware_resolution_answer_selection_template"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_blocker_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_blocker_response_template"]).resolve()
    submission_path = (
        Path(submission_template_path).expanduser().resolve()
        if submission_template_path
        else context["base_dir"] / DEFAULT_INPUT_TEMPLATE_FILENAME
    )
    if not submission_path.is_file():
        built = build_resolution_input_submission_template_for_workspace(document=document)
        submission_path = Path(built["artifacts"]["hardware_resolution_input_submission_template"]).resolve()
    report = preflight_hardware_resolution_answer_selection(
        answer_candidates=_read_json(candidates_path),
        blocker_packet=_read_json(packet_path),
        input_requests=_read_json(requests_path),
        selection_template=_read_json(selection_path),
        response_template=_read_json(response_path),
        submission_template=_read_json(submission_path),
    )
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_ANSWER_PREFLIGHT_REPORT_FILENAME
    )
    save_hardware_resolution_answer_preflight_report(report, destination)
    return {
        "schema_version": "agentic_hardware_resolution_answer_preflight_command.v1",
        "status": "hardware_resolution_answer_preflight_written",
        "preflight_status": report.get("status"),
        "ok_to_submit": report.get("ok_to_submit", False),
        "summary": report.get("summary", {}),
        "next_actions": report.get("next_actions", []),
        "artifacts": {
            "hardware_resolution_answer_candidates": str(candidates_path),
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_input_requests": str(requests_path),
            "hardware_resolution_answer_selection_template": str(selection_path),
            "hardware_resolution_blocker_response_template": str(response_path),
            "hardware_resolution_input_submission_template": str(submission_path),
            "hardware_resolution_answer_preflight_report": str(destination),
        },
    }


def run_guarded_resolution_submission_for_workspace(
    *,
    document: Any | None = None,
    selection_template_path: str | Path | None = None,
    response_template_path: str | Path | None = None,
    submission_template_path: str | Path | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    """Run guarded submission only when answer preflight is ready."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_decisions import (
        empty_hardware_resolution_decisions,
        load_hardware_resolution_decisions,
    )
    from backend.freecad_bridge.hardware_resolution_guarded_submission import (
        run_guarded_hardware_resolution_submission_from_answer_selection,
    )

    candidates_path = context["base_dir"] / DEFAULT_INPUT_ANSWER_CANDIDATES_FILENAME
    if not candidates_path.is_file():
        built = build_resolution_answer_candidates_for_workspace(document=document)
        candidates_path = Path(built["artifacts"]["hardware_resolution_answer_candidates"]).resolve()
    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    selection_path = (
        Path(selection_template_path).expanduser().resolve()
        if selection_template_path
        else context["base_dir"] / DEFAULT_INPUT_ANSWER_SELECTION_TEMPLATE_FILENAME
    )
    if not selection_path.is_file():
        built = build_resolution_answer_selection_template_for_workspace(document=document)
        selection_path = Path(built["artifacts"]["hardware_resolution_answer_selection_template"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_blocker_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_blocker_response_template"]).resolve()
    submission_path = (
        Path(submission_template_path).expanduser().resolve()
        if submission_template_path
        else context["base_dir"] / DEFAULT_INPUT_TEMPLATE_FILENAME
    )
    if not submission_path.is_file():
        built = build_resolution_input_submission_template_for_workspace(document=document)
        submission_path = Path(built["artifacts"]["hardware_resolution_input_submission_template"]).resolve()
    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    decisions_path = _decisions_path(context, None)
    decisions = (
        load_hardware_resolution_decisions(decisions_path)
        if decisions_path.is_file()
        else empty_hardware_resolution_decisions()
    )
    cad_root = context["base_dir"].parent
    report = run_guarded_hardware_resolution_submission_from_answer_selection(
        answer_candidates=_read_json(candidates_path),
        blocker_packet=_read_json(packet_path),
        input_requests=_read_json(requests_path),
        selection_template=_read_json(selection_path),
        response_template=_read_json(response_path),
        submission_template=_read_json(submission_path),
        resolution_plan=_read_json(plan_path),
        decisions=decisions,
        hardware_ir=_read_json(context["base_dir"] / "assembly_hardware_ir.json"),
        assembly_layout_ir=_read_json(context["base_dir"] / "assembly_layout_ir.json"),
        base_dir=context["base_dir"],
        approved=approved,
        part_ir=_read_json(context["base_dir"] / "assembly_cad_ir.json")
        if (context["base_dir"] / "assembly_cad_ir.json").is_file() else None,
        constraint_ir=_read_json(context["base_dir"] / "assembly_constraint_ir.json")
        if (context["base_dir"] / "assembly_constraint_ir.json").is_file() else None,
        part_model_path=_first_existing(cad_root, "*/custom_part_library.FCStd"),
        part_manifest_path=_first_existing(cad_root, "*/custom_part_manifest.json"),
        hardware_model_path=_first_existing(cad_root, "*/hardware_library.FCStd"),
        hardware_manifest_path=_first_existing(cad_root, "*/hardware_library_manifest.json"),
    )
    return {
        "schema_version": "agentic_hardware_resolution_guarded_submission_command.v1",
        "status": "hardware_resolution_guarded_submission_written",
        "guarded_status": report.get("status"),
        "ok": report.get("ok", False),
        "summary": report.get("summary", {}),
        "next_actions": report.get("next_actions", []),
        "artifacts": {
            "hardware_resolution_answer_candidates": str(candidates_path),
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_input_requests": str(requests_path),
            "hardware_resolution_answer_selection_template": str(selection_path),
            "hardware_resolution_blocker_response_template": str(response_path),
            "hardware_resolution_input_submission_template": str(submission_path),
            "hardware_resolution_plan": str(plan_path),
            "hardware_resolution_decisions": str(decisions_path) if decisions_path.is_file() else None,
            **report.get("artifacts", {}),
        },
    }


def run_guarded_manual_completion_submission_for_workspace(
    *,
    document: Any | None = None,
    manual_template_path: str | Path | None = None,
    response_template_path: str | Path | None = None,
    submission_template_path: str | Path | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    """Run guarded submission only when manual-completion preflight is ready."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_decisions import (
        empty_hardware_resolution_decisions,
        load_hardware_resolution_decisions,
    )
    from backend.freecad_bridge.hardware_resolution_guarded_submission import (
        run_guarded_hardware_resolution_submission_from_manual_completion,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    manual_path = _manual_completion_template_path(context, manual_template_path)
    if not manual_path.is_file():
        built = build_resolution_manual_completion_template_for_workspace(document=document)
        manual_path = Path(built["artifacts"]["hardware_resolution_manual_completion_template"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_blocker_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_blocker_response_template"]).resolve()
    submission_path = (
        Path(submission_template_path).expanduser().resolve()
        if submission_template_path
        else context["base_dir"] / DEFAULT_INPUT_TEMPLATE_FILENAME
    )
    if not submission_path.is_file():
        built = build_resolution_input_submission_template_for_workspace(document=document)
        submission_path = Path(built["artifacts"]["hardware_resolution_input_submission_template"]).resolve()
    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    decisions_path = _decisions_path(context, None)
    decisions = (
        load_hardware_resolution_decisions(decisions_path)
        if decisions_path.is_file()
        else empty_hardware_resolution_decisions()
    )
    cad_root = context["base_dir"].parent
    report = run_guarded_hardware_resolution_submission_from_manual_completion(
        blocker_packet=_read_json(packet_path),
        input_requests=_read_json(requests_path),
        manual_completion_template=_read_json(manual_path),
        response_template=_read_json(response_path),
        submission_template=_read_json(submission_path),
        resolution_plan=_read_json(plan_path),
        decisions=decisions,
        hardware_ir=_read_json(context["base_dir"] / "assembly_hardware_ir.json"),
        assembly_layout_ir=_read_json(context["base_dir"] / "assembly_layout_ir.json"),
        base_dir=context["base_dir"],
        approved=approved,
        part_ir=_read_json(context["base_dir"] / "assembly_cad_ir.json")
        if (context["base_dir"] / "assembly_cad_ir.json").is_file() else None,
        constraint_ir=_read_json(context["base_dir"] / "assembly_constraint_ir.json")
        if (context["base_dir"] / "assembly_constraint_ir.json").is_file() else None,
        part_model_path=_first_existing(cad_root, "*/custom_part_library.FCStd"),
        part_manifest_path=_first_existing(cad_root, "*/custom_part_manifest.json"),
        hardware_model_path=_first_existing(cad_root, "*/hardware_library.FCStd"),
        hardware_manifest_path=_first_existing(cad_root, "*/hardware_library_manifest.json"),
    )
    return {
        "schema_version": "agentic_hardware_resolution_manual_guarded_submission_command.v1",
        "status": "hardware_resolution_manual_guarded_submission_written",
        "guarded_status": report.get("status"),
        "ok": report.get("ok", False),
        "summary": report.get("summary", {}),
        "next_actions": report.get("next_actions", []),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_input_requests": str(requests_path),
            "hardware_resolution_manual_completion_template": str(manual_path),
            "hardware_resolution_blocker_response_template": str(response_path),
            "hardware_resolution_input_submission_template": str(submission_path),
            "hardware_resolution_plan": str(plan_path),
            "hardware_resolution_decisions": str(decisions_path) if decisions_path.is_file() else None,
            **report.get("artifacts", {}),
        },
    }


def apply_resolution_blocker_responses_for_workspace(
    *,
    document: Any | None = None,
    response_template_path: str | Path | None = None,
    submission_template_path: str | Path | None = None,
    output_report_path: str | Path | None = None,
    output_submission_template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Apply filled blocker responses to the pending submission template."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_blocker_response import (
        apply_hardware_resolution_blocker_responses_to_submission_template,
        save_hardware_resolution_blocker_response_apply_report,
    )

    packet_path = context["base_dir"] / DEFAULT_INPUT_BLOCKER_PACKET_FILENAME
    if not packet_path.is_file():
        built = build_resolution_blocker_packet_for_workspace(document=document)
        packet_path = Path(built["artifacts"]["hardware_resolution_blocker_packet"]).resolve()
    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    response_path = (
        Path(response_template_path).expanduser().resolve()
        if response_template_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_TEMPLATE_FILENAME
    )
    if not response_path.is_file():
        built = build_resolution_blocker_response_template_for_workspace(document=document)
        response_path = Path(built["artifacts"]["hardware_resolution_blocker_response_template"]).resolve()
    submission_path = (
        Path(submission_template_path).expanduser().resolve()
        if submission_template_path
        else context["base_dir"] / DEFAULT_INPUT_TEMPLATE_FILENAME
    )
    if not submission_path.is_file():
        built = build_resolution_input_submission_template_for_workspace(document=document)
        submission_path = Path(built["artifacts"]["hardware_resolution_input_submission_template"]).resolve()
    report = apply_hardware_resolution_blocker_responses_to_submission_template(
        blocker_packet=_read_json(packet_path),
        input_requests=_read_json(requests_path),
        response_template=_read_json(response_path),
        submission_template=_read_json(submission_path),
    )
    report_destination = (
        Path(output_report_path).expanduser().resolve()
        if output_report_path
        else context["base_dir"] / DEFAULT_INPUT_BLOCKER_RESPONSE_APPLY_REPORT_FILENAME
    )
    submission_destination = (
        Path(output_submission_template_path).expanduser().resolve()
        if output_submission_template_path
        else submission_path
    )
    artifacts = save_hardware_resolution_blocker_response_apply_report(
        report,
        report_path=report_destination,
        submission_template_path=submission_destination,
    )
    return {
        "schema_version": "agentic_hardware_resolution_blocker_response_command.v1",
        "status": "hardware_resolution_blocker_responses_applied",
        "apply_status": report.get("status"),
        "summary": report.get("summary", {}),
        "submission_validation": report.get("submission_validation", {}),
        "artifacts": {
            "hardware_resolution_blocker_packet": str(packet_path),
            "hardware_resolution_blocker_response_template": str(response_path),
            **artifacts,
        },
    }


def build_resolution_input_confirmation_requests_for_workspace(
    *,
    document: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write explicit human-confirmation requests for draft candidates."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_input_confirmation import (
        build_hardware_resolution_input_confirmation_requests,
        save_hardware_resolution_input_confirmation_requests,
    )

    draft_path = context["base_dir"] / DEFAULT_INPUT_DRAFT_REPORT_FILENAME
    if not draft_path.is_file():
        built = build_resolution_input_drafts_for_workspace(document=document)
        draft_path = Path(built["artifacts"]["hardware_resolution_input_draft_report"]).resolve()
    report = build_hardware_resolution_input_confirmation_requests(_read_json(draft_path))
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_INPUT_CONFIRMATION_REQUESTS_FILENAME
    )
    save_hardware_resolution_input_confirmation_requests(report, destination)
    return {
        "schema_version": "agentic_hardware_resolution_input_confirmation_command.v1",
        "status": "hardware_resolution_input_confirmation_requests_written",
        "confirmation_status": report.get("status"),
        "summary": report.get("summary", {}),
        "requests": report.get("requests", []),
        "artifacts": {
            "hardware_resolution_input_draft_report": str(draft_path),
            "hardware_resolution_input_confirmation_requests": str(destination),
        },
    }


def confirm_resolution_input_candidate_for_workspace(
    *,
    document: Any | None = None,
    request_id: str | None = None,
    candidate_id: str | None = None,
    reviewer: str = "freecad-ui",
    output_report_path: str | Path | None = None,
    output_template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Fill a submission template only after an explicit candidate confirmation."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_input_confirmation import (
        DECISIONS_SCHEMA_VERSION,
        apply_hardware_resolution_input_confirmation_decisions,
        build_hardware_resolution_input_confirmation_requests,
        save_hardware_resolution_input_confirmation_report,
        save_hardware_resolution_input_confirmation_requests,
        save_hardware_resolution_input_confirmation_template,
    )

    draft_path = context["base_dir"] / DEFAULT_INPUT_DRAFT_REPORT_FILENAME
    if not draft_path.is_file():
        built = build_resolution_input_drafts_for_workspace(document=document)
        draft_path = Path(built["artifacts"]["hardware_resolution_input_draft_report"]).resolve()
    draft = _read_json(draft_path)
    requests = build_hardware_resolution_input_confirmation_requests(draft)
    requests_path = context["base_dir"] / DEFAULT_INPUT_CONFIRMATION_REQUESTS_FILENAME
    save_hardware_resolution_input_confirmation_requests(requests, requests_path)
    selected = _select_confirmation_candidate(requests, request_id=request_id, candidate_id=candidate_id)
    decisions = {
        "schema_version": DECISIONS_SCHEMA_VERSION,
        "decisions": [{
            "request_id": selected["request_id"],
            "candidate_id": selected["candidate_id"],
            "decision": "confirm",
            "reviewer": reviewer,
        }],
    }
    report = apply_hardware_resolution_input_confirmation_decisions(
        draft_report=draft,
        confirmation_decisions=decisions,
    )
    report_destination = (
        Path(output_report_path).expanduser().resolve()
        if output_report_path
        else context["base_dir"] / DEFAULT_INPUT_CONFIRMATION_REPORT_FILENAME
    )
    template_destination = (
        Path(output_template_path).expanduser().resolve()
        if output_template_path
        else context["base_dir"] / DEFAULT_INPUT_CONFIRMED_TEMPLATE_FILENAME
    )
    save_hardware_resolution_input_confirmation_report(report, report_destination)
    save_hardware_resolution_input_confirmation_template(report, template_destination)
    return {
        "schema_version": "agentic_hardware_resolution_input_confirmation_command.v1",
        "status": "hardware_resolution_input_confirmation_applied",
        "confirmation_status": report.get("status"),
        "summary": report.get("summary", {}),
        "selected": selected,
        "artifacts": {
            "hardware_resolution_input_draft_report": str(draft_path),
            "hardware_resolution_input_confirmation_requests": str(requests_path),
            "hardware_resolution_input_confirmation_report": str(report_destination),
            "hardware_resolution_input_confirmed_template": str(template_destination),
        },
    }


def submit_confirmed_resolution_input_template_for_workspace(
    *,
    document: Any | None = None,
    reviewer: str = "freecad-ui",
    rationale: str | None = None,
    validate_only: bool = False,
    require_all_valid: bool = False,
) -> dict[str, Any]:
    """Submit the template produced by an explicit confirmation step."""
    context = resolve_fastener_context(document=document)
    confirmed_template = context["base_dir"] / DEFAULT_INPUT_CONFIRMED_TEMPLATE_FILENAME
    if not confirmed_template.is_file():
        raise FileNotFoundError(
            "confirmed input template is missing; run Confirm Input Candidate first"
        )
    return submit_resolution_input_template_for_workspace(
        document=document,
        template_path=confirmed_template,
        reviewer=reviewer,
        rationale=rationale,
        validate_only=validate_only,
        require_all_valid=require_all_valid,
    )


def record_resolution_input_submission_for_workspace(
    *,
    submission: dict[str, Any],
    document: Any | None = None,
    reviewer: str = "freecad-ui",
    rationale: str | None = None,
) -> dict[str, Any]:
    """Validate one filled input request and record it as a resolution decision."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_decisions import (
        load_hardware_resolution_decisions,
        save_hardware_resolution_decisions,
    )
    from backend.freecad_bridge.hardware_resolution_input_submission import (
        record_hardware_resolution_input_submission,
    )

    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    requests_path = _input_requests_path(context)
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    decisions_path = _decisions_path(context, None)
    report = record_hardware_resolution_input_submission(
        _read_json(plan_path),
        _read_json(requests_path),
        load_hardware_resolution_decisions(decisions_path),
        submission,
        reviewer=reviewer,
        rationale=rationale,
    )
    save_hardware_resolution_decisions(report["decisions"], decisions_path)
    return {
        "schema_version": "agentic_hardware_resolution_input_command.v1",
        "status": "hardware_resolution_input_submission_recorded",
        "decision": report.get("decision"),
        "decision_report": report.get("decision_report"),
        "artifacts": {
            "hardware_resolution_plan": str(plan_path),
            "hardware_resolution_input_requests": str(requests_path),
            "hardware_resolution_decisions": str(decisions_path),
        },
    }


def submit_resolution_input_template_for_workspace(
    *,
    document: Any | None = None,
    template_path: str | Path | None = None,
    reviewer: str = "freecad-ui",
    rationale: str | None = None,
    validate_only: bool = False,
    require_all_valid: bool = False,
) -> dict[str, Any]:
    """Validate or record all filled submissions from a template file."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_decisions import (
        load_hardware_resolution_decisions,
        save_hardware_resolution_decisions,
    )
    from backend.freecad_bridge.hardware_resolution_input_submission import (
        record_hardware_resolution_input_submission_template,
        validate_hardware_resolution_input_submission_template,
    )

    plan_path = _resolution_plan_path(context)
    requests_path = _input_requests_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    if not requests_path.is_file():
        built = build_resolution_input_requests_for_workspace(document=document)
        requests_path = Path(built["artifacts"]["hardware_resolution_input_requests"]).resolve()
    resolved_template_path = (
        Path(template_path).expanduser().resolve()
        if template_path
        else context["base_dir"] / DEFAULT_INPUT_TEMPLATE_FILENAME
    )
    if not resolved_template_path.is_file():
        built = build_resolution_input_submission_template_for_workspace(document=document)
        resolved_template_path = Path(built["artifacts"]["hardware_resolution_input_submission_template"]).resolve()
    validation = validate_hardware_resolution_input_submission_template(
        _read_json(resolved_template_path),
        _read_json(requests_path),
    )
    if validate_only:
        return {
            "schema_version": "agentic_hardware_resolution_input_command.v1",
            "status": "hardware_resolution_input_template_validated",
            "validation": validation,
            "artifacts": {
                "hardware_resolution_input_submission_template": str(resolved_template_path),
            },
        }
    decisions_path = _decisions_path(context, None)
    report = record_hardware_resolution_input_submission_template(
        _read_json(plan_path),
        _read_json(requests_path),
        load_hardware_resolution_decisions(decisions_path),
        _read_json(resolved_template_path),
        reviewer=reviewer,
        rationale=rationale,
        require_all_valid=require_all_valid,
    )
    save_hardware_resolution_decisions(report["decisions"], decisions_path)
    return {
        "schema_version": "agentic_hardware_resolution_input_command.v1",
        "status": "hardware_resolution_input_template_submitted",
        "recorded_count": report.get("recorded_count", 0),
        "validation": report.get("validation"),
        "decision_report": report.get("decision_report"),
        "artifacts": {
            "hardware_resolution_input_submission_template": str(resolved_template_path),
            "hardware_resolution_decisions": str(decisions_path),
        },
    }


def record_resolution_decision_for_workspace(
    *,
    document: Any | None = None,
    action_id: str | None = None,
    decision_action: str = "defer",
    evidence_refs: list[dict[str, Any]] | None = None,
    spec_patch: dict[str, Any] | None = None,
    decisions_path: str | Path | None = None,
    reviewer: str = "freecad-ui",
    rationale: str | None = None,
) -> dict[str, Any]:
    """Record one decision against the active hardware resolution plan."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_decisions import (
        apply_hardware_resolution_decisions,
        load_hardware_resolution_decisions,
        make_hardware_resolution_decision,
        save_hardware_resolution_decisions,
        upsert_hardware_resolution_decision,
    )

    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    plan = _read_json(plan_path)
    action = _select_action(
        plan,
        action_id,
        recommended_action="reject_or_add_evidence" if decision_action == "confirm_reject" else None,
    )
    destination = _decisions_path(context, decisions_path)
    decisions = load_hardware_resolution_decisions(destination)
    decision = make_hardware_resolution_decision(
        action,
        decision_action,
        reviewer=reviewer,
        rationale=rationale,
        evidence_refs=evidence_refs,
        spec_patch=spec_patch,
    )
    updated = upsert_hardware_resolution_decision(decisions, decision)
    save_hardware_resolution_decisions(updated, destination)
    decision_report = apply_hardware_resolution_decisions(plan, updated)
    return {
        "schema_version": "agentic_hardware_resolution_decision_command.v1",
        "status": "recorded",
        "decision": decision,
        "decision_count": len(updated["decisions"]),
        "decision_report": decision_report,
        "artifacts": {
            "hardware_resolution_plan": str(plan_path),
            "hardware_resolution_decisions": str(destination),
        },
    }


def export_fastener_reject_decisions_for_workspace(
    *,
    document: Any | None = None,
    action_id: str | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Export reject decisions for all current fastener human-review items."""
    context = resolve_fastener_context(document=document)
    _ensure_repo_import(context["repo_root"])
    from backend.freecad_bridge.hardware_resolution_decisions import (
        build_fastener_reject_decisions_for_resolution_action,
    )

    plan_path = _resolution_plan_path(context)
    if not plan_path.is_file():
        built = build_hardware_resolution_plan_for_workspace(document=document)
        plan_path = Path(built["artifacts"]["hardware_resolution_plan"]).resolve()
    review_path = _review_plan_path(context)
    if review_path is None or not review_path.is_file():
        raise FileNotFoundError("human review plan is required to export fastener reject decisions")
    plan = _read_json(plan_path)
    selected_action = _select_action(plan, action_id, recommended_action="reject_or_add_evidence")
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else context["base_dir"] / DEFAULT_FASTENER_REJECT_FILENAME
    )
    fastener_decisions = build_fastener_reject_decisions_for_resolution_action(
        plan,
        _read_json(review_path),
        selected_action["action_id"],
    )
    _write_json(destination, fastener_decisions)
    return {
        "schema_version": "agentic_hardware_resolution_decision_command.v1",
        "status": "fastener_reject_decisions_written",
        "decision_count": len(fastener_decisions.get("decisions", [])),
        "action_id": selected_action["action_id"],
        "artifacts": {
            "hardware_resolution_plan": str(plan_path),
            "human_review_plan": str(review_path),
            "fastener_human_review_decisions": str(destination),
        },
    }


def format_resolution_decision_summary(report: dict[str, Any]) -> str:
    decision = report.get("decision", {})
    decision_report = report.get("decision_report", {})
    summary = decision_report.get("summary", {})
    return (
        "Hardware resolution decision: "
        f"{decision.get('action_id', report.get('action_id', 'unknown'))}="
        f"{decision.get('action', report.get('status', 'unknown'))}, "
        f"ready={summary.get('ready_for_pipeline_count', 0)}, "
        f"pending={summary.get('pending_count', 0)}"
    )


def format_fastener_reject_export_summary(report: dict[str, Any]) -> str:
    return (
        "Fastener reject decisions exported: "
        f"{report.get('decision_count', 0)} decisions -> "
        f"{report.get('artifacts', {}).get('fastener_human_review_decisions')}"
    )


def format_resolution_status_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware resolution status: "
        f"{report.get('report_status', 'unknown')}, "
        f"ready={summary.get('ready_for_pipeline_count', 0)}, "
        f"pending={summary.get('pending_count', 0)}, "
        f"decided={summary.get('decided_count', 0)}"
    )


def format_resolution_status_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_status_summary(report)]
    artifact = report.get("artifacts", {}).get("hardware_resolution_status_report")
    if artifact:
        lines.append(f"Status report: {artifact}")
    for action in report.get("actions", []):
        lines.append(
            "- "
            f"{action.get('description') or action.get('stable_part_id')}: "
            f"{action.get('status')} -> {action.get('next_pipeline_task')}"
        )
    return "\n".join(lines)


def format_resolution_pipeline_queue_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware resolution pipeline queue: "
        f"{report.get('queue_status', 'unknown')}, "
        f"ready={summary.get('ready_task_count', 0)}, "
        f"blocked={summary.get('blocked_count', 0)}, "
        f"invalid={summary.get('invalid_count', 0)}"
    )


def format_resolution_pipeline_queue_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_pipeline_queue_summary(report)]
    artifact = report.get("artifacts", {}).get("hardware_resolution_pipeline_queue")
    if artifact:
        lines.append(f"Pipeline queue: {artifact}")
    for task in report.get("tasks", []):
        lines.append(
            "- ready "
            f"{task.get('task_type')}: "
            f"{task.get('description') or task.get('stable_part_id')} "
            f"-> {task.get('next_pipeline_task')}"
        )
    for item in report.get("blocked_actions", []):
        lines.append(
            "- blocked "
            f"{item.get('description') or item.get('stable_part_id')}: "
            f"{item.get('status')} ({item.get('reason')})"
        )
    return "\n".join(lines)


def format_resolution_pipeline_execution_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware resolution pipeline execution: "
        f"{report.get('execution_status', 'unknown')}, "
        f"executed={summary.get('executed_task_count', 0)}, "
        f"staged={summary.get('staged_task_count', 0)}, "
        f"blocked={summary.get('blocked_count', 0)}, "
        f"failed={summary.get('failed_count', 0)}"
    )


def format_resolution_pipeline_execution_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_pipeline_execution_summary(report)]
    artifact = report.get("artifacts", {}).get("hardware_resolution_pipeline_execution_report")
    if artifact:
        lines.append(f"Execution report: {artifact}")
    for result in report.get("task_results", []):
        lines.append(
            "- "
            f"{result.get('task_type')}: "
            f"{result.get('status')} "
            f"({result.get('stable_part_id') or result.get('action_id')})"
        )
    for item in report.get("blocked_actions", []):
        lines.append(
            "- blocked "
            f"{item.get('description') or item.get('stable_part_id')}: "
            f"{item.get('reason')}"
        )
    return "\n".join(lines)


def format_resolution_regeneration_prep_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware regeneration prep: "
        f"{report.get('prep_status', 'unknown')}, "
        f"tasks={summary.get('task_count', 0)}, "
        f"source={summary.get('source_evidence_task_count', 0)}, "
        f"spec={summary.get('spec_patch_task_count', 0)}"
    )


def format_resolution_regeneration_prep_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_regeneration_prep_summary(report)]
    artifact = report.get("artifacts", {}).get("hardware_resolution_regeneration_prep_report")
    if artifact:
        lines.append(f"Prep report: {artifact}")
    for key, value in sorted(report.get("artifacts", {}).items()):
        if key != "hardware_resolution_regeneration_prep_report":
            lines.append(f"- {key}: {value}")
    for step in report.get("next_steps", []):
        lines.append(f"- next: {step}")
    return "\n".join(lines)


def format_resolution_regeneration_check_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware regeneration check: "
        f"{report.get('check_status', 'unknown')}, "
        f"placement={summary.get('resolved_placement_request_count', 0)}/"
        f"{summary.get('placement_request_count', 0)}, "
        f"unsupported={summary.get('generator_unsupported_count', 0)}, "
        f"blocking={summary.get('blocking_count', 0)}"
    )


def format_resolution_regeneration_check_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_regeneration_check_summary(report)]
    artifact = report.get("artifacts", {}).get("hardware_resolution_regeneration_check_report")
    if artifact:
        lines.append(f"Check report: {artifact}")
    for reason in report.get("blocking_reasons", []):
        lines.append(f"- blocking: {reason}")
    for step in report.get("next_steps", []):
        lines.append(f"- next: {step}")
    return "\n".join(lines)


def format_resolution_regeneration_execution_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware regeneration execution: "
        f"{report.get('execution_status', 'unknown')}, "
        f"ok={report.get('ok', False)}, "
        f"generated={summary.get('generated', False)}, "
        f"blocking={summary.get('blocking_count', 0)}"
    )


def format_resolution_regeneration_execution_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_regeneration_execution_summary(report)]
    artifact = report.get("artifacts", {}).get("hardware_resolution_regeneration_execution_report")
    if artifact:
        lines.append(f"Execution report: {artifact}")
    for reason in report.get("blocking_reasons", []):
        lines.append(f"- blocking: {reason}")
    hardware_model = report.get("artifacts", {}).get("hardware_model")
    if hardware_model:
        lines.append(f"Hardware model: {hardware_model}")
    return "\n".join(lines)


def format_resolution_layout_patch_candidates_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware layout patch candidates: "
        f"{report.get('candidate_status', 'unknown')}, "
        f"candidates={summary.get('candidate_count', 0)}, "
        f"blocked={summary.get('blocked_count', 0)}"
    )


def format_resolution_layout_patch_candidates_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_layout_patch_candidates_summary(report)]
    artifact = report.get("artifacts", {}).get("hardware_layout_patch_candidates")
    if artifact:
        lines.append(f"Layout patch candidates: {artifact}")
    for candidate in report.get("candidates", []):
        lines.append(
            "- candidate "
            f"{candidate.get('candidate_id')}: "
            f"{candidate.get('stable_part_id')} -> "
            f"{candidate.get('anchor_instance_id')} "
            f"({candidate.get('status')})"
        )
    for item in report.get("blocked_items", []):
        lines.append(
            "- blocked "
            f"{item.get('stable_part_id') or item.get('request_id')}: "
            f"{item.get('reason')}"
        )
    if not report.get("candidates") and not report.get("blocked_items"):
        lines.append("No source-evidence placement targets are ready yet.")
    return "\n".join(lines)


def format_resolution_layout_patch_contact_probe_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware layout patch contact probe: "
        f"{report.get('probe_status', 'unknown')}, "
        f"ok={report.get('ok', False)}, "
        f"approved={summary.get('approved_count', 0)}, "
        f"rejected={summary.get('rejected_count', 0)}, "
        f"blocked={summary.get('blocked_count', 0)}"
    )


def format_resolution_layout_patch_contact_probe_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_layout_patch_contact_probe_summary(report)]
    artifact = report.get("artifacts", {}).get("contact_probe_report")
    if artifact:
        lines.append(f"Contact probe report: {artifact}")
    manifest = report.get("artifacts", {}).get("contact_probe_manifest")
    if manifest:
        lines.append(f"Contact probe manifest: {manifest}")
    if report.get("probe_status") == "blocked_no_candidates":
        lines.append("No layout patch candidates are ready to probe yet.")
    return "\n".join(lines)


def format_resolution_layout_patch_merge_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware layout patch merge: "
        f"{report.get('merge_status', 'unknown')}, "
        f"ok={report.get('ok', False)}, "
        f"merged={summary.get('merged_count', 0)}, "
        f"blocked={summary.get('blocked_count', 0)}"
    )


def format_resolution_layout_patch_merge_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_layout_patch_merge_summary(report)]
    artifact = report.get("artifacts", {}).get("hardware_layout_patch_merge_report")
    if artifact:
        lines.append(f"Merge report: {artifact}")
    layout = report.get("artifacts", {}).get("merged_assembly_layout_ir")
    if layout:
        lines.append(f"Merged layout IR: {layout}")
    elif report.get("merge_status") == "blocked_user_approval_required":
        lines.append("No layout IR was written because explicit merge approval is required.")
    elif report.get("merge_status") == "blocked_no_approved_candidates":
        lines.append("No layout IR was written because no contact-probe-approved candidates exist.")
    return "\n".join(lines)


def format_resolution_layout_patch_downstream_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware layout patch downstream regeneration: "
        f"{report.get('regeneration_status', 'unknown')}, "
        f"ok={report.get('ok', False)}, "
        f"generated={summary.get('generated', False)}, "
        f"merged={summary.get('merged_count', 0)}"
    )


def format_resolution_layout_patch_downstream_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_layout_patch_downstream_summary(report)]
    artifact = report.get("artifacts", {}).get("downstream_regeneration_report")
    if artifact:
        lines.append(f"Downstream report: {artifact}")
    model = report.get("artifacts", {}).get("assembly_model")
    if model:
        lines.append(f"Assembly model: {model}")
    for reason in report.get("blocking_reasons", []):
        lines.append(f"- blocking: {reason}")
    return "\n".join(lines)


def format_resolution_input_requests_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware input requests: "
        f"{report.get('request_status', 'unknown')}, "
        f"{summary.get('request_count', 0)} requests "
        f"(evidence={summary.get('source_evidence_request_count', 0)}, "
        f"spec={summary.get('missing_spec_request_count', 0)})"
    )


def format_resolution_input_requests_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_input_requests_summary(report)]
    artifact = report.get("artifacts", {}).get("hardware_resolution_input_requests")
    if artifact:
        lines.append(f"Requests: {artifact}")
    requests = report.get("requests", [])
    if not requests:
        lines.append("No pending input requests remain.")
        return "\n".join(lines)
    for request in requests:
        lines.append(
            "- "
            f"{request.get('description') or request.get('stable_part_id')}: "
            f"{request.get('input_kind')} for {request.get('unplaced_quantity', 0)} unplaced"
        )
        field_names = ", ".join(field.get("name", "") for field in request.get("fields", [])[:4])
        if field_names:
            lines.append(f"  fields: {field_names}")
    return "\n".join(lines)


def format_resolution_input_template_summary(report: dict[str, Any]) -> str:
    return (
        "Hardware input submission template: "
        f"{report.get('template_status', 'unknown')}, "
        f"{report.get('submission_count', 0)} submissions -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_input_submission_template')}"
    )


def format_resolution_input_template_submit_summary(report: dict[str, Any]) -> str:
    validation = report.get("validation", {})
    summary = validation.get("summary", {})
    return (
        "Hardware input template submit: "
        f"{report.get('status', 'unknown')}, "
        f"recorded={report.get('recorded_count', 0)}, "
        f"valid={summary.get('valid_count', 0)}, "
        f"empty={summary.get('empty_count', 0)}, "
        f"invalid={summary.get('invalid_count', 0)}"
    )


def format_resolution_input_draft_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware input drafts: "
        f"{report.get('draft_status', 'unknown')}, "
        f"ready={summary.get('ready_count', 0)}, "
        f"confirm={summary.get('requires_confirmation_count', 0)}, "
        f"blocked={summary.get('blocked_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_input_draft_report')}"
    )


def format_resolution_input_draft_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_input_draft_summary(report)]
    template = report.get("artifacts", {}).get("hardware_resolution_input_draft_template")
    if template:
        lines.append(f"Draft template: {template}")
    for item in report.get("items", []):
        lines.append(
            "- "
            f"{item.get('description') or item.get('stable_part_id')}: "
            f"{item.get('draft_status')}"
        )
        for reason in item.get("blocking_reasons", [])[:3]:
            lines.append(f"  blocking: {reason}")
        for warning in item.get("warnings", [])[:3]:
            lines.append(f"  warning: {warning}")
    return "\n".join(lines)


def format_resolution_blocker_packet_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware blocker packet: "
        f"{report.get('packet_status', 'unknown')}, "
        f"blocked={summary.get('blocked_count', 0)}, "
        f"confirm={summary.get('requires_confirmation_count', 0)}, "
        f"ready={summary.get('ready_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_blocker_packet')}"
    )


def format_resolution_blocker_packet_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_blocker_packet_summary(report)]
    for item in report.get("items", []):
        lines.append(
            "- "
            f"{item.get('description') or item.get('stable_part_id')}: "
            f"{item.get('packet_status')} -> {item.get('next_action')}"
        )
        for reason in item.get("blocking_reasons", [])[:3]:
            lines.append(f"  blocking: {reason}")
        for question in item.get("human_questions", [])[:3]:
            lines.append(f"  ask: {question}")
    return "\n".join(lines)


def format_resolution_answer_candidates_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware answer candidates: "
        f"{report.get('candidate_status', 'unknown')}, "
        f"items={summary.get('item_count', 0)}, "
        f"ready={summary.get('ready_candidate_count', 0)}, "
        f"confirm={summary.get('confirmation_candidate_count', 0)}, "
        f"blocked={summary.get('blocked_item_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_answer_candidates')}"
    )


def format_resolution_answer_candidates_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_answer_candidates_summary(report)]
    for item in report.get("items", []):
        lines.append(
            "- "
            f"{item.get('description') or item.get('stable_part_id')}: "
            f"{item.get('item_status')} -> {item.get('next_action')}"
        )
        for candidate in item.get("candidates", [])[:3]:
            lines.append(
                "  candidate: "
                f"{candidate.get('candidate_id')} "
                f"{candidate.get('candidate_status')} "
                f"({candidate.get('evidence_status')})"
            )
            for reason in candidate.get("reasons", [])[:2]:
                lines.append(f"    reason: {reason}")
    return "\n".join(lines)


def format_resolution_evidence_pack_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware evidence pack: "
        f"{report.get('pack_status', 'unknown')}, "
        f"items={summary.get('item_count', 0)}, "
        f"covered={summary.get('covered_field_count', 0)}, "
        f"uncovered={summary.get('uncovered_field_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_evidence_pack')}"
    )


def format_resolution_evidence_pack_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_evidence_pack_summary(report)]
    for item in report.get("items", []):
        guidance = item.get("manual_completion_guidance", {})
        lines.append(
            "- "
            f"{item.get('description') or item.get('stable_part_id')}: "
            f"{item.get('pack_status')} -> {guidance.get('next_action')}"
        )
        for field in item.get("field_requirements", []):
            lines.append(
                "  field: "
                f"{field.get('name')}={field.get('coverage_status')}"
            )
        for candidate in item.get("candidate_evidence", [])[:2]:
            lines.append(
                "  candidate: "
                f"{candidate.get('candidate_id')} "
                f"{candidate.get('candidate_status')} "
                f"missing={candidate.get('missing_payload_fields', [])}"
            )
    return "\n".join(lines)


def format_resolution_manual_completion_evidence_draft_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware manual completion evidence draft: "
        f"{report.get('draft_status', 'unknown')}, "
        f"drafted={summary.get('drafted_count', 0)}, "
        f"complete={summary.get('complete_payload_count', 0)}, "
        f"incomplete={summary.get('incomplete_payload_count', 0)}, "
        f"source_backed={summary.get('source_backed_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_manual_completion_review_template')}"
    )


def format_resolution_manual_completion_evidence_draft_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_manual_completion_evidence_draft_summary(report)]
    for item in report.get("drafted_completions", []):
        lines.append(
            "- "
            f"{item.get('stable_part_id') or item.get('request_id')}: "
            f"{item.get('pack_status')} "
            f"missing={item.get('missing_required_fields_after_draft', [])}"
        )
    lines.append("Policy: drafted payloads remain source_backed=false until a human/verifier confirms them.")
    return "\n".join(lines)


def format_resolution_hitl_question_packet_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL questions: "
        f"{report.get('question_status', 'unknown')}, "
        f"questions={summary.get('question_count', 0)}, "
        f"fields={summary.get('field_question_count', 0)}, "
        f"confirm={summary.get('source_confirmation_question_count', 0)}, "
        f"rationale={summary.get('rationale_question_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_question_packet')}"
    )


def format_resolution_hitl_question_packet_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_question_packet_summary(report)]
    for item in report.get("items", []):
        lines.append(
            "- "
            f"{item.get('stable_part_id')}: "
            f"missing={item.get('current_missing_fields', [])} "
            f"questions={len(item.get('question_ids', []))}"
        )
    for question in report.get("questions", [])[:8]:
        option_count = len(question.get("candidate_evidence", []))
        lines.append(
            "  ask: "
            f"{question.get('question_kind')} "
            f"{question.get('field_name') or ''} "
            f"options={option_count} -> {question.get('prompt')}"
        )
    return "\n".join(lines)


def format_resolution_hitl_answer_apply_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL answers applied: "
        f"{report.get('apply_status', 'unknown')}, "
        f"applied={summary.get('applied_count', 0)}, "
        f"skipped={summary.get('skipped_count', 0)}, "
        f"invalid={summary.get('invalid_count', 0)}, "
        f"ready={summary.get('ready_for_manual_preflight_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_manual_completion_review_template')}"
    )


def format_resolution_hitl_answer_patch_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL answer patch: "
        f"{report.get('patch_status', 'unknown')}, "
        f"patched={summary.get('applied_count', 0)}, "
        f"invalid={summary.get('invalid_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_answer_template')}"
    )


def format_resolution_hitl_answer_patch_preflight_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL answer patch preflight: "
        f"{report.get('preflight_status', 'unknown')}, "
        f"ok={report.get('ok_to_apply_patch', False)}, "
        f"valid={summary.get('valid_patch_count', 0)}, "
        f"invalid={summary.get('invalid_count', 0)}, "
        f"warnings={summary.get('warning_count', 0)}, "
        f"remaining={summary.get('remaining_unanswered_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_answer_patch_preflight_report')}"
    )


def format_resolution_hitl_answer_patch_preflight_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_answer_patch_preflight_summary(report)]
    for item in report.get("valid_patches", [])[:8]:
        lines.append(
            "- valid "
            f"{item.get('question_id')}: {item.get('source')}"
        )
    for item in report.get("warning_patches", [])[:8]:
        lines.append(
            "- warning "
            f"{item.get('question_id')}: {item.get('warning')} "
            f"status={item.get('candidate_status')}"
        )
    for item in report.get("invalid_patches", [])[:8]:
        lines.append(
            "- invalid "
            f"{item.get('question_id')}: {item.get('error')}"
        )
    for item in report.get("missing_rationale_pairs", [])[:8]:
        lines.append(
            "- missing rationale "
            f"{item.get('question_id')}: {item.get('error')}"
        )
    for action in report.get("next_actions", [])[:5]:
        lines.append(f"- next: {action}")
    return "\n".join(lines)


def format_resolution_hitl_source_assertion_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL source assertion packet: "
        f"{report.get('assertion_status', 'unknown')}, "
        f"items={summary.get('item_count', 0)}, "
        f"blocked={summary.get('blocked_item_count', 0)}, "
        f"source={summary.get('source_confirmation_required_count', 0)}, "
        f"rationale={summary.get('rationale_required_count', 0)}, "
        f"fields={summary.get('field_value_required_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_source_assertion_packet')}"
    )


def format_resolution_hitl_source_assertion_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_source_assertion_summary(report)]
    for item in report.get("assertion_items", []):
        lines.append(
            "- "
            f"{item.get('stable_part_id')}: "
            f"ready={item.get('ready_for_guarded_submission')} "
            f"source_backed={item.get('source_backed')} "
            f"rationale={item.get('rationale_present')} "
            f"fields={item.get('missing_required_fields', [])}"
        )
        for requirement in item.get("minimum_patch_requirements", []):
            lines.append(f"  need: {requirement}")
        for candidate in item.get("source_candidates", [])[:3]:
            lines.append(
                "  candidate: "
                f"{candidate.get('candidate_id')} "
                f"status={candidate.get('candidate_status')} "
                f"missing={candidate.get('missing_payload_fields', [])}"
            )
    return "\n".join(lines)


def format_resolution_hitl_source_assertion_response_template_summary(report: dict[str, Any]) -> str:
    return (
        "Hardware HITL source assertion response template: "
        f"{report.get('response_template_status', 'unknown')}, "
        f"responses={report.get('response_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_source_assertion_response_template')}"
    )


def format_resolution_hitl_source_assertion_disposition_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL source assertion disposition: "
        f"{report.get('disposition_status', 'unknown')}, "
        f"ready={summary.get('ready_count', 0)}, "
        f"blocked={summary.get('blocked_count', 0)}, "
        f"invalid={summary.get('invalid_count', 0)}, "
        f"missing_fields={summary.get('missing_field_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_source_assertion_disposition_report')}"
    )


def format_resolution_hitl_source_assertion_disposition_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_source_assertion_disposition_summary(report)]
    for item in report.get("items", []):
        lines.append(
            "- "
            f"{item.get('stable_part_id')}: "
            f"{item.get('disposition_status')} "
            f"source={item.get('source_confirmed')} "
            f"rationale={item.get('rationale_present')} "
            f"missing={item.get('missing_fields', [])}"
        )
        for reason in item.get("documented_reasons", [])[:6]:
            lines.append(f"  reason: {reason}")
        for reason in item.get("invalid_reasons", [])[:6]:
            lines.append(f"  invalid: {reason}")
        lines.append(f"  next: {item.get('next_action')}")
    for action in report.get("next_actions", [])[:6]:
        lines.append(f"next_action: {action}")
    return "\n".join(lines)


def format_resolution_hitl_source_assertion_response_apply_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL source assertion response apply: "
        f"{report.get('apply_status', 'unknown')}, "
        f"patches={summary.get('patch_count', 0)}, "
        f"applied={summary.get('applied_count', 0)}, "
        f"skipped={summary.get('skipped_count', 0)}, "
        f"invalid={summary.get('invalid_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_answer_patch')}"
    )


def format_resolution_hitl_source_assertion_response_apply_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_source_assertion_response_apply_summary(report)]
    for item in report.get("applied_responses", [])[:8]:
        lines.append(
            "- applied "
            f"{item.get('question_id')}: {item.get('question_kind')} {item.get('field_name') or ''}"
        )
    for item in report.get("skipped_responses", [])[:8]:
        lines.append(
            "- skipped "
            f"{item.get('question_id')}: {item.get('reason')}"
        )
    for item in report.get("invalid_responses", [])[:8]:
        lines.append(
            "- invalid "
            f"{item.get('question_id') or item.get('request_id')}: {item.get('error')}"
        )
    return "\n".join(lines)


def format_resolution_hitl_answer_patch_template_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL answer patch template: "
        f"{report.get('patch_template_status', 'unknown')}, "
        f"instructions={summary.get('instruction_count', 0)}, "
        f"options={summary.get('option_instruction_count', 0)}, "
        f"explicit={summary.get('explicit_answer_instruction_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_answer_patch_template')}"
    )


def format_resolution_hitl_answer_patch_template_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_answer_patch_template_summary(report)]
    for item in report.get("patch_instructions", [])[:8]:
        lines.append(
            "- "
            f"{item.get('question_kind')} "
            f"{item.get('field_name') or ''}: "
            f"{item.get('recommended_patch_shape')}"
        )
    return "\n".join(lines)


def format_resolution_hitl_evidence_review_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL evidence review: "
        f"{report.get('review_status', 'unknown')}, "
        f"items={summary.get('item_count', 0)}, "
        f"unanswered={summary.get('unanswered_question_count', 0)}, "
        f"ready={summary.get('ready_item_count', 0)}, "
        f"blocked={summary.get('blocked_item_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_evidence_review_packet')}"
    )


def format_resolution_hitl_evidence_review_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_evidence_review_summary(report)]
    for item in report.get("review_items", []):
        lines.append(
            "- "
            f"{item.get('stable_part_id')}: "
            f"source_backed={item.get('source_backed')} "
            f"rationale={item.get('rationale_present')} "
            f"missing={item.get('missing_required_fields', [])} "
            f"unanswered={len(item.get('unanswered_questions', []))}"
        )
        for question in item.get("unanswered_questions", [])[:4]:
            lines.append(
                "  ask: "
                f"{question.get('question_kind')} "
                f"{question.get('field_name') or ''} -> "
                f"{question.get('recommended_patch_shape')}"
            )
    return "\n".join(lines)


def format_resolution_hitl_answer_patch_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_answer_patch_summary(report)]
    for item in report.get("applied_patches", []):
        lines.append(
            "- patched "
            f"{item.get('question_id')}: {item.get('source')}"
        )
    for item in report.get("invalid_patches", []):
        lines.append(
            "- invalid "
            f"{item.get('question_id')}: {item.get('error')}"
        )
    artifact = report.get("artifacts", {}).get("hardware_resolution_hitl_answer_patch_apply_report")
    if artifact:
        lines.append(f"Patch report: {artifact}")
    return "\n".join(lines)


def format_resolution_hitl_answer_apply_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_answer_apply_summary(report)]
    for item in report.get("completion_readiness", []):
        lines.append(
            "- "
            f"{item.get('stable_part_id')}: "
            f"ready={item.get('ready_for_manual_preflight')} "
            f"missing_fields={item.get('missing_required_fields', [])} "
            f"missing_manual={item.get('missing_manual_fields', [])}"
        )
    return "\n".join(lines)


def format_resolution_hitl_guarded_submission_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL guarded submission: "
        f"{report.get('guarded_status', 'unknown')}, "
        f"ok={report.get('ok', False)}, "
        f"hitl_applied={summary.get('hitl_applied_count', 0)}, "
        f"preflight={summary.get('preflight_status', 'unknown')}, "
        f"flow_ran={summary.get('submission_flow_ran', False)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_guarded_submission_report')}"
    )


def format_resolution_hitl_patch_guarded_submission_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL patch guarded submission: "
        f"{report.get('guarded_status', 'unknown')}, "
        f"ok={report.get('ok', False)}, "
        f"patch={summary.get('patch_status', 'unknown')}, "
        f"preflight={summary.get('preflight_status', 'unknown')}, "
        f"flow_ran={summary.get('submission_flow_ran', False)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_patch_guarded_submission_report')}"
    )


def format_resolution_hitl_source_response_guarded_submission_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware HITL source response guarded submission: "
        f"{report.get('guarded_status', 'unknown')}, "
        f"ok={report.get('ok', False)}, "
        f"source_response={summary.get('source_response_status', 'unknown')}, "
        f"patches={summary.get('source_response_patch_count', 0)}, "
        f"preflight={summary.get('preflight_status', 'unknown')}, "
        f"flow_ran={summary.get('submission_flow_ran', False)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_hitl_source_response_guarded_submission_report')}"
    )


def format_resolution_hitl_source_response_guarded_submission_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_source_response_guarded_submission_summary(report)]
    for action in report.get("next_actions", [])[:5]:
        lines.append(f"- next: {action}")
    return "\n".join(lines)


def format_resolution_hitl_patch_guarded_submission_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_patch_guarded_submission_summary(report)]
    for action in report.get("next_actions", [])[:5]:
        lines.append(f"- next: {action}")
    return "\n".join(lines)


def format_resolution_hitl_guarded_submission_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_hitl_guarded_submission_summary(report)]
    for action in report.get("next_actions", [])[:5]:
        lines.append(f"- next: {action}")
    return "\n".join(lines)


def format_resolution_answer_selection_template_summary(report: dict[str, Any]) -> str:
    return (
        "Hardware answer selection template: "
        f"{report.get('selection_status', 'unknown')}, "
        f"selections={report.get('selection_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_answer_selection_template')}"
    )


def format_resolution_manual_completion_template_summary(report: dict[str, Any]) -> str:
    return (
        "Hardware manual completion template: "
        f"{report.get('completion_status', 'unknown')}, "
        f"completions={report.get('completion_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_manual_completion_template')}"
    )


def format_resolution_manual_completion_apply_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware manual completion apply: "
        f"{report.get('apply_status', 'unknown')}, "
        f"applied={summary.get('applied_count', 0)}, "
        f"skipped={summary.get('skipped_count', 0)}, "
        f"invalid={summary.get('invalid_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_blocker_response_template')}"
    )


def format_resolution_manual_completion_apply_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_manual_completion_apply_summary(report)]
    for item in report.get("applied_completions", []):
        lines.append(
            "- applied "
            f"{item.get('request_id')}: {item.get('input_kind')}"
        )
    for item in report.get("invalid_completions", []):
        lines.append(
            "- invalid "
            f"{item.get('request_id')}: {item.get('error')}"
        )
    artifact = report.get("artifacts", {}).get("manual_completion_apply_report")
    if artifact:
        lines.append(f"Manual apply report: {artifact}")
    return "\n".join(lines)


def format_resolution_manual_completion_preflight_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware manual completion preflight: "
        f"{report.get('preflight_status', 'unknown')}, "
        f"ok_to_submit={report.get('ok_to_submit', False)}, "
        f"valid={summary.get('valid_submission_count', 0)}, "
        f"invalid={summary.get('submission_invalid_count', 0)}, "
        f"manual_invalid={summary.get('manual_invalid_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_manual_completion_preflight_report')}"
    )


def format_resolution_manual_completion_preflight_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_manual_completion_preflight_summary(report)]
    for action in report.get("next_actions", []):
        lines.append(f"- next: {action}")
    return "\n".join(lines)


def format_resolution_answer_selection_apply_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware answer selection apply: "
        f"{report.get('apply_status', 'unknown')}, "
        f"applied={summary.get('applied_count', 0)}, "
        f"skipped={summary.get('skipped_count', 0)}, "
        f"invalid={summary.get('invalid_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_blocker_response_template')}"
    )


def format_resolution_answer_selection_apply_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_answer_selection_apply_summary(report)]
    for item in report.get("applied_selections", []):
        lines.append(
            "- applied "
            f"{item.get('request_id')}: {item.get('candidate_id')} "
            f"({item.get('candidate_status')})"
        )
    for item in report.get("invalid_selections", []):
        lines.append(
            "- invalid "
            f"{item.get('request_id')}: {item.get('candidate_id')} "
            f"({item.get('error')})"
        )
    artifact = report.get("artifacts", {}).get("answer_selection_apply_report")
    if artifact:
        lines.append(f"Selection apply report: {artifact}")
    return "\n".join(lines)


def format_resolution_answer_preflight_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware answer preflight: "
        f"{report.get('preflight_status', 'unknown')}, "
        f"ok_to_submit={report.get('ok_to_submit', False)}, "
        f"valid={summary.get('valid_submission_count', 0)}, "
        f"invalid={summary.get('submission_invalid_count', 0)}, "
        f"selection_invalid={summary.get('selection_invalid_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_answer_preflight_report')}"
    )


def format_resolution_answer_preflight_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_answer_preflight_summary(report)]
    for action in report.get("next_actions", []):
        lines.append(f"- next: {action}")
    return "\n".join(lines)


def format_resolution_guarded_submission_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware guarded submission: "
        f"{report.get('guarded_status', 'unknown')}, "
        f"ok={report.get('ok', False)}, "
        f"flow_ran={summary.get('submission_flow_ran', False)}, "
        f"recorded={summary.get('recorded_count', 0)}, "
        f"layout_candidates={summary.get('layout_candidate_count', 0)} -> "
        f"{report.get('artifacts', {}).get('guarded_submission_report')}"
    )


def format_resolution_guarded_submission_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_guarded_submission_summary(report)]
    for action in report.get("next_actions", []):
        lines.append(f"- next: {action}")
    return "\n".join(lines)


def format_resolution_blocker_response_template_summary(report: dict[str, Any]) -> str:
    return (
        "Hardware blocker response template: "
        f"{report.get('response_status', 'unknown')}, "
        f"responses={report.get('response_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_blocker_response_template')}"
    )


def format_resolution_blocker_response_apply_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware blocker response apply: "
        f"{report.get('apply_status', 'unknown')}, "
        f"applied={summary.get('applied_count', 0)}, "
        f"empty={summary.get('empty_count', 0)}, "
        f"invalid={summary.get('invalid_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_input_submission_template')}"
    )


def format_resolution_blocker_response_apply_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_blocker_response_apply_summary(report)]
    validation = report.get("submission_validation", {})
    for item in validation.get("items", []):
        lines.append(
            "- "
            f"{item.get('request_id')}: {item.get('status')}"
            + (f" ({item.get('error')})" if item.get("error") else "")
        )
    artifact = report.get("artifacts", {}).get("blocker_response_apply_report")
    if artifact:
        lines.append(f"Apply report: {artifact}")
    return "\n".join(lines)


def format_resolution_input_confirmation_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return (
        "Hardware input confirmations: "
        f"{report.get('confirmation_status', 'unknown')}, "
        f"requests={summary.get('request_count', 0)}, "
        f"candidates={summary.get('candidate_count', 0)} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_input_confirmation_requests')}"
    )


def format_resolution_input_confirmation_details(report: dict[str, Any]) -> str:
    lines = [format_resolution_input_confirmation_summary(report)]
    for request in report.get("requests", []):
        lines.append(
            "- "
            f"{request.get('description') or request.get('stable_part_id')}: "
            f"{request.get('confirmation_status')}"
        )
        for candidate in request.get("candidates", []):
            lines.append(
                "  candidate: "
                f"{candidate.get('candidate_id')} "
                f"qty={candidate.get('quantity')} "
                f"status={candidate.get('status')}"
            )
        for reason in request.get("blocking_reasons", [])[:2]:
            lines.append(f"  blocking: {reason}")
    if not report.get("requests"):
        lines.append("No draft candidates currently require confirmation.")
    return "\n".join(lines)


def format_resolution_input_confirmation_apply_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    selected = report.get("selected", {})
    return (
        "Hardware input confirmation applied: "
        f"{report.get('confirmation_status', 'unknown')}, "
        f"applied={summary.get('applied_count', 0)}, "
        f"blocked={summary.get('blocked_count', 0)}, "
        f"selected={selected.get('request_id', 'unknown')}:{selected.get('candidate_id', 'unknown')} -> "
        f"{report.get('artifacts', {}).get('hardware_resolution_input_confirmed_template')}"
    )


def _input_requests_path(context: dict[str, Path]) -> Path:
    env_path = _env_path("AGENTIC_CAD_HARDWARE_RESOLUTION_INPUT_REQUESTS")
    if env_path:
        return env_path
    return context["base_dir"] / DEFAULT_INPUT_REQUESTS_FILENAME


def _manual_completion_template_path(
    context: dict[str, Path],
    explicit_path: str | Path | None,
) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    env_path = _env_path("AGENTIC_CAD_HARDWARE_RESOLUTION_MANUAL_COMPLETION_TEMPLATE")
    if env_path:
        return env_path
    review_template = context["base_dir"] / DEFAULT_INPUT_MANUAL_COMPLETION_REVIEW_TEMPLATE_FILENAME
    if review_template.is_file():
        return review_template
    return context["base_dir"] / DEFAULT_INPUT_MANUAL_COMPLETION_TEMPLATE_FILENAME


def _default_input_draft_evidence_paths(
    repo_root: Path,
    explicit_paths: list[str | Path] | None,
) -> list[Path]:
    if explicit_paths is not None:
        return [Path(path).expanduser().resolve() for path in explicit_paths]
    root = repo_root / "reference_cases" / "wheelchair_sources" / "ground_truth"
    return [
        root / "disruptor_hardware_specs.json",
        root / "disruptor_reviewed_custom_parts.json",
    ]


def _resolution_plan_path(context: dict[str, Path]) -> Path:
    env_path = _env_path("AGENTIC_CAD_HARDWARE_RESOLUTION_PLAN")
    if env_path:
        return env_path
    return context["base_dir"] / "hardware_resolution_plan.json"


def _decisions_path(context: dict[str, Path], explicit_path: str | Path | None) -> Path:
    if explicit_path is not None:
        return Path(explicit_path).expanduser().resolve()
    env_path = _env_path("AGENTIC_CAD_HARDWARE_RESOLUTION_DECISIONS")
    if env_path:
        return env_path
    return context["base_dir"] / DEFAULT_DECISIONS_FILENAME


def _review_plan_path(context: dict[str, Path]) -> Path | None:
    env_path = _env_path("AGENTIC_CAD_HUMAN_REVIEW_PLAN")
    if env_path:
        return env_path
    candidate = context["base_dir"] / "wood_screw_human_review_plan.json"
    return candidate.resolve() if candidate.is_file() else None


def _select_action(
    plan: dict[str, Any],
    action_id: str | None,
    *,
    recommended_action: str | None = None,
) -> dict[str, Any]:
    actions = plan.get("actions", [])
    if action_id:
        for action in actions:
            if action.get("action_id") == action_id:
                if recommended_action and action.get("recommended_action") != recommended_action:
                    raise ValueError(f"resolution action is not {recommended_action}: {action_id}")
                return action
        raise ValueError(f"resolution action was not found: {action_id}")
    candidates = [
        action for action in actions
        if recommended_action is None or action.get("recommended_action") == recommended_action
    ]
    if len(candidates) != 1:
        raise ValueError("action_id is required when the resolution plan has multiple matching actions")
    return candidates[0]


def _select_confirmation_candidate(
    requests: dict[str, Any],
    *,
    request_id: str | None,
    candidate_id: str | None,
) -> dict[str, str]:
    candidates: list[dict[str, str]] = []
    for request in requests.get("requests", []):
        if request_id and request.get("request_id") != request_id:
            continue
        for candidate in request.get("candidates", []):
            if candidate_id and candidate.get("candidate_id") != candidate_id:
                continue
            candidates.append({
                "request_id": request.get("request_id"),
                "candidate_id": candidate.get("candidate_id"),
            })
    if len(candidates) != 1:
        raise ValueError(
            "exactly one confirmation candidate must be selected; "
            "provide request_id and candidate_id when multiple candidates exist"
        )
    return candidates[0]


def _read_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object is required: {path}")
    return value


def _write_json(path: str | Path, value: dict[str, Any]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def _first_existing(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"required artifact not found under {root}: {pattern}")
    return matches[0].resolve()


def _optional_first_existing(root: Path, pattern: str) -> Path | None:
    matches = sorted(root.glob(pattern))
    return matches[0].resolve() if matches else None


def _env_path(name: str) -> Path | None:
    value = os.getenv(name)
    return Path(value).expanduser().resolve() if value else None


def _ensure_repo_import(repo_root: Path) -> None:
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
