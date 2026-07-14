"""FreeCAD command registration for the agentic-cad workbench."""

import json

import FreeCADGui as Gui  # type: ignore

from services.human_review_apply import (
    apply_saved_human_review_decisions,
    format_apply_summary,
)
from services.gui_smoke import run_plan_execute_smoke, run_selection_update_smoke
from services.architectural_scan_import import (
    DEFAULT_ARCHITECTURAL_SCAN_IR,
    import_architectural_scan_ir,
)
from services.fastener_reports import (
    build_focused_reprobe_request,
    build_hardware_resolution_plan_for_workspace,
    build_hardware_unresolved_report_for_workspace,
    format_candidate_report_summary,
    format_focused_reprobe_summary,
    format_focused_reprobe_pipeline_summary,
    format_hardware_resolution_summary,
    format_hardware_unresolved_summary,
    rebuild_wood_screw_candidate_report,
    run_focused_reprobe_pipeline,
)
from services.human_review_decisions import (
    default_decisions_path,
    format_decision_summary,
    record_overlay_decision,
)
from services.hardware_resolution_decisions import (
    apply_resolution_blocker_responses_for_workspace,
    apply_resolution_answer_selection_for_workspace,
    apply_resolution_hitl_source_assertion_response_for_workspace,
    apply_resolution_hitl_answers_for_workspace,
    apply_resolution_manual_completion_for_workspace,
    build_resolution_answer_candidates_for_workspace,
    build_resolution_answer_selection_template_for_workspace,
    build_resolution_blocker_packet_for_workspace,
    build_resolution_blocker_response_template_for_workspace,
    build_resolution_evidence_pack_for_workspace,
    draft_resolution_manual_completion_from_evidence_pack_for_workspace,
    build_resolution_hitl_evidence_review_packet_for_workspace,
    build_resolution_hitl_answer_patch_template_for_workspace,
    build_resolution_hitl_question_packet_for_workspace,
    build_resolution_hitl_source_assertion_packet_for_workspace,
    build_resolution_hitl_source_assertion_disposition_report_for_workspace,
    build_resolution_hitl_source_assertion_response_template_for_workspace,
    build_resolution_manual_completion_template_for_workspace,
    build_resolution_layout_patch_candidates_for_workspace,
    build_resolution_input_confirmation_requests_for_workspace,
    build_resolution_input_drafts_for_workspace,
    build_resolution_input_requests_for_workspace,
    build_resolution_input_submission_template_for_workspace,
    build_resolution_pipeline_queue_for_workspace,
    build_resolution_status_report_for_workspace,
    check_resolution_regeneration_readiness_for_workspace,
    confirm_resolution_input_candidate_for_workspace,
    execute_resolution_regeneration_for_workspace,
    execute_resolution_pipeline_queue_for_workspace,
    export_fastener_reject_decisions_for_workspace,
    format_fastener_reject_export_summary,
    format_resolution_answer_candidates_summary,
    format_resolution_answer_selection_apply_summary,
    format_resolution_answer_preflight_summary,
    format_resolution_answer_selection_template_summary,
    format_resolution_blocker_packet_summary,
    format_resolution_blocker_response_apply_summary,
    format_resolution_blocker_response_template_summary,
    format_resolution_evidence_pack_summary,
    format_resolution_hitl_answer_patch_template_summary,
    format_resolution_hitl_evidence_review_summary,
    format_resolution_hitl_answer_patch_summary,
    format_resolution_hitl_answer_patch_preflight_summary,
    format_resolution_hitl_source_assertion_summary,
    format_resolution_hitl_source_assertion_disposition_summary,
    format_resolution_hitl_source_assertion_response_apply_summary,
    format_resolution_hitl_source_assertion_response_template_summary,
    format_resolution_hitl_answer_apply_summary,
    format_resolution_hitl_guarded_submission_summary,
    format_resolution_hitl_patch_guarded_submission_summary,
    format_resolution_hitl_source_response_guarded_submission_summary,
    format_resolution_hitl_question_packet_summary,
    format_resolution_manual_completion_evidence_draft_summary,
    format_resolution_input_confirmation_apply_summary,
    format_resolution_input_confirmation_summary,
    format_resolution_input_requests_summary,
    format_resolution_input_draft_summary,
    format_resolution_input_template_summary,
    format_resolution_input_template_submit_summary,
    format_resolution_layout_patch_contact_probe_summary,
    format_resolution_layout_patch_candidates_summary,
    format_resolution_layout_patch_downstream_summary,
    format_resolution_layout_patch_merge_summary,
    format_resolution_manual_completion_apply_summary,
    format_resolution_manual_completion_preflight_summary,
    format_resolution_manual_completion_template_summary,
    format_resolution_pipeline_execution_summary,
    format_resolution_pipeline_queue_summary,
    format_resolution_regeneration_check_summary,
    format_resolution_regeneration_execution_summary,
    format_resolution_regeneration_prep_summary,
    format_resolution_decision_summary,
    format_resolution_guarded_submission_summary,
    format_resolution_status_summary,
    prepare_resolution_regeneration_inputs_for_workspace,
    merge_resolution_layout_patch_candidates_for_workspace,
    patch_resolution_hitl_answer_template_for_workspace,
    preflight_resolution_hitl_answer_patch_for_workspace,
    preflight_resolution_answer_selection_for_workspace,
    preflight_resolution_manual_completion_for_workspace,
    probe_resolution_layout_patch_contacts_for_workspace,
    regenerate_resolution_layout_patch_assembly_for_workspace,
    record_resolution_decision_for_workspace,
    run_guarded_resolution_submission_for_workspace,
    run_guarded_hitl_submission_for_workspace,
    run_guarded_hitl_patch_submission_for_workspace,
    run_guarded_hitl_source_response_submission_for_workspace,
    run_guarded_manual_completion_submission_for_workspace,
    submit_confirmed_resolution_input_template_for_workspace,
    submit_resolution_input_template_for_workspace,
)
from panels.chat_panel import describe_chat_panel, format_chat_panel_state, show_chat_panel
from services.human_review_visualization import (
    default_review_plan_path,
    format_visualization_summary,
    visualize_review_plan,
)
from services.self_test import format_self_test_summary, run_self_test


class _OpenChatCommand:
    """Open the agentic-cad chat panel."""

    def GetResources(self):
        return {
            "MenuText": "Open Agentic Chat",
            "ToolTip": "Open the AI chat panel for agentic-cad",
        }

    def Activated(self):
        show_chat_panel()

    def IsActive(self):
        return True


class _RunSelfTestCommand:
    """Run local plugin diagnostics without requiring the backend."""

    def GetResources(self):
        return {
            "MenuText": "Run Agentic Self Test",
            "ToolTip": "Verify plugin capabilities, approval gates, and document context.",
        }

    def Activated(self):
        report = run_self_test()
        summary = format_self_test_summary(report)
        try:
            import FreeCAD  # type: ignore

            FreeCAD.Console.PrintMessage(summary + "\n")
            FreeCAD.Console.PrintMessage(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        except Exception:
            print(summary)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        try:
            from PySide6 import QtWidgets
        except ImportError:
            try:
                from PySide2 import QtWidgets
            except ImportError:
                QtWidgets = None
        if QtWidgets is not None:
            QtWidgets.QMessageBox.information(None, "Agentic CAD Self Test", summary)

    def IsActive(self):
        return True


class _ReportChatPanelCommand:
    """Report whether the chat dock and required controls are visible."""

    def GetResources(self):
        return {
            "MenuText": "Report Chat Panel State",
            "ToolTip": "Verify that the Agentic CAD chat dock and required controls are present.",
        }

    def Activated(self):
        try:
            widget = show_chat_panel()
            report = describe_chat_panel(widget)
            summary = format_chat_panel_state(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic CAD Chat Panel", summary)
        except Exception as exc:
            _print_error(f"Chat panel diagnostics failed: {exc}")
            _show_message("Agentic CAD Chat Panel Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _RunPlanExecuteSmokeCommand:
    """Run backend Plan -> approved native Execute from a toolbar command."""

    def GetResources(self):
        return {
            "MenuText": "Run Plan Execute Smoke",
            "ToolTip": "Verify backend planning and approved native FreeCAD execution from the GUI.",
        }

    def Activated(self):
        try:
            report = run_plan_execute_smoke()
            summary = str(report.get("summary", "Plan Execute smoke completed"))
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic CAD Plan Execute Smoke", summary)
        except Exception as exc:
            _print_error(f"Plan Execute smoke failed: {exc}")
            _show_message("Agentic CAD Plan Execute Smoke Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _RunSelectionUpdateSmokeCommand:
    """Run Create -> GUI selection -> stable-ID parameter update smoke."""

    def GetResources(self):
        return {
            "MenuText": "Run Selection Update Smoke",
            "ToolTip": "Verify that planner selection context updates an object by stable ID.",
        }

    def Activated(self):
        try:
            report = run_selection_update_smoke()
            summary = str(report.get("summary", "Selection update smoke completed"))
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic CAD Selection Update Smoke", summary)
        except Exception as exc:
            _print_error(f"Selection update smoke failed: {exc}")
            _show_message("Agentic CAD Selection Update Smoke Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ImportArchitecturalScanCommand:
    """Import the detailed page2/page7 architectural scan rough BIM IR."""

    def GetResources(self):
        return {
            "MenuText": "Import Page2/Page7 Architectural Scan",
            "ToolTip": "Create detailed review proxy geometry from the generated page2/page7 architectural scan IR.",
        }

    def Activated(self):
        try:
            ir_path = _choose_architectural_scan_ir_path()
            if not ir_path:
                return
            report = import_architectural_scan_ir(ir_path)
            summary = (
                f"Imported {report.get('created_object_count', 0)} architectural scan objects. "
                "These are detailed review proxies, not verified construction geometry."
            )
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic CAD Architectural Scan Import", summary)
        except Exception as exc:
            _print_error(f"Architectural scan import failed: {exc}")
            _show_message("Agentic CAD Architectural Scan Import Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildFocusedReprobeRequestCommand:
    """Build a focused material-path reprobe request from a candidate report."""

    def GetResources(self):
        return {
            "MenuText": "Build Focused Reprobe Request",
            "ToolTip": "Create a smaller material-path probe request from ambiguous fastener candidates.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_focused_reprobe_request(document=document)
            summary = format_focused_reprobe_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Focused Reprobe", summary)
        except Exception as exc:
            _print_error(f"Focused reprobe request failed: {exc}")
            _show_message("Agentic Focused Reprobe Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _RebuildWoodScrewCandidateReportCommand:
    """Rebuild a wood screw candidate report from current probe evidence."""

    def GetResources(self):
        return {
            "MenuText": "Rebuild Wood Screw Candidate Report",
            "ToolTip": "Rebuild place/reject/ask_user screw candidates from material-path evidence.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = rebuild_wood_screw_candidate_report(document=document)
            summary = format_candidate_report_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Candidate Report", summary)
        except Exception as exc:
            _print_error(f"Candidate report rebuild failed: {exc}")
            _show_message("Agentic Candidate Report Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _RunFocusedReprobePipelineCommand:
    """Run focused material probe and rebuild wood screw candidate report."""

    def GetResources(self):
        return {
            "MenuText": "Run Focused Reprobe Pipeline",
            "ToolTip": "Run focused FreeCAD material probing and rebuild screw candidates.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = run_focused_reprobe_pipeline(document=document)
            summary = format_focused_reprobe_pipeline_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Focused Reprobe Pipeline", summary)
        except Exception as exc:
            _print_error(f"Focused reprobe pipeline failed: {exc}")
            _show_message("Agentic Focused Reprobe Pipeline Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildHardwareUnresolvedReportCommand:
    """Build a report explaining all currently unplaced hardware."""

    def GetResources(self):
        return {
            "MenuText": "Build Hardware Unresolved Report",
            "ToolTip": "Summarize unplaced hardware and required evidence/review before CAD placement.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_hardware_unresolved_report_for_workspace(document=document)
            summary = format_hardware_unresolved_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Unresolved Report", summary)
        except Exception as exc:
            _print_error(f"Hardware unresolved report failed: {exc}")
            _show_message("Agentic Hardware Unresolved Report Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildHardwareResolutionPlanCommand:
    """Build a next-action plan for currently unresolved hardware."""

    def GetResources(self):
        return {
            "MenuText": "Build Hardware Resolution Plan",
            "ToolTip": "Turn unresolved hardware into bounded review, evidence, and spec actions.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_hardware_resolution_plan_for_workspace(document=document)
            summary = format_hardware_resolution_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Resolution Plan", summary)
        except Exception as exc:
            _print_error(f"Hardware resolution plan failed: {exc}")
            _show_message("Agentic Hardware Resolution Plan Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ConfirmResolutionRejectCommand:
    """Record a confirm-reject decision for the current rejectable resolution action."""

    def GetResources(self):
        return {
            "MenuText": "Confirm Resolution Reject Action",
            "ToolTip": "Record a non-mutating confirm_reject decision for the current hardware resolution action.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = record_resolution_decision_for_workspace(
                document=document,
                decision_action="confirm_reject",
                rationale="confirmed from FreeCAD hardware resolution workflow",
            )
            summary = format_resolution_decision_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Resolution Decision", summary)
        except Exception as exc:
            _print_error(f"Hardware resolution decision failed: {exc}")
            _show_message("Agentic Hardware Resolution Decision Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ExportFastenerRejectDecisionsCommand:
    """Export per-candidate reject decisions from a resolution reject action."""

    def GetResources(self):
        return {
            "MenuText": "Export Fastener Reject Decisions",
            "ToolTip": "Write fastener human-review reject decisions from the hardware resolution action.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = export_fastener_reject_decisions_for_workspace(document=document)
            summary = format_fastener_reject_export_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Fastener Reject Decisions", summary)
        except Exception as exc:
            _print_error(f"Fastener reject decision export failed: {exc}")
            _show_message("Agentic Fastener Reject Decision Export Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionInputRequestsCommand:
    """Build source/spec input requests for remaining hardware resolution actions."""

    def GetResources(self):
        return {
            "MenuText": "Build Resolution Input Requests",
            "ToolTip": "Write fillable source-evidence and missing-spec requests for pending hardware actions.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_input_requests_for_workspace(document=document)
            summary = format_resolution_input_requests_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Input Requests", summary)
        except Exception as exc:
            _print_error(f"Hardware input request generation failed: {exc}")
            _show_message("Agentic Hardware Input Requests Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionStatusReportCommand:
    """Build the current status report for hardware resolution decisions."""

    def GetResources(self):
        return {
            "MenuText": "Build Resolution Status Report",
            "ToolTip": "Write the current ready/pending hardware resolution decision status report.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_status_report_for_workspace(document=document)
            summary = format_resolution_status_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Resolution Status", summary)
        except Exception as exc:
            _print_error(f"Hardware resolution status report failed: {exc}")
            _show_message("Agentic Hardware Resolution Status Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionPipelineQueueCommand:
    """Build the downstream queue for ready hardware resolution decisions."""

    def GetResources(self):
        return {
            "MenuText": "Build Resolution Pipeline Queue",
            "ToolTip": "Write ready/blocked downstream tasks from hardware resolution decisions.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_pipeline_queue_for_workspace(document=document)
            summary = format_resolution_pipeline_queue_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Pipeline Queue", summary)
        except Exception as exc:
            _print_error(f"Hardware resolution pipeline queue failed: {exc}")
            _show_message("Agentic Hardware Pipeline Queue Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ExecuteResolutionPipelineQueueCommand:
    """Execute ready downstream tasks from the hardware resolution queue."""

    def GetResources(self):
        return {
            "MenuText": "Execute Resolution Pipeline Queue",
            "ToolTip": "Run ready hardware-resolution tasks and write an execution report.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = execute_resolution_pipeline_queue_for_workspace(document=document)
            summary = format_resolution_pipeline_execution_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Pipeline Execution", summary)
        except Exception as exc:
            _print_error(f"Hardware resolution pipeline execution failed: {exc}")
            _show_message("Agentic Hardware Pipeline Execution Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _PrepareResolutionRegenerationCommand:
    """Prepare regeneration artifacts from staged hardware source/spec inputs."""

    def GetResources(self):
        return {
            "MenuText": "Prepare Resolution Regeneration",
            "ToolTip": "Prepare placement/spec regeneration artifacts from staged hardware inputs.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = prepare_resolution_regeneration_inputs_for_workspace(document=document)
            summary = format_resolution_regeneration_prep_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Regeneration Prep", summary)
        except Exception as exc:
            _print_error(f"Hardware regeneration prep failed: {exc}")
            _show_message("Agentic Hardware Regeneration Prep Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _CheckResolutionRegenerationCommand:
    """Check whether prepared regeneration artifacts can enter FreeCAD generation."""

    def GetResources(self):
        return {
            "MenuText": "Check Resolution Regeneration",
            "ToolTip": "Check placement targets and generator support before FreeCAD regeneration.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = check_resolution_regeneration_readiness_for_workspace(document=document)
            summary = format_resolution_regeneration_check_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Regeneration Check", summary)
        except Exception as exc:
            _print_error(f"Hardware regeneration check failed: {exc}")
            _show_message("Agentic Hardware Regeneration Check Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ExecuteResolutionRegenerationCommand:
    """Execute FreeCAD hardware regeneration after checks pass."""

    def GetResources(self):
        return {
            "MenuText": "Execute Resolution Regeneration",
            "ToolTip": "Run FreeCAD hardware regeneration only after readiness checks pass.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = execute_resolution_regeneration_for_workspace(document=document)
            summary = format_resolution_regeneration_execution_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Regeneration Execution", summary)
        except Exception as exc:
            _print_error(f"Hardware regeneration execution failed: {exc}")
            _show_message("Agentic Hardware Regeneration Execution Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionLayoutPatchCandidatesCommand:
    """Build reviewable layout patch candidates from resolved placement targets."""

    def GetResources(self):
        return {
            "MenuText": "Build Resolution Layout Patch Candidates",
            "ToolTip": "Create non-committing layout patch candidates that still require FreeCAD contact probing.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_layout_patch_candidates_for_workspace(document=document)
            summary = format_resolution_layout_patch_candidates_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Layout Patch Candidates", summary)
        except Exception as exc:
            _print_error(f"Hardware layout patch candidate generation failed: {exc}")
            _show_message("Agentic Hardware Layout Patch Candidates Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ProbeResolutionLayoutPatchContactsCommand:
    """Probe layout patch candidates against FreeCAD contact/collision geometry."""

    def GetResources(self):
        return {
            "MenuText": "Probe Resolution Layout Patch Contacts",
            "ToolTip": "Measure contact and collision gates for layout patch candidates before merge.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = probe_resolution_layout_patch_contacts_for_workspace(document=document)
            summary = format_resolution_layout_patch_contact_probe_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Layout Patch Contact Probe", summary)
        except Exception as exc:
            _print_error(f"Hardware layout patch contact probe failed: {exc}")
            _show_message("Agentic Hardware Layout Patch Contact Probe Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _MergeResolutionLayoutPatchCandidatesCommand:
    """Preview or approve the guarded layout patch merge."""

    def __init__(self, *, approved, menu_text, tooltip):
        self.approved = approved
        self.menu_text = menu_text
        self.tooltip = tooltip

    def GetResources(self):
        return {
            "MenuText": self.menu_text,
            "ToolTip": self.tooltip,
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = merge_resolution_layout_patch_candidates_for_workspace(
                document=document,
                approved=self.approved,
                approver="freecad-toolbar",
            )
            summary = format_resolution_layout_patch_merge_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Layout Patch Merge", summary)
        except Exception as exc:
            _print_error(f"Hardware layout patch merge failed: {exc}")
            _show_message("Agentic Hardware Layout Patch Merge Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _RegenerateResolutionLayoutPatchAssemblyCommand:
    """Regenerate assembly artifacts from an approved layout patch merge."""

    def GetResources(self):
        return {
            "MenuText": "Regenerate Resolution Layout Patch Assembly",
            "ToolTip": "Generate and validate an assembly from a merged layout patch candidate.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = regenerate_resolution_layout_patch_assembly_for_workspace(document=document)
            summary = format_resolution_layout_patch_downstream_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Layout Patch Assembly", summary)
        except Exception as exc:
            _print_error(f"Hardware layout patch assembly regeneration failed: {exc}")
            _show_message("Agentic Hardware Layout Patch Assembly Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionInputTemplateCommand:
    """Build a fillable submission template for pending hardware inputs."""

    def GetResources(self):
        return {
            "MenuText": "Build Resolution Input Template",
            "ToolTip": "Write a fillable JSON template for pending hardware source/spec inputs.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_input_submission_template_for_workspace(document=document)
            summary = format_resolution_input_template_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Input Template", summary)
        except Exception as exc:
            _print_error(f"Hardware input template generation failed: {exc}")
            _show_message("Agentic Hardware Input Template Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionInputDraftsCommand:
    """Build conservative source/spec input drafts from local reference facts."""

    def GetResources(self):
        return {
            "MenuText": "Build Resolution Input Drafts",
            "ToolTip": "Draft hardware source/spec submissions and report missing evidence without committing CAD.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_input_drafts_for_workspace(document=document)
            summary = format_resolution_input_draft_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Input Drafts", summary)
        except Exception as exc:
            _print_error(f"Hardware input draft build failed: {exc}")
            _show_message("Agentic Hardware Input Drafts Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionBlockerPacketCommand:
    """Build a UI-facing packet for blocked source/spec inputs."""

    def GetResources(self):
        return {
            "MenuText": "Build Resolution Blocker Packet",
            "ToolTip": "Write a packet that explains blocked hardware inputs, candidate evidence, and required questions.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_blocker_packet_for_workspace(document=document)
            summary = format_resolution_blocker_packet_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Blocker Packet", summary)
        except Exception as exc:
            _print_error(f"Hardware blocker packet build failed: {exc}")
            _show_message("Agentic Hardware Blocker Packet Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionAnswerCandidatesCommand:
    """Build non-committing answer candidates for blocked hardware inputs."""

    def GetResources(self):
        return {
            "MenuText": "Build Resolution Answer Candidates",
            "ToolTip": "Write candidate source/spec answers from local evidence without committing CAD.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_answer_candidates_for_workspace(document=document)
            summary = format_resolution_answer_candidates_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Answer Candidates", summary)
        except Exception as exc:
            _print_error(f"Hardware answer candidate build failed: {exc}")
            _show_message("Agentic Hardware Answer Candidates Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionEvidencePackCommand:
    """Build a non-committing evidence pack for blocked hardware inputs."""

    def GetResources(self):
        return {
            "MenuText": "Build Resolution Evidence Pack",
            "ToolTip": "Write field-level evidence coverage for blocked source/spec requests.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_evidence_pack_for_workspace(document=document)
            summary = format_resolution_evidence_pack_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Evidence Pack", summary)
        except Exception as exc:
            _print_error(f"Hardware evidence pack build failed: {exc}")
            _show_message("Agentic Hardware Evidence Pack Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _DraftResolutionManualCompletionFromEvidenceCommand:
    """Draft manual completions from the current evidence pack."""

    def GetResources(self):
        return {
            "MenuText": "Draft Manual Completion From Evidence",
            "ToolTip": "Write a review-only manual completion draft from evidence suggestions.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = draft_resolution_manual_completion_from_evidence_pack_for_workspace(document=document)
            summary = format_resolution_manual_completion_evidence_draft_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Manual Completion Draft", summary)
        except Exception as exc:
            _print_error(f"Hardware manual completion evidence draft failed: {exc}")
            _show_message("Agentic Hardware Manual Completion Draft Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionHitlQuestionPacketCommand:
    """Build HITL questions for source/spec completion review."""

    def GetResources(self):
        return {
            "MenuText": "Build HITL Question Packet",
            "ToolTip": "Write questions and an answer sheet for missing source/spec review fields.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_hitl_question_packet_for_workspace(document=document)
            summary = format_resolution_hitl_question_packet_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware HITL Questions", summary)
        except Exception as exc:
            _print_error(f"Hardware HITL question build failed: {exc}")
            _show_message("Agentic Hardware HITL Questions Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ApplyResolutionHitlAnswersCommand:
    """Apply filled HITL answers to the manual completion review template."""

    def GetResources(self):
        return {
            "MenuText": "Apply HITL Answers",
            "ToolTip": "Copy HITL answers into the manual completion review template.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = apply_resolution_hitl_answers_for_workspace(document=document)
            summary = format_resolution_hitl_answer_apply_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware HITL Answers", summary)
        except Exception as exc:
            _print_error(f"Hardware HITL answer apply failed: {exc}")
            _show_message("Agentic Hardware HITL Answers Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _PatchResolutionHitlAnswersCommand:
    """Patch HITL answers from a selected option/explicit-answer patch file."""

    def GetResources(self):
        return {
            "MenuText": "Patch HITL Answers",
            "ToolTip": "Copy selected HITL answer options or explicit answers into the answer template.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = patch_resolution_hitl_answer_template_for_workspace(document=document)
            summary = format_resolution_hitl_answer_patch_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware HITL Answer Patch", summary)
        except Exception as exc:
            _print_error(f"Hardware HITL answer patch failed: {exc}")
            _show_message("Agentic Hardware HITL Answer Patch Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _PreflightResolutionHitlAnswerPatchCommand:
    """Preflight a HITL answer patch against the evidence review packet."""

    def GetResources(self):
        return {
            "MenuText": "Preflight HITL Answer Patch",
            "ToolTip": "Check HITL answer patch rows against the current evidence review packet before applying them.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = preflight_resolution_hitl_answer_patch_for_workspace(document=document)
            summary = format_resolution_hitl_answer_patch_preflight_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware HITL Patch Preflight", summary)
        except Exception as exc:
            _print_error(f"Hardware HITL answer patch preflight failed: {exc}")
            _show_message("Agentic Hardware HITL Patch Preflight Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionHitlSourceAssertionPacketCommand:
    """Build a reviewer work packet for remaining HITL source assertions."""

    def GetResources(self):
        return {
            "MenuText": "Build HITL Source Assertion Packet",
            "ToolTip": "Write a reviewer checklist for remaining source confirmation, rationale, and spec fields.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_hitl_source_assertion_packet_for_workspace(document=document)
            summary = format_resolution_hitl_source_assertion_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware HITL Source Assertions", summary)
        except Exception as exc:
            _print_error(f"Hardware HITL source assertion packet failed: {exc}")
            _show_message("Agentic Hardware HITL Source Assertions Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionHitlSourceAssertionResponseTemplateCommand:
    """Build a fillable response template for HITL source assertions."""

    def GetResources(self):
        return {
            "MenuText": "Build HITL Source Assertion Response Template",
            "ToolTip": "Write the fillable response file used to create a HITL answer patch.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_hitl_source_assertion_response_template_for_workspace(document=document)
            summary = format_resolution_hitl_source_assertion_response_template_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware HITL Source Response Template", summary)
        except Exception as exc:
            _print_error(f"Hardware HITL source response template failed: {exc}")
            _show_message("Agentic Hardware HITL Source Response Template Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionHitlSourceAssertionDispositionReportCommand:
    """Build a readiness/blocker report for HITL source assertion responses."""

    def GetResources(self):
        return {
            "MenuText": "Build HITL Source Assertion Disposition Report",
            "ToolTip": "Explain which source assertion responses are ready, blocked, or invalid.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_hitl_source_assertion_disposition_report_for_workspace(document=document)
            summary = format_resolution_hitl_source_assertion_disposition_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware HITL Source Disposition", summary)
        except Exception as exc:
            _print_error(f"Hardware HITL source disposition failed: {exc}")
            _show_message("Agentic Hardware HITL Source Disposition Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ApplyResolutionHitlSourceAssertionResponseCommand:
    """Convert filled source assertion responses into a HITL answer patch."""

    def GetResources(self):
        return {
            "MenuText": "Apply HITL Source Assertion Response",
            "ToolTip": "Convert filled source assertion responses into hardware_resolution_hitl_answer_patch.json.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = apply_resolution_hitl_source_assertion_response_for_workspace(document=document)
            summary = format_resolution_hitl_source_assertion_response_apply_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware HITL Source Response Apply", summary)
        except Exception as exc:
            _print_error(f"Hardware HITL source response apply failed: {exc}")
            _show_message("Agentic Hardware HITL Source Response Apply Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionHitlAnswerPatchTemplateCommand:
    """Build a focused HITL answer patch template for unanswered rows."""

    def GetResources(self):
        return {
            "MenuText": "Build HITL Answer Patch Template",
            "ToolTip": "Write a focused patch template for remaining HITL answer rows.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_hitl_answer_patch_template_for_workspace(document=document)
            summary = format_resolution_hitl_answer_patch_template_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware HITL Patch Template", summary)
        except Exception as exc:
            _print_error(f"Hardware HITL answer patch template failed: {exc}")
            _show_message("Agentic Hardware HITL Patch Template Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionHitlEvidenceReviewPacketCommand:
    """Build a HITL evidence review packet for source/spec decisions."""

    def GetResources(self):
        return {
            "MenuText": "Build HITL Evidence Review Packet",
            "ToolTip": "Write a non-committing evidence review packet for unanswered HITL rows.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_hitl_evidence_review_packet_for_workspace(document=document)
            summary = format_resolution_hitl_evidence_review_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware HITL Evidence Review", summary)
        except Exception as exc:
            _print_error(f"Hardware HITL evidence review failed: {exc}")
            _show_message("Agentic Hardware HITL Evidence Review Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _RunGuardedResolutionHitlSubmissionCommand:
    """Run guarded submission from filled HITL answers."""

    def GetResources(self):
        return {
            "MenuText": "Run Guarded HITL Submission",
            "ToolTip": "Apply HITL answers and run guarded source/spec submission only if preflight passes.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = run_guarded_hitl_submission_for_workspace(document=document)
            summary = format_resolution_hitl_guarded_submission_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Guarded HITL Submission", summary)
        except Exception as exc:
            _print_error(f"Hardware guarded HITL submission failed: {exc}")
            _show_message("Agentic Hardware Guarded HITL Submission Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _RunGuardedResolutionHitlPatchSubmissionCommand:
    """Patch HITL answers and run guarded submission when safe."""

    def GetResources(self):
        return {
            "MenuText": "Run Guarded HITL Patch Submission",
            "ToolTip": "Patch HITL answers, then run guarded source/spec submission only if preflight passes.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = run_guarded_hitl_patch_submission_for_workspace(document=document)
            summary = format_resolution_hitl_patch_guarded_submission_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Guarded HITL Patch Submission", summary)
        except Exception as exc:
            _print_error(f"Hardware guarded HITL patch submission failed: {exc}")
            _show_message("Agentic Hardware Guarded HITL Patch Submission Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _RunGuardedResolutionHitlSourceResponseSubmissionCommand:
    """Apply source assertion responses and run guarded HITL submission when safe."""

    def GetResources(self):
        return {
            "MenuText": "Run Guarded HITL Source Response Submission",
            "ToolTip": "Apply source assertion responses, then run guarded source/spec submission only if safe.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = run_guarded_hitl_source_response_submission_for_workspace(document=document)
            summary = format_resolution_hitl_source_response_guarded_submission_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Guarded HITL Source Response Submission", summary)
        except Exception as exc:
            _print_error(f"Hardware guarded HITL source response submission failed: {exc}")
            _show_message("Agentic Hardware Guarded HITL Source Response Submission Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionBlockerResponseTemplateCommand:
    """Build a fillable response template for the current blocker packet."""

    def GetResources(self):
        return {
            "MenuText": "Build Blocker Response Template",
            "ToolTip": "Write a fillable answer template for blocked source/spec requests.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_blocker_response_template_for_workspace(document=document)
            summary = format_resolution_blocker_response_template_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Blocker Response Template", summary)
        except Exception as exc:
            _print_error(f"Hardware blocker response template build failed: {exc}")
            _show_message("Agentic Hardware Blocker Response Template Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionAnswerSelectionTemplateCommand:
    """Build a fillable template for selecting answer candidates."""

    def GetResources(self):
        return {
            "MenuText": "Build Answer Selection Template",
            "ToolTip": "Write a human-editable template for selecting answer candidates.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_answer_selection_template_for_workspace(document=document)
            summary = format_resolution_answer_selection_template_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Answer Selection Template", summary)
        except Exception as exc:
            _print_error(f"Hardware answer selection template build failed: {exc}")
            _show_message("Agentic Hardware Answer Selection Template Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionManualCompletionTemplateCommand:
    """Build a manual source/spec completion template."""

    def GetResources(self):
        return {
            "MenuText": "Build Manual Completion Template",
            "ToolTip": "Write a source-backed manual completion template for blocked hardware inputs.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_manual_completion_template_for_workspace(document=document)
            summary = format_resolution_manual_completion_template_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Manual Completion Template", summary)
        except Exception as exc:
            _print_error(f"Hardware manual completion template build failed: {exc}")
            _show_message("Agentic Hardware Manual Completion Template Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ApplyResolutionManualCompletionCommand:
    """Apply source-backed manual completions into blocker responses."""

    def GetResources(self):
        return {
            "MenuText": "Apply Manual Completion",
            "ToolTip": "Copy source-backed manual completions into the blocker response template.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = apply_resolution_manual_completion_for_workspace(document=document)
            summary = format_resolution_manual_completion_apply_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Manual Completion", summary)
        except Exception as exc:
            _print_error(f"Hardware manual completion apply failed: {exc}")
            _show_message("Agentic Hardware Manual Completion Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _PreflightResolutionManualCompletionCommand:
    """Preflight source-backed manual completions before submission."""

    def GetResources(self):
        return {
            "MenuText": "Preflight Manual Completion",
            "ToolTip": "Validate source-backed manual completions before recording source/spec decisions.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = preflight_resolution_manual_completion_for_workspace(document=document)
            summary = format_resolution_manual_completion_preflight_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Manual Completion Preflight", summary)
        except Exception as exc:
            _print_error(f"Hardware manual completion preflight failed: {exc}")
            _show_message("Agentic Hardware Manual Completion Preflight Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ApplyResolutionAnswerSelectionCommand:
    """Apply selected answer candidates into the blocker response template."""

    def GetResources(self):
        return {
            "MenuText": "Apply Answer Selection",
            "ToolTip": "Copy selected answer candidates into the blocker response template without committing CAD.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = apply_resolution_answer_selection_for_workspace(document=document)
            summary = format_resolution_answer_selection_apply_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Answer Selection", summary)
        except Exception as exc:
            _print_error(f"Hardware answer selection apply failed: {exc}")
            _show_message("Agentic Hardware Answer Selection Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _PreflightResolutionAnswerSelectionCommand:
    """Preflight selected answer candidates through submission validation."""

    def GetResources(self):
        return {
            "MenuText": "Preflight Answer Selection",
            "ToolTip": "Validate selected answers through the submission boundary without recording decisions.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = preflight_resolution_answer_selection_for_workspace(document=document)
            summary = format_resolution_answer_preflight_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Answer Preflight", summary)
        except Exception as exc:
            _print_error(f"Hardware answer preflight failed: {exc}")
            _show_message("Agentic Hardware Answer Preflight Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _RunGuardedResolutionSubmissionCommand:
    """Run guarded submission only after answer preflight passes."""

    def GetResources(self):
        return {
            "MenuText": "Run Guarded Resolution Submission",
            "ToolTip": "Run the guarded source/spec submission flow only if answer preflight is ready.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = run_guarded_resolution_submission_for_workspace(document=document)
            summary = format_resolution_guarded_submission_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Guarded Submission", summary)
        except Exception as exc:
            _print_error(f"Hardware guarded submission failed: {exc}")
            _show_message("Agentic Hardware Guarded Submission Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _RunGuardedManualCompletionSubmissionCommand:
    """Run guarded submission only after manual-completion preflight passes."""

    def GetResources(self):
        return {
            "MenuText": "Run Guarded Manual Completion Submission",
            "ToolTip": "Run the guarded source/spec submission flow only if manual-completion preflight is ready.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = run_guarded_manual_completion_submission_for_workspace(document=document)
            summary = format_resolution_guarded_submission_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Manual Guarded Submission", summary)
        except Exception as exc:
            _print_error(f"Hardware manual guarded submission failed: {exc}")
            _show_message("Agentic Hardware Manual Guarded Submission Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ApplyResolutionBlockerResponsesCommand:
    """Apply filled blocker responses into the source/spec submission template."""

    def GetResources(self):
        return {
            "MenuText": "Apply Blocker Responses",
            "ToolTip": "Validate blocker answers and copy them into the hardware input submission template.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = apply_resolution_blocker_responses_for_workspace(document=document)
            summary = format_resolution_blocker_response_apply_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Blocker Responses", summary)
        except Exception as exc:
            _print_error(f"Hardware blocker response apply failed: {exc}")
            _show_message("Agentic Hardware Blocker Responses Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _BuildResolutionInputConfirmationsCommand:
    """Build explicit human-confirmation requests from input draft candidates."""

    def GetResources(self):
        return {
            "MenuText": "Build Resolution Input Confirmations",
            "ToolTip": "List draft candidates that require explicit human confirmation before submission.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = build_resolution_input_confirmation_requests_for_workspace(document=document)
            summary = format_resolution_input_confirmation_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Input Confirmations", summary)
        except Exception as exc:
            _print_error(f"Hardware input confirmation request build failed: {exc}")
            _show_message("Agentic Hardware Input Confirmations Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _ConfirmResolutionInputCandidateCommand:
    """Confirm a selected input candidate and write a filled template."""

    def GetResources(self):
        return {
            "MenuText": "Confirm Input Candidate",
            "ToolTip": "Confirm a selected draft candidate and write a confirmed input template.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            selected = _choose_input_confirmation_candidate(document)
            report = confirm_resolution_input_candidate_for_workspace(
                document=document,
                request_id=selected["request_id"],
                candidate_id=selected["candidate_id"],
            )
            summary = format_resolution_input_confirmation_apply_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Input Confirmation Applied", summary)
        except Exception as exc:
            _print_error(f"Hardware input candidate confirmation failed: {exc}")
            _show_message("Agentic Hardware Input Candidate Confirmation Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _SubmitConfirmedResolutionInputTemplateCommand:
    """Validate and record the explicit-confirmation input template."""

    def GetResources(self):
        return {
            "MenuText": "Submit Confirmed Resolution Input",
            "ToolTip": "Submit the template produced by Confirm Input Candidate.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = submit_confirmed_resolution_input_template_for_workspace(
                document=document,
                rationale="submitted from confirmed FreeCAD input candidate",
            )
            summary = format_resolution_input_template_submit_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Confirmed Hardware Input Submitted", summary)
        except Exception as exc:
            _print_error(f"Confirmed hardware input template submission failed: {exc}")
            _show_message("Agentic Confirmed Hardware Input Submit Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _SubmitResolutionInputTemplateCommand:
    """Validate and record filled hardware input template submissions."""

    def GetResources(self):
        return {
            "MenuText": "Submit Resolution Input Template",
            "ToolTip": "Validate the filled hardware input template and record valid add_evidence/add_spec decisions.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = submit_resolution_input_template_for_workspace(document=document)
            summary = format_resolution_input_template_submit_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Hardware Input Template Submitted", summary)
        except Exception as exc:
            _print_error(f"Hardware input template submission failed: {exc}")
            _show_message("Agentic Hardware Input Template Submit Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _VisualizeHumanReviewCommand:
    """Render human-review candidates and target options in the active document."""

    def GetResources(self):
        return {
            "MenuText": "Visualize Human Review",
            "ToolTip": "Show fastener human-review candidates, target options, and geometry warnings.",
        }

    def Activated(self):
        path = _choose_review_plan_path()
        try:
            report = visualize_review_plan(path)
            summary = format_visualization_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Human Review", summary)
        except Exception as exc:
            _print_error(f"Human review visualization failed: {exc}")
            _show_message("Agentic Human Review Failed", str(exc), error=True)

    def IsActive(self):
        return True


class _RecordHumanReviewDecisionCommand:
    """Record an approve/reject/defer decision from the selected review overlay."""

    def __init__(self, action, menu_text, tooltip):
        self.action = action
        self.menu_text = menu_text
        self.tooltip = tooltip

    def GetResources(self):
        return {
            "MenuText": self.menu_text,
            "ToolTip": self.tooltip,
        }

    def Activated(self):
        try:
            overlay = _selected_review_overlay()
            report = record_overlay_decision(
                overlay,
                self.action,
                path=_choose_decisions_path(),
            )
            summary = format_decision_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Human Review Decision", summary)
        except Exception as exc:
            _print_error(f"Human review decision failed: {exc}")
            _show_message("Agentic Human Review Decision Failed", str(exc), error=True)

    def IsActive(self):
        try:
            _selected_review_overlay()
            return True
        except Exception:
            return False


class _ApplyHumanReviewDecisionsCommand:
    """Apply saved human-review decisions and open the regenerated model."""

    def GetResources(self):
        return {
            "MenuText": "Apply Human Review Decisions",
            "ToolTip": "Apply saved human-review decisions, regenerate the assembly, and open the result.",
        }

    def Activated(self):
        try:
            import FreeCAD  # type: ignore

            document = FreeCAD.ActiveDocument
        except Exception:
            document = None
        try:
            report = apply_saved_human_review_decisions(
                document=document,
                open_result=True,
            )
            summary = format_apply_summary(report)
            _print_message(summary)
            _print_message(json.dumps(report, ensure_ascii=False, indent=2))
            _show_message("Agentic Human Review Applied", summary)
        except Exception as exc:
            _print_error(f"Human review apply failed: {exc}")
            _show_message("Agentic Human Review Apply Failed", str(exc), error=True)

    def IsActive(self):
        return True


def _choose_review_plan_path():
    try:
        import FreeCAD  # type: ignore

        default = default_review_plan_path(FreeCAD.ActiveDocument)
    except Exception:
        default = default_review_plan_path(None)
    if default is not None and default.is_file():
        return default
    try:
        from PySide6 import QtWidgets
    except ImportError:
        try:
            from PySide2 import QtWidgets
        except ImportError:
            QtWidgets = None
    if QtWidgets is None:
        return default
    selected, _filter = QtWidgets.QFileDialog.getOpenFileName(
        None,
        "Open Agentic Human Review Plan",
        str(default.parent if default is not None else ""),
        "JSON files (*.json);;All files (*)",
    )
    return selected or default


def _choose_decisions_path():
    try:
        import FreeCAD  # type: ignore

        return default_decisions_path(FreeCAD.ActiveDocument)
    except Exception:
        return default_decisions_path(None)


def _selected_review_overlay():
    selection = Gui.Selection.getSelection()
    for obj in selection:
        properties = getattr(obj, "PropertiesList", [])
        if "AgenticCandidateId" in properties:
            return obj
    raise ValueError("select one AgenticHumanReview overlay object first")


def _choose_input_confirmation_candidate(document):
    report = build_resolution_input_confirmation_requests_for_workspace(document=document)
    candidates = []
    for request_item in report.get("requests", []):
        for candidate in request_item.get("candidates", []):
            label = (
                f"{request_item.get('description') or request_item.get('stable_part_id')} -> "
                f"{candidate.get('candidate_id')} "
                f"(qty={candidate.get('quantity')}, status={candidate.get('status')})"
            )
            candidates.append({
                "label": label,
                "request_id": request_item.get("request_id"),
                "candidate_id": candidate.get("candidate_id"),
            })
    if not candidates:
        raise ValueError("no input confirmation candidates are available")
    if len(candidates) == 1:
        return candidates[0]
    try:
        from PySide6 import QtWidgets
    except ImportError:
        try:
            from PySide2 import QtWidgets
        except ImportError:
            QtWidgets = None
    if QtWidgets is None:
        raise ValueError("multiple confirmation candidates require a GUI selection")
    labels = [candidate["label"] for candidate in candidates]
    selected_label, accepted = QtWidgets.QInputDialog.getItem(
        None,
        "Confirm Agentic CAD Input Candidate",
        "Choose the candidate to confirm:",
        labels,
        0,
        False,
    )
    if not accepted:
        raise ValueError("input candidate confirmation was cancelled")
    return candidates[labels.index(selected_label)]


def _choose_architectural_scan_ir_path():
    default_path = str(DEFAULT_ARCHITECTURAL_SCAN_IR)
    try:
        from PySide6 import QtWidgets
    except ImportError:
        try:
            from PySide2 import QtWidgets
        except ImportError:
            QtWidgets = None
    if QtWidgets is None:
        return default_path
    path, _ = QtWidgets.QFileDialog.getOpenFileName(
        None,
        "Import Agentic Architectural Scan IR",
        default_path,
        "Agentic BIM IR (*.json);;JSON files (*.json);;All files (*)",
    )
    return path or None


def _print_message(message):
    try:
        import FreeCAD  # type: ignore

        FreeCAD.Console.PrintMessage(str(message) + "\n")
    except Exception:
        print(message)


def _print_error(message):
    try:
        import FreeCAD  # type: ignore

        FreeCAD.Console.PrintError(str(message) + "\n")
    except Exception:
        print(message)


def _show_message(title, message, *, error=False):
    try:
        from PySide6 import QtWidgets
    except ImportError:
        try:
            from PySide2 import QtWidgets
        except ImportError:
            QtWidgets = None
    if QtWidgets is None:
        return
    if error:
        QtWidgets.QMessageBox.critical(None, title, message)
    else:
        QtWidgets.QMessageBox.information(None, title, message)


Gui.addCommand("AgenticCad_OpenChat", _OpenChatCommand())
Gui.addCommand("AgenticCad_RunSelfTest", _RunSelfTestCommand())
Gui.addCommand("AgenticCad_ReportChatPanel", _ReportChatPanelCommand())
Gui.addCommand("AgenticCad_RunPlanExecuteSmoke", _RunPlanExecuteSmokeCommand())
Gui.addCommand("AgenticCad_RunSelectionUpdateSmoke", _RunSelectionUpdateSmokeCommand())
Gui.addCommand("AgenticCad_ImportArchitecturalScan", _ImportArchitecturalScanCommand())
Gui.addCommand("AgenticCad_BuildFocusedReprobeRequest", _BuildFocusedReprobeRequestCommand())
Gui.addCommand("AgenticCad_RebuildWoodScrewCandidateReport", _RebuildWoodScrewCandidateReportCommand())
Gui.addCommand("AgenticCad_RunFocusedReprobePipeline", _RunFocusedReprobePipelineCommand())
Gui.addCommand("AgenticCad_BuildHardwareUnresolvedReport", _BuildHardwareUnresolvedReportCommand())
Gui.addCommand("AgenticCad_BuildHardwareResolutionPlan", _BuildHardwareResolutionPlanCommand())
Gui.addCommand("AgenticCad_ConfirmResolutionReject", _ConfirmResolutionRejectCommand())
Gui.addCommand("AgenticCad_ExportFastenerRejectDecisions", _ExportFastenerRejectDecisionsCommand())
Gui.addCommand("AgenticCad_BuildResolutionStatusReport", _BuildResolutionStatusReportCommand())
Gui.addCommand("AgenticCad_BuildResolutionPipelineQueue", _BuildResolutionPipelineQueueCommand())
Gui.addCommand("AgenticCad_ExecuteResolutionPipelineQueue", _ExecuteResolutionPipelineQueueCommand())
Gui.addCommand("AgenticCad_PrepareResolutionRegeneration", _PrepareResolutionRegenerationCommand())
Gui.addCommand("AgenticCad_CheckResolutionRegeneration", _CheckResolutionRegenerationCommand())
Gui.addCommand("AgenticCad_ExecuteResolutionRegeneration", _ExecuteResolutionRegenerationCommand())
Gui.addCommand("AgenticCad_BuildResolutionLayoutPatchCandidates", _BuildResolutionLayoutPatchCandidatesCommand())
Gui.addCommand("AgenticCad_ProbeResolutionLayoutPatchContacts", _ProbeResolutionLayoutPatchContactsCommand())
Gui.addCommand(
    "AgenticCad_PreviewResolutionLayoutPatchMerge",
    _MergeResolutionLayoutPatchCandidatesCommand(
        approved=False,
        menu_text="Preview Resolution Layout Patch Merge",
        tooltip="Preview guarded layout patch merge; never writes merged layout without approval.",
    ),
)
Gui.addCommand(
    "AgenticCad_ApproveResolutionLayoutPatchMerge",
    _MergeResolutionLayoutPatchCandidatesCommand(
        approved=True,
        menu_text="Approve Resolution Layout Patch Merge",
        tooltip="Merge only contact-probe-approved layout candidates after explicit approval.",
    ),
)
Gui.addCommand("AgenticCad_RegenerateResolutionLayoutPatchAssembly", _RegenerateResolutionLayoutPatchAssemblyCommand())
Gui.addCommand("AgenticCad_BuildResolutionInputRequests", _BuildResolutionInputRequestsCommand())
Gui.addCommand("AgenticCad_BuildResolutionInputTemplate", _BuildResolutionInputTemplateCommand())
Gui.addCommand("AgenticCad_BuildResolutionInputDrafts", _BuildResolutionInputDraftsCommand())
Gui.addCommand("AgenticCad_BuildResolutionBlockerPacket", _BuildResolutionBlockerPacketCommand())
Gui.addCommand("AgenticCad_BuildResolutionAnswerCandidates", _BuildResolutionAnswerCandidatesCommand())
Gui.addCommand("AgenticCad_BuildResolutionEvidencePack", _BuildResolutionEvidencePackCommand())
Gui.addCommand(
    "AgenticCad_DraftResolutionManualCompletionFromEvidence",
    _DraftResolutionManualCompletionFromEvidenceCommand(),
)
Gui.addCommand("AgenticCad_BuildResolutionHitlQuestionPacket", _BuildResolutionHitlQuestionPacketCommand())
Gui.addCommand("AgenticCad_BuildResolutionHitlAnswerPatchTemplate", _BuildResolutionHitlAnswerPatchTemplateCommand())
Gui.addCommand("AgenticCad_BuildResolutionHitlEvidenceReviewPacket", _BuildResolutionHitlEvidenceReviewPacketCommand())
Gui.addCommand("AgenticCad_PreflightResolutionHitlAnswerPatch", _PreflightResolutionHitlAnswerPatchCommand())
Gui.addCommand("AgenticCad_BuildResolutionHitlSourceAssertionPacket", _BuildResolutionHitlSourceAssertionPacketCommand())
Gui.addCommand(
    "AgenticCad_BuildResolutionHitlSourceAssertionResponseTemplate",
    _BuildResolutionHitlSourceAssertionResponseTemplateCommand(),
)
Gui.addCommand(
    "AgenticCad_BuildResolutionHitlSourceAssertionDispositionReport",
    _BuildResolutionHitlSourceAssertionDispositionReportCommand(),
)
Gui.addCommand(
    "AgenticCad_ApplyResolutionHitlSourceAssertionResponse",
    _ApplyResolutionHitlSourceAssertionResponseCommand(),
)
Gui.addCommand("AgenticCad_PatchResolutionHitlAnswers", _PatchResolutionHitlAnswersCommand())
Gui.addCommand("AgenticCad_ApplyResolutionHitlAnswers", _ApplyResolutionHitlAnswersCommand())
Gui.addCommand("AgenticCad_RunGuardedResolutionHitlSubmission", _RunGuardedResolutionHitlSubmissionCommand())
Gui.addCommand("AgenticCad_RunGuardedResolutionHitlPatchSubmission", _RunGuardedResolutionHitlPatchSubmissionCommand())
Gui.addCommand(
    "AgenticCad_RunGuardedResolutionHitlSourceResponseSubmission",
    _RunGuardedResolutionHitlSourceResponseSubmissionCommand(),
)
Gui.addCommand("AgenticCad_BuildResolutionManualCompletionTemplate", _BuildResolutionManualCompletionTemplateCommand())
Gui.addCommand("AgenticCad_ApplyResolutionManualCompletion", _ApplyResolutionManualCompletionCommand())
Gui.addCommand("AgenticCad_PreflightResolutionManualCompletion", _PreflightResolutionManualCompletionCommand())
Gui.addCommand("AgenticCad_BuildResolutionAnswerSelectionTemplate", _BuildResolutionAnswerSelectionTemplateCommand())
Gui.addCommand("AgenticCad_ApplyResolutionAnswerSelection", _ApplyResolutionAnswerSelectionCommand())
Gui.addCommand("AgenticCad_PreflightResolutionAnswerSelection", _PreflightResolutionAnswerSelectionCommand())
Gui.addCommand("AgenticCad_RunGuardedResolutionSubmission", _RunGuardedResolutionSubmissionCommand())
Gui.addCommand("AgenticCad_RunGuardedManualCompletionSubmission", _RunGuardedManualCompletionSubmissionCommand())
Gui.addCommand("AgenticCad_BuildResolutionBlockerResponseTemplate", _BuildResolutionBlockerResponseTemplateCommand())
Gui.addCommand("AgenticCad_ApplyResolutionBlockerResponses", _ApplyResolutionBlockerResponsesCommand())
Gui.addCommand("AgenticCad_BuildResolutionInputConfirmations", _BuildResolutionInputConfirmationsCommand())
Gui.addCommand("AgenticCad_ConfirmResolutionInputCandidate", _ConfirmResolutionInputCandidateCommand())
Gui.addCommand("AgenticCad_SubmitResolutionInputTemplate", _SubmitResolutionInputTemplateCommand())
Gui.addCommand("AgenticCad_SubmitConfirmedResolutionInputTemplate", _SubmitConfirmedResolutionInputTemplateCommand())
Gui.addCommand("AgenticCad_VisualizeHumanReview", _VisualizeHumanReviewCommand())
Gui.addCommand("AgenticCad_ApplyHumanReviewDecisions", _ApplyHumanReviewDecisionsCommand())
Gui.addCommand(
    "AgenticCad_ApproveHumanReviewTarget",
    _RecordHumanReviewDecisionCommand(
        "select_target",
        "Approve Selected Review Target",
        "Approve the selected human-review target option and save a decisions JSON file.",
    ),
)
Gui.addCommand(
    "AgenticCad_RejectHumanReviewCandidate",
    _RecordHumanReviewDecisionCommand(
        "reject",
        "Reject Selected Review Candidate",
        "Reject the selected human-review candidate and save a decisions JSON file.",
    ),
)
Gui.addCommand(
    "AgenticCad_DeferHumanReviewCandidate",
    _RecordHumanReviewDecisionCommand(
        "defer",
        "Defer Selected Review Candidate",
        "Defer the selected human-review candidate and save a decisions JSON file.",
    ),
)
