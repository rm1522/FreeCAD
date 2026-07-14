"""Minimal dockable chat panel scaffold."""

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtWidgets
    except ImportError:
        from PySide import QtCore, QtGui as QtWidgets  # type: ignore

from services.api_client import AgenticApiClient
from services.capability_registry import list_capabilities
from services.fastener_reports import (
    build_hardware_resolution_plan_for_workspace,
    build_hardware_unresolved_report_for_workspace,
    format_hardware_resolution_details,
    format_hardware_unresolved_details,
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
    format_resolution_answer_candidates_details,
    format_resolution_answer_selection_apply_details,
    format_resolution_answer_preflight_details,
    format_resolution_answer_selection_template_summary,
    format_resolution_blocker_packet_details,
    format_resolution_blocker_response_apply_details,
    format_resolution_blocker_response_template_summary,
    format_resolution_evidence_pack_details,
    format_resolution_hitl_answer_patch_template_details,
    format_resolution_hitl_evidence_review_details,
    format_resolution_hitl_answer_patch_details,
    format_resolution_hitl_answer_patch_preflight_details,
    format_resolution_hitl_source_assertion_details,
    format_resolution_hitl_source_assertion_disposition_details,
    format_resolution_hitl_source_assertion_response_apply_details,
    format_resolution_hitl_source_assertion_response_template_summary,
    format_resolution_hitl_answer_apply_details,
    format_resolution_hitl_guarded_submission_details,
    format_resolution_hitl_patch_guarded_submission_details,
    format_resolution_hitl_source_response_guarded_submission_details,
    format_resolution_hitl_question_packet_details,
    format_resolution_manual_completion_evidence_draft_details,
    format_resolution_input_confirmation_apply_summary,
    format_resolution_input_confirmation_details,
    format_resolution_input_requests_details,
    format_resolution_input_draft_details,
    format_resolution_input_template_summary,
    format_resolution_input_template_submit_summary,
    format_resolution_layout_patch_contact_probe_details,
    format_resolution_layout_patch_candidates_details,
    format_resolution_layout_patch_downstream_details,
    format_resolution_layout_patch_merge_details,
    format_resolution_manual_completion_apply_details,
    format_resolution_manual_completion_preflight_details,
    format_resolution_manual_completion_template_summary,
    format_resolution_pipeline_execution_details,
    format_resolution_pipeline_queue_details,
    format_resolution_regeneration_check_details,
    format_resolution_regeneration_execution_details,
    format_resolution_regeneration_prep_details,
    format_resolution_decision_summary,
    format_resolution_guarded_submission_details,
    format_resolution_status_details,
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
from services.local_agent_loop import run_approved_local_agent_loop
from services.native_tools import execute_plan, get_document_context, requires_user_approval
from services.plan_preview import build_plan_preview, format_plan_preview
from services.s1_gate_panel import (
    approve_s1_silhouette,
    build_s1_package,
    format_promotion_summary,
    format_s1_package_summary,
)
from services.s2_gate_panel import build_s2_package, format_s2_package_summary


CHAT_PANEL_REQUIRED_CONTROLS = (
    ("log", "Agentic CAD Log"),
    ("plan_diff_preview", "Agentic CAD Plan Diff Preview"),
    ("hardware_report_preview", "Agentic CAD Hardware Unresolved Preview"),
    ("input", "Agentic CAD Prompt"),
    ("health_button", "Health Check"),
    ("plan_button", "Plan"),
    ("hardware_report_button", "Build Hardware Unresolved Report"),
    ("hardware_resolution_button", "Build Hardware Resolution Plan"),
    ("s1_gate_button", "Build S1 Gate Package"),
    ("s1_approve_button", "Approve S1 Silhouette"),
    ("s2_gate_button", "Build S2 Gate Package"),
    ("resolution_reject_button", "Confirm Resolution Reject Action"),
    ("export_fastener_reject_button", "Export Fastener Reject Decisions"),
    ("resolution_status_button", "Build Resolution Status Report"),
    ("resolution_pipeline_queue_button", "Build Resolution Pipeline Queue"),
    ("resolution_execute_queue_button", "Execute Resolution Pipeline Queue"),
    ("resolution_regeneration_prep_button", "Prepare Resolution Regeneration"),
    ("resolution_regeneration_check_button", "Check Resolution Regeneration"),
    ("resolution_regeneration_execute_button", "Execute Resolution Regeneration"),
    ("resolution_layout_patch_button", "Build Resolution Layout Patch Candidates"),
    ("resolution_contact_probe_button", "Probe Resolution Layout Patch Contacts"),
    ("resolution_preview_merge_button", "Preview Resolution Layout Patch Merge"),
    ("resolution_approve_merge_button", "Approve Resolution Layout Patch Merge"),
    ("resolution_downstream_regeneration_button", "Regenerate Resolution Layout Patch Assembly"),
    ("resolution_inputs_button", "Build Resolution Input Requests"),
    ("resolution_template_button", "Build Resolution Input Template"),
    ("resolution_input_drafts_button", "Build Resolution Input Drafts"),
    ("resolution_blocker_packet_button", "Build Resolution Blocker Packet"),
    ("resolution_answer_candidates_button", "Build Resolution Answer Candidates"),
    ("resolution_evidence_pack_button", "Build Resolution Evidence Pack"),
    ("resolution_manual_completion_evidence_draft_button", "Draft Manual Completion From Evidence"),
    ("resolution_hitl_question_packet_button", "Build HITL Question Packet"),
    ("resolution_hitl_answer_patch_template_button", "Build HITL Answer Patch Template"),
    ("resolution_hitl_evidence_review_button", "Build HITL Evidence Review Packet"),
    ("resolution_patch_hitl_answers_button", "Patch HITL Answers"),
    ("resolution_apply_hitl_answers_button", "Apply HITL Answers"),
    ("resolution_run_guarded_hitl_submission_button", "Run Guarded HITL Submission"),
    ("resolution_run_guarded_hitl_patch_submission_button", "Run Guarded HITL Patch Submission"),
    ("resolution_manual_completion_template_button", "Build Manual Completion Template"),
    ("resolution_apply_manual_completion_button", "Apply Manual Completion"),
    ("resolution_preflight_manual_completion_button", "Preflight Manual Completion"),
    ("resolution_answer_selection_template_button", "Build Answer Selection Template"),
    ("resolution_apply_answer_selection_button", "Apply Answer Selection"),
    ("resolution_preflight_answer_selection_button", "Preflight Answer Selection"),
    ("resolution_run_guarded_submission_button", "Run Guarded Resolution Submission"),
    ("resolution_run_guarded_manual_submission_button", "Run Guarded Manual Completion Submission"),
    ("resolution_blocker_response_template_button", "Build Blocker Response Template"),
    ("resolution_apply_blocker_responses_button", "Apply Blocker Responses"),
    ("resolution_input_confirmations_button", "Build Resolution Input Confirmations"),
    ("resolution_confirm_input_candidate_button", "Confirm Resolution Input Candidate"),
    ("resolution_submit_template_button", "Submit Resolution Input Template"),
    ("resolution_submit_confirmed_template_button", "Submit Confirmed Resolution Input Template"),
    ("agent_episode_button", "Preview Agent Loop"),
    ("run_agent_loop_button", "Run Approved Agent Loop"),
    ("approval_checkbox", "Review and Approve Plan"),
    ("execute_button", "Execute Approved Plan"),
)


class ChatPanel(QtWidgets.QWidget):
    """Dockable typed-agent panel for the external FreeCAD plugin."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agentic CAD")
        self.setObjectName("AgenticCADChatPanel")
        self.pending_plan = None

        layout = QtWidgets.QVBoxLayout(self)
        self.log = QtWidgets.QTextEdit(self)
        self.log.setObjectName("AgenticCADLog")
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Agentic CAD typed tool logs will appear here.")

        self.plan_diff_preview = QtWidgets.QTextEdit(self)
        self.plan_diff_preview.setObjectName("AgenticCADPlanDiffPreview")
        self.plan_diff_preview.setReadOnly(True)
        self.plan_diff_preview.setMaximumHeight(96)
        self.plan_diff_preview.setPlaceholderText("Plan diff preview will appear here before execution.")

        self.hardware_report_preview = QtWidgets.QTextEdit(self)
        self.hardware_report_preview.setObjectName("AgenticCADHardwareUnresolvedPreview")
        self.hardware_report_preview.setReadOnly(True)
        self.hardware_report_preview.setMaximumHeight(132)
        self.hardware_report_preview.setPlaceholderText("Unresolved hardware report will appear here.")

        self.input = QtWidgets.QLineEdit(self)
        self.input.setObjectName("AgenticCADPromptInput")
        self.input.setPlaceholderText("例: 長さ80mm、幅50mm、高さ20mmの箱を作って")

        self.health_button = QtWidgets.QPushButton("Health Check", self)
        self.health_button.setObjectName("AgenticCADHealthButton")
        self.health_button.clicked.connect(self._on_health_clicked)

        self.plan_button = QtWidgets.QPushButton("Plan", self)
        self.plan_button.setObjectName("AgenticCADPlanButton")
        self.plan_button.clicked.connect(self._on_plan_clicked)

        self.hardware_report_button = QtWidgets.QPushButton("Hardware Report", self)
        self.hardware_report_button.setObjectName("AgenticCADBuildHardwareUnresolvedReportButton")
        self.hardware_report_button.clicked.connect(self._on_hardware_report_clicked)

        self.s1_gate_button = QtWidgets.QPushButton("S1 Gate Package", self)
        self.s1_gate_button.setObjectName("AgenticCADS1GateButton")
        self.s1_gate_button.clicked.connect(self._on_s1_gate_clicked)

        self.s1_approve_button = QtWidgets.QPushButton("Approve S1 Silhouette", self)
        self.s1_approve_button.setObjectName("AgenticCADS1ApproveButton")
        self.s1_approve_button.clicked.connect(self._on_s1_approve_clicked)
        self._s1_last_package_dir = ""
        self._s1_reviewer_override = None
        self._s1_rationale_override = None

        self.s2_gate_button = QtWidgets.QPushButton("S2 Gate Package", self)
        self.s2_gate_button.setObjectName("AgenticCADS2GateButton")
        self.s2_gate_button.clicked.connect(self._on_s2_gate_clicked)
        self._s2_last_package_dir = ""

        self.hardware_resolution_button = QtWidgets.QPushButton("Resolution Plan", self)
        self.hardware_resolution_button.setObjectName("AgenticCADBuildHardwareResolutionPlanButton")
        self.hardware_resolution_button.clicked.connect(self._on_hardware_resolution_clicked)

        self.resolution_reject_button = QtWidgets.QPushButton("Confirm Reject Action", self)
        self.resolution_reject_button.setObjectName("AgenticCADConfirmResolutionRejectButton")
        self.resolution_reject_button.clicked.connect(self._on_resolution_reject_clicked)

        self.export_fastener_reject_button = QtWidgets.QPushButton("Export Fastener Rejects", self)
        self.export_fastener_reject_button.setObjectName("AgenticCADExportFastenerRejectDecisionsButton")
        self.export_fastener_reject_button.clicked.connect(self._on_export_fastener_reject_clicked)

        self.resolution_status_button = QtWidgets.QPushButton("Resolution Status", self)
        self.resolution_status_button.setObjectName("AgenticCADBuildResolutionStatusReportButton")
        self.resolution_status_button.clicked.connect(self._on_resolution_status_clicked)

        self.resolution_pipeline_queue_button = QtWidgets.QPushButton("Pipeline Queue", self)
        self.resolution_pipeline_queue_button.setObjectName("AgenticCADBuildResolutionPipelineQueueButton")
        self.resolution_pipeline_queue_button.clicked.connect(self._on_resolution_pipeline_queue_clicked)

        self.resolution_execute_queue_button = QtWidgets.QPushButton("Execute Queue", self)
        self.resolution_execute_queue_button.setObjectName("AgenticCADExecuteResolutionPipelineQueueButton")
        self.resolution_execute_queue_button.clicked.connect(self._on_resolution_execute_queue_clicked)

        self.resolution_regeneration_prep_button = QtWidgets.QPushButton("Regeneration Prep", self)
        self.resolution_regeneration_prep_button.setObjectName("AgenticCADPrepareResolutionRegenerationButton")
        self.resolution_regeneration_prep_button.clicked.connect(self._on_resolution_regeneration_prep_clicked)

        self.resolution_regeneration_check_button = QtWidgets.QPushButton("Regeneration Check", self)
        self.resolution_regeneration_check_button.setObjectName("AgenticCADCheckResolutionRegenerationButton")
        self.resolution_regeneration_check_button.clicked.connect(self._on_resolution_regeneration_check_clicked)

        self.resolution_regeneration_execute_button = QtWidgets.QPushButton("Execute Regeneration", self)
        self.resolution_regeneration_execute_button.setObjectName("AgenticCADExecuteResolutionRegenerationButton")
        self.resolution_regeneration_execute_button.clicked.connect(self._on_resolution_regeneration_execute_clicked)

        self.resolution_layout_patch_button = QtWidgets.QPushButton("Layout Patch Candidates", self)
        self.resolution_layout_patch_button.setObjectName("AgenticCADBuildResolutionLayoutPatchCandidatesButton")
        self.resolution_layout_patch_button.clicked.connect(self._on_resolution_layout_patch_clicked)

        self.resolution_contact_probe_button = QtWidgets.QPushButton("Probe Layout Contacts", self)
        self.resolution_contact_probe_button.setObjectName("AgenticCADProbeResolutionLayoutPatchContactsButton")
        self.resolution_contact_probe_button.clicked.connect(self._on_resolution_contact_probe_clicked)

        self.resolution_preview_merge_button = QtWidgets.QPushButton("Preview Layout Merge", self)
        self.resolution_preview_merge_button.setObjectName("AgenticCADPreviewResolutionLayoutPatchMergeButton")
        self.resolution_preview_merge_button.clicked.connect(self._on_resolution_preview_merge_clicked)

        self.resolution_approve_merge_button = QtWidgets.QPushButton("Approve Layout Merge", self)
        self.resolution_approve_merge_button.setObjectName("AgenticCADApproveResolutionLayoutPatchMergeButton")
        self.resolution_approve_merge_button.clicked.connect(self._on_resolution_approve_merge_clicked)

        self.resolution_downstream_regeneration_button = QtWidgets.QPushButton("Regenerate Layout Patch Assembly", self)
        self.resolution_downstream_regeneration_button.setObjectName(
            "AgenticCADRegenerateResolutionLayoutPatchAssemblyButton"
        )
        self.resolution_downstream_regeneration_button.clicked.connect(
            self._on_resolution_downstream_regeneration_clicked
        )

        self.resolution_inputs_button = QtWidgets.QPushButton("Input Requests", self)
        self.resolution_inputs_button.setObjectName("AgenticCADBuildResolutionInputRequestsButton")
        self.resolution_inputs_button.clicked.connect(self._on_resolution_inputs_clicked)

        self.resolution_template_button = QtWidgets.QPushButton("Input Template", self)
        self.resolution_template_button.setObjectName("AgenticCADBuildResolutionInputTemplateButton")
        self.resolution_template_button.clicked.connect(self._on_resolution_template_clicked)

        self.resolution_input_drafts_button = QtWidgets.QPushButton("Input Drafts", self)
        self.resolution_input_drafts_button.setObjectName("AgenticCADBuildResolutionInputDraftsButton")
        self.resolution_input_drafts_button.clicked.connect(self._on_resolution_input_drafts_clicked)

        self.resolution_blocker_packet_button = QtWidgets.QPushButton("Blocker Packet", self)
        self.resolution_blocker_packet_button.setObjectName("AgenticCADBuildResolutionBlockerPacketButton")
        self.resolution_blocker_packet_button.clicked.connect(self._on_resolution_blocker_packet_clicked)

        self.resolution_answer_candidates_button = QtWidgets.QPushButton("Answer Candidates", self)
        self.resolution_answer_candidates_button.setObjectName("AgenticCADBuildResolutionAnswerCandidatesButton")
        self.resolution_answer_candidates_button.clicked.connect(self._on_resolution_answer_candidates_clicked)

        self.resolution_evidence_pack_button = QtWidgets.QPushButton("Evidence Pack", self)
        self.resolution_evidence_pack_button.setObjectName("AgenticCADBuildResolutionEvidencePackButton")
        self.resolution_evidence_pack_button.clicked.connect(self._on_resolution_evidence_pack_clicked)

        self.resolution_manual_completion_evidence_draft_button = QtWidgets.QPushButton(
            "Draft Manual From Evidence",
            self,
        )
        self.resolution_manual_completion_evidence_draft_button.setObjectName(
            "AgenticCADDraftResolutionManualCompletionFromEvidenceButton"
        )
        self.resolution_manual_completion_evidence_draft_button.clicked.connect(
            self._on_resolution_manual_completion_evidence_draft_clicked
        )

        self.resolution_hitl_question_packet_button = QtWidgets.QPushButton("HITL Questions", self)
        self.resolution_hitl_question_packet_button.setObjectName(
            "AgenticCADBuildResolutionHitlQuestionPacketButton"
        )
        self.resolution_hitl_question_packet_button.clicked.connect(
            self._on_resolution_hitl_question_packet_clicked
        )

        self.resolution_hitl_answer_patch_template_button = QtWidgets.QPushButton("HITL Patch Template", self)
        self.resolution_hitl_answer_patch_template_button.setObjectName(
            "AgenticCADBuildResolutionHitlAnswerPatchTemplateButton"
        )
        self.resolution_hitl_answer_patch_template_button.clicked.connect(
            self._on_resolution_hitl_answer_patch_template_clicked
        )

        self.resolution_hitl_evidence_review_button = QtWidgets.QPushButton("HITL Evidence Review", self)
        self.resolution_hitl_evidence_review_button.setObjectName(
            "AgenticCADBuildResolutionHitlEvidenceReviewPacketButton"
        )
        self.resolution_hitl_evidence_review_button.clicked.connect(
            self._on_resolution_hitl_evidence_review_clicked
        )

        self.resolution_patch_hitl_answers_button = QtWidgets.QPushButton("Patch HITL Answers", self)
        self.resolution_patch_hitl_answers_button.setObjectName("AgenticCADPatchResolutionHitlAnswersButton")
        self.resolution_patch_hitl_answers_button.clicked.connect(self._on_resolution_patch_hitl_answers_clicked)

        self.resolution_preflight_hitl_answer_patch_button = QtWidgets.QPushButton("Preflight HITL Patch", self)
        self.resolution_preflight_hitl_answer_patch_button.setObjectName(
            "AgenticCADPreflightResolutionHitlAnswerPatchButton"
        )
        self.resolution_preflight_hitl_answer_patch_button.clicked.connect(
            self._on_resolution_preflight_hitl_answer_patch_clicked
        )

        self.resolution_hitl_source_assertion_button = QtWidgets.QPushButton("HITL Source Assertions", self)
        self.resolution_hitl_source_assertion_button.setObjectName(
            "AgenticCADBuildResolutionHitlSourceAssertionPacketButton"
        )
        self.resolution_hitl_source_assertion_button.clicked.connect(
            self._on_resolution_hitl_source_assertion_clicked
        )

        self.resolution_hitl_source_response_template_button = QtWidgets.QPushButton(
            "HITL Source Response Template",
            self,
        )
        self.resolution_hitl_source_response_template_button.setObjectName(
            "AgenticCADBuildResolutionHitlSourceAssertionResponseTemplateButton"
        )
        self.resolution_hitl_source_response_template_button.clicked.connect(
            self._on_resolution_hitl_source_response_template_clicked
        )

        self.resolution_hitl_source_disposition_button = QtWidgets.QPushButton(
            "HITL Source Disposition",
            self,
        )
        self.resolution_hitl_source_disposition_button.setObjectName(
            "AgenticCADBuildResolutionHitlSourceAssertionDispositionReportButton"
        )
        self.resolution_hitl_source_disposition_button.clicked.connect(
            self._on_resolution_hitl_source_disposition_clicked
        )

        self.resolution_apply_hitl_source_response_button = QtWidgets.QPushButton(
            "Apply HITL Source Response",
            self,
        )
        self.resolution_apply_hitl_source_response_button.setObjectName(
            "AgenticCADApplyResolutionHitlSourceAssertionResponseButton"
        )
        self.resolution_apply_hitl_source_response_button.clicked.connect(
            self._on_resolution_apply_hitl_source_response_clicked
        )

        self.resolution_apply_hitl_answers_button = QtWidgets.QPushButton("Apply HITL Answers", self)
        self.resolution_apply_hitl_answers_button.setObjectName("AgenticCADApplyResolutionHitlAnswersButton")
        self.resolution_apply_hitl_answers_button.clicked.connect(self._on_resolution_apply_hitl_answers_clicked)

        self.resolution_run_guarded_hitl_submission_button = QtWidgets.QPushButton(
            "Run Guarded HITL Submission",
            self,
        )
        self.resolution_run_guarded_hitl_submission_button.setObjectName(
            "AgenticCADRunGuardedResolutionHitlSubmissionButton"
        )
        self.resolution_run_guarded_hitl_submission_button.clicked.connect(
            self._on_resolution_run_guarded_hitl_submission_clicked
        )

        self.resolution_run_guarded_hitl_patch_submission_button = QtWidgets.QPushButton(
            "Run Guarded HITL Patch Submission",
            self,
        )
        self.resolution_run_guarded_hitl_patch_submission_button.setObjectName(
            "AgenticCADRunGuardedResolutionHitlPatchSubmissionButton"
        )
        self.resolution_run_guarded_hitl_patch_submission_button.clicked.connect(
            self._on_resolution_run_guarded_hitl_patch_submission_clicked
        )

        self.resolution_run_guarded_hitl_source_response_submission_button = QtWidgets.QPushButton(
            "Run Guarded HITL Source Response Submission",
            self,
        )
        self.resolution_run_guarded_hitl_source_response_submission_button.setObjectName(
            "AgenticCADRunGuardedResolutionHitlSourceResponseSubmissionButton"
        )
        self.resolution_run_guarded_hitl_source_response_submission_button.clicked.connect(
            self._on_resolution_run_guarded_hitl_source_response_submission_clicked
        )

        self.resolution_manual_completion_template_button = QtWidgets.QPushButton("Manual Completion Template", self)
        self.resolution_manual_completion_template_button.setObjectName(
            "AgenticCADBuildResolutionManualCompletionTemplateButton"
        )
        self.resolution_manual_completion_template_button.clicked.connect(
            self._on_resolution_manual_completion_template_clicked
        )

        self.resolution_apply_manual_completion_button = QtWidgets.QPushButton("Apply Manual Completion", self)
        self.resolution_apply_manual_completion_button.setObjectName("AgenticCADApplyResolutionManualCompletionButton")
        self.resolution_apply_manual_completion_button.clicked.connect(
            self._on_resolution_apply_manual_completion_clicked
        )

        self.resolution_preflight_manual_completion_button = QtWidgets.QPushButton("Preflight Manual Completion", self)
        self.resolution_preflight_manual_completion_button.setObjectName(
            "AgenticCADPreflightResolutionManualCompletionButton"
        )
        self.resolution_preflight_manual_completion_button.clicked.connect(
            self._on_resolution_preflight_manual_completion_clicked
        )

        self.resolution_answer_selection_template_button = QtWidgets.QPushButton("Answer Selection Template", self)
        self.resolution_answer_selection_template_button.setObjectName(
            "AgenticCADBuildResolutionAnswerSelectionTemplateButton"
        )
        self.resolution_answer_selection_template_button.clicked.connect(
            self._on_resolution_answer_selection_template_clicked
        )

        self.resolution_apply_answer_selection_button = QtWidgets.QPushButton("Apply Answer Selection", self)
        self.resolution_apply_answer_selection_button.setObjectName("AgenticCADApplyResolutionAnswerSelectionButton")
        self.resolution_apply_answer_selection_button.clicked.connect(
            self._on_resolution_apply_answer_selection_clicked
        )

        self.resolution_preflight_answer_selection_button = QtWidgets.QPushButton("Preflight Answer", self)
        self.resolution_preflight_answer_selection_button.setObjectName(
            "AgenticCADPreflightResolutionAnswerSelectionButton"
        )
        self.resolution_preflight_answer_selection_button.clicked.connect(
            self._on_resolution_preflight_answer_selection_clicked
        )

        self.resolution_run_guarded_submission_button = QtWidgets.QPushButton("Run Guarded Submission", self)
        self.resolution_run_guarded_submission_button.setObjectName("AgenticCADRunGuardedResolutionSubmissionButton")
        self.resolution_run_guarded_submission_button.clicked.connect(
            self._on_resolution_run_guarded_submission_clicked
        )

        self.resolution_run_guarded_manual_submission_button = QtWidgets.QPushButton(
            "Run Guarded Manual Submission",
            self,
        )
        self.resolution_run_guarded_manual_submission_button.setObjectName(
            "AgenticCADRunGuardedManualCompletionSubmissionButton"
        )
        self.resolution_run_guarded_manual_submission_button.clicked.connect(
            self._on_resolution_run_guarded_manual_submission_clicked
        )

        self.resolution_blocker_response_template_button = QtWidgets.QPushButton("Blocker Response Template", self)
        self.resolution_blocker_response_template_button.setObjectName(
            "AgenticCADBuildResolutionBlockerResponseTemplateButton"
        )
        self.resolution_blocker_response_template_button.clicked.connect(
            self._on_resolution_blocker_response_template_clicked
        )

        self.resolution_apply_blocker_responses_button = QtWidgets.QPushButton("Apply Blocker Responses", self)
        self.resolution_apply_blocker_responses_button.setObjectName(
            "AgenticCADApplyResolutionBlockerResponsesButton"
        )
        self.resolution_apply_blocker_responses_button.clicked.connect(
            self._on_resolution_apply_blocker_responses_clicked
        )

        self.resolution_input_confirmations_button = QtWidgets.QPushButton("Input Confirmations", self)
        self.resolution_input_confirmations_button.setObjectName("AgenticCADBuildResolutionInputConfirmationsButton")
        self.resolution_input_confirmations_button.clicked.connect(self._on_resolution_input_confirmations_clicked)

        self.resolution_confirm_input_candidate_button = QtWidgets.QPushButton("Confirm Input Candidate", self)
        self.resolution_confirm_input_candidate_button.setObjectName("AgenticCADConfirmResolutionInputCandidateButton")
        self.resolution_confirm_input_candidate_button.clicked.connect(
            self._on_resolution_confirm_input_candidate_clicked
        )

        self.resolution_submit_template_button = QtWidgets.QPushButton("Submit Input Template", self)
        self.resolution_submit_template_button.setObjectName("AgenticCADSubmitResolutionInputTemplateButton")
        self.resolution_submit_template_button.clicked.connect(self._on_resolution_submit_template_clicked)

        self.resolution_submit_confirmed_template_button = QtWidgets.QPushButton("Submit Confirmed Input", self)
        self.resolution_submit_confirmed_template_button.setObjectName(
            "AgenticCADSubmitConfirmedResolutionInputTemplateButton"
        )
        self.resolution_submit_confirmed_template_button.clicked.connect(
            self._on_resolution_submit_confirmed_template_clicked
        )

        self.agent_episode_button = QtWidgets.QPushButton("Preview Agent Loop", self)
        self.agent_episode_button.setObjectName("AgenticCADPreviewAgentLoopButton")
        self.agent_episode_button.clicked.connect(self._on_agent_episode_clicked)

        self.run_agent_loop_button = QtWidgets.QPushButton("Run Approved Agent Loop", self)
        self.run_agent_loop_button.setObjectName("AgenticCADRunApprovedAgentLoopButton")
        self.run_agent_loop_button.clicked.connect(self._on_run_agent_loop_clicked)

        self.approval_checkbox = QtWidgets.QCheckBox("I reviewed this mutating plan and approve execution", self)
        self.approval_checkbox.setObjectName("AgenticCADApprovalCheckbox")
        self.approval_checkbox.setEnabled(False)
        self.approval_checkbox.stateChanged.connect(self._on_approval_changed)

        self.execute_button = QtWidgets.QPushButton("Execute Approved Plan", self)
        self.execute_button.setObjectName("AgenticCADExecuteApprovedPlanButton")
        self.execute_button.setEnabled(False)
        self.execute_button.clicked.connect(self._on_execute_clicked)

        self.client = AgenticApiClient()

        layout.addWidget(self.log)
        layout.addWidget(self.plan_diff_preview)
        layout.addWidget(self.hardware_report_preview)
        layout.addWidget(self.input)
        layout.addWidget(self.health_button)
        layout.addWidget(self.plan_button)
        layout.addWidget(self.s1_gate_button)
        layout.addWidget(self.s1_approve_button)
        layout.addWidget(self.s2_gate_button)
        layout.addWidget(self.hardware_report_button)
        layout.addWidget(self.hardware_resolution_button)
        layout.addWidget(self.resolution_reject_button)
        layout.addWidget(self.export_fastener_reject_button)
        layout.addWidget(self.resolution_status_button)
        layout.addWidget(self.resolution_pipeline_queue_button)
        layout.addWidget(self.resolution_execute_queue_button)
        layout.addWidget(self.resolution_regeneration_prep_button)
        layout.addWidget(self.resolution_regeneration_check_button)
        layout.addWidget(self.resolution_regeneration_execute_button)
        layout.addWidget(self.resolution_layout_patch_button)
        layout.addWidget(self.resolution_contact_probe_button)
        layout.addWidget(self.resolution_preview_merge_button)
        layout.addWidget(self.resolution_approve_merge_button)
        layout.addWidget(self.resolution_downstream_regeneration_button)
        layout.addWidget(self.resolution_inputs_button)
        layout.addWidget(self.resolution_template_button)
        layout.addWidget(self.resolution_input_drafts_button)
        layout.addWidget(self.resolution_blocker_packet_button)
        layout.addWidget(self.resolution_answer_candidates_button)
        layout.addWidget(self.resolution_evidence_pack_button)
        layout.addWidget(self.resolution_manual_completion_evidence_draft_button)
        layout.addWidget(self.resolution_hitl_question_packet_button)
        layout.addWidget(self.resolution_hitl_answer_patch_template_button)
        layout.addWidget(self.resolution_hitl_evidence_review_button)
        layout.addWidget(self.resolution_preflight_hitl_answer_patch_button)
        layout.addWidget(self.resolution_hitl_source_assertion_button)
        layout.addWidget(self.resolution_hitl_source_response_template_button)
        layout.addWidget(self.resolution_hitl_source_disposition_button)
        layout.addWidget(self.resolution_apply_hitl_source_response_button)
        layout.addWidget(self.resolution_patch_hitl_answers_button)
        layout.addWidget(self.resolution_apply_hitl_answers_button)
        layout.addWidget(self.resolution_run_guarded_hitl_submission_button)
        layout.addWidget(self.resolution_run_guarded_hitl_patch_submission_button)
        layout.addWidget(self.resolution_run_guarded_hitl_source_response_submission_button)
        layout.addWidget(self.resolution_manual_completion_template_button)
        layout.addWidget(self.resolution_apply_manual_completion_button)
        layout.addWidget(self.resolution_preflight_manual_completion_button)
        layout.addWidget(self.resolution_answer_selection_template_button)
        layout.addWidget(self.resolution_apply_answer_selection_button)
        layout.addWidget(self.resolution_preflight_answer_selection_button)
        layout.addWidget(self.resolution_run_guarded_submission_button)
        layout.addWidget(self.resolution_run_guarded_manual_submission_button)
        layout.addWidget(self.resolution_blocker_response_template_button)
        layout.addWidget(self.resolution_apply_blocker_responses_button)
        layout.addWidget(self.resolution_input_confirmations_button)
        layout.addWidget(self.resolution_confirm_input_candidate_button)
        layout.addWidget(self.resolution_submit_template_button)
        layout.addWidget(self.resolution_submit_confirmed_template_button)
        layout.addWidget(self.agent_episode_button)
        layout.addWidget(self.run_agent_loop_button)
        layout.addWidget(self.approval_checkbox)
        layout.addWidget(self.execute_button)

    def _on_health_clicked(self):
        self.health_button.setEnabled(False)
        try:
            status = self.client.health()
            self.log.append(f"[health] ok={status.get('ok')} checks={status.get('checks', {})}")
        except Exception as exc:
            self.log.append(f"[health:error] {exc}")
        finally:
            self.health_button.setEnabled(True)

    def _on_s1_gate_clicked(self):
        self.s1_gate_button.setEnabled(False)
        self.hardware_report_preview.clear()
        try:
            package = build_s1_package(_active_document())
            self._s1_last_package_dir = str(package.get("package_dir") or "")
            self.hardware_report_preview.setPlainText(format_s1_package_summary(package))
            gate_report = package.get("gate_report", {})
            self.log.append(
                f"[s1-gate] {gate_report.get('status')} solids={gate_report.get('solid_count')} "
                f"interferences={gate_report.get('interference_count')} renders={len(package.get('renders') or [])}"
            )
            self.log.append(f"[s1-gate:file] {self._s1_last_package_dir}")
        except Exception as exc:
            self.log.append(f"[s1-gate:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.s1_gate_button.setEnabled(True)

    def _on_s1_approve_clicked(self):
        self.s1_approve_button.setEnabled(False)
        try:
            if not self._s1_last_package_dir:
                raise ValueError("Run S1 Gate Package first so there is a package to approve")
            reviewer = self._s1_reviewer_override
            rationale = self._s1_rationale_override
            if reviewer is None:
                reviewer, accepted = QtWidgets.QInputDialog.getText(
                    self, "Approve S1 Silhouette", "Reviewer name or email:"
                )
                if not accepted:
                    raise ValueError("Silhouette approval cancelled")
            if rationale is None:
                rationale, accepted = QtWidgets.QInputDialog.getText(
                    self, "Approve S1 Silhouette", "Approval rationale:"
                )
                if not accepted:
                    raise ValueError("Silhouette approval cancelled")
            result = approve_s1_silhouette(
                self._s1_last_package_dir, reviewer=str(reviewer), rationale=str(rationale)
            )
            self.hardware_report_preview.setPlainText(format_promotion_summary(result))
            promotion = result.get("promotion", {})
            self.log.append(f"[s1-approve] {promotion.get('status')} reasons={promotion.get('reasons')}")
        except Exception as exc:
            self.log.append(f"[s1-approve:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.s1_approve_button.setEnabled(True)

    def _on_s2_gate_clicked(self):
        self.s2_gate_button.setEnabled(False)
        self.hardware_report_preview.clear()
        try:
            package = build_s2_package(_active_document())
            self._s2_last_package_dir = str(package.get("package_dir") or "")
            self.hardware_report_preview.setPlainText(format_s2_package_summary(package))
            gate_report = package.get("gate_report", {})
            promotion = package.get("promotion", {})
            self.log.append(
                f"[s2-gate] {gate_report.get('status')} bodies={gate_report.get('body_count')} "
                f"features={gate_report.get('feature_count')} promotion={promotion.get('status')}"
            )
            self.log.append(f"[s2-gate:file] {self._s2_last_package_dir}")
        except Exception as exc:
            self.log.append(f"[s2-gate:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.s2_gate_button.setEnabled(True)

    def _on_hardware_report_clicked(self):
        self.hardware_report_button.setEnabled(False)
        self.hardware_report_preview.clear()
        try:
            report = build_hardware_unresolved_report_for_workspace(document=_active_document())
            details = format_hardware_unresolved_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware] {report.get('report_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_unresolved_report")
            if artifact:
                self.log.append(f"[hardware:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.hardware_report_button.setEnabled(True)

    def _on_hardware_resolution_clicked(self):
        self.hardware_resolution_button.setEnabled(False)
        self.hardware_report_preview.clear()
        try:
            report = build_hardware_resolution_plan_for_workspace(document=_active_document())
            details = format_hardware_resolution_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-resolution] {report.get('plan_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_plan")
            if artifact:
                self.log.append(f"[hardware-resolution:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-resolution:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.hardware_resolution_button.setEnabled(True)

    def _on_resolution_reject_clicked(self):
        self.resolution_reject_button.setEnabled(False)
        try:
            report = record_resolution_decision_for_workspace(
                document=_active_document(),
                decision_action="confirm_reject",
                rationale="confirmed from Agentic CAD Dock",
            )
            summary = format_resolution_decision_summary(report)
            self.hardware_report_preview.setPlainText(summary)
            self.log.append(f"[hardware-resolution-decision] {summary}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_decisions")
            if artifact:
                self.log.append(f"[hardware-resolution-decision:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-resolution-decision:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_reject_button.setEnabled(True)

    def _on_export_fastener_reject_clicked(self):
        self.export_fastener_reject_button.setEnabled(False)
        try:
            report = export_fastener_reject_decisions_for_workspace(document=_active_document())
            summary = format_fastener_reject_export_summary(report)
            self.hardware_report_preview.setPlainText(summary)
            self.log.append(f"[fastener-reject-export] {summary}")
        except Exception as exc:
            self.log.append(f"[fastener-reject-export:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.export_fastener_reject_button.setEnabled(True)

    def _on_resolution_status_clicked(self):
        self.resolution_status_button.setEnabled(False)
        try:
            report = build_resolution_status_report_for_workspace(document=_active_document())
            details = format_resolution_status_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-resolution-status] {report.get('report_status')} {report.get('summary', {})}")
        except Exception as exc:
            self.log.append(f"[hardware-resolution-status:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_status_button.setEnabled(True)

    def _on_resolution_pipeline_queue_clicked(self):
        self.resolution_pipeline_queue_button.setEnabled(False)
        try:
            report = build_resolution_pipeline_queue_for_workspace(document=_active_document())
            details = format_resolution_pipeline_queue_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-pipeline-queue] {report.get('queue_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_pipeline_queue")
            if artifact:
                self.log.append(f"[hardware-pipeline-queue:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-pipeline-queue:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_pipeline_queue_button.setEnabled(True)

    def _on_resolution_execute_queue_clicked(self):
        self.resolution_execute_queue_button.setEnabled(False)
        try:
            report = execute_resolution_pipeline_queue_for_workspace(document=_active_document())
            details = format_resolution_pipeline_execution_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-pipeline-exec] {report.get('execution_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_pipeline_execution_report")
            if artifact:
                self.log.append(f"[hardware-pipeline-exec:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-pipeline-exec:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_execute_queue_button.setEnabled(True)

    def _on_resolution_regeneration_prep_clicked(self):
        self.resolution_regeneration_prep_button.setEnabled(False)
        try:
            report = prepare_resolution_regeneration_inputs_for_workspace(document=_active_document())
            details = format_resolution_regeneration_prep_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-regeneration-prep] {report.get('prep_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_regeneration_prep_report")
            if artifact:
                self.log.append(f"[hardware-regeneration-prep:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-regeneration-prep:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_regeneration_prep_button.setEnabled(True)

    def _on_resolution_regeneration_check_clicked(self):
        self.resolution_regeneration_check_button.setEnabled(False)
        try:
            report = check_resolution_regeneration_readiness_for_workspace(document=_active_document())
            details = format_resolution_regeneration_check_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-regeneration-check] {report.get('check_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_regeneration_check_report")
            if artifact:
                self.log.append(f"[hardware-regeneration-check:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-regeneration-check:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_regeneration_check_button.setEnabled(True)

    def _on_resolution_regeneration_execute_clicked(self):
        self.resolution_regeneration_execute_button.setEnabled(False)
        try:
            report = execute_resolution_regeneration_for_workspace(document=_active_document())
            details = format_resolution_regeneration_execution_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-regeneration-exec] {report.get('execution_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_regeneration_execution_report")
            if artifact:
                self.log.append(f"[hardware-regeneration-exec:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-regeneration-exec:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_regeneration_execute_button.setEnabled(True)

    def _on_resolution_layout_patch_clicked(self):
        self.resolution_layout_patch_button.setEnabled(False)
        try:
            report = build_resolution_layout_patch_candidates_for_workspace(document=_active_document())
            details = format_resolution_layout_patch_candidates_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-layout-patch] {report.get('candidate_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_layout_patch_candidates")
            if artifact:
                self.log.append(f"[hardware-layout-patch:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-layout-patch:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_layout_patch_button.setEnabled(True)

    def _on_resolution_contact_probe_clicked(self):
        self.resolution_contact_probe_button.setEnabled(False)
        try:
            report = probe_resolution_layout_patch_contacts_for_workspace(document=_active_document())
            details = format_resolution_layout_patch_contact_probe_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-contact-probe] {report.get('probe_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("contact_probe_report")
            if artifact:
                self.log.append(f"[hardware-contact-probe:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-contact-probe:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_contact_probe_button.setEnabled(True)

    def _on_resolution_preview_merge_clicked(self):
        self.resolution_preview_merge_button.setEnabled(False)
        try:
            report = merge_resolution_layout_patch_candidates_for_workspace(
                document=_active_document(),
                approved=False,
                approver="freecad-dock-preview",
            )
            details = format_resolution_layout_patch_merge_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-layout-merge-preview] {report.get('merge_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_layout_patch_merge_report")
            if artifact:
                self.log.append(f"[hardware-layout-merge-preview:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-layout-merge-preview:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_preview_merge_button.setEnabled(True)

    def _on_resolution_approve_merge_clicked(self):
        self.resolution_approve_merge_button.setEnabled(False)
        try:
            report = merge_resolution_layout_patch_candidates_for_workspace(
                document=_active_document(),
                approved=True,
                approver="freecad-dock-approved",
            )
            details = format_resolution_layout_patch_merge_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-layout-merge-approved] {report.get('merge_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("merged_assembly_layout_ir")
            if artifact:
                self.log.append(f"[hardware-layout-merge-approved:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-layout-merge-approved:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_approve_merge_button.setEnabled(True)

    def _on_resolution_downstream_regeneration_clicked(self):
        self.resolution_downstream_regeneration_button.setEnabled(False)
        try:
            report = regenerate_resolution_layout_patch_assembly_for_workspace(document=_active_document())
            details = format_resolution_layout_patch_downstream_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-layout-downstream] {report.get('regeneration_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get("downstream_regeneration_report")
            if artifact:
                self.log.append(f"[hardware-layout-downstream:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-layout-downstream:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_downstream_regeneration_button.setEnabled(True)

    def _on_resolution_inputs_clicked(self):
        self.resolution_inputs_button.setEnabled(False)
        try:
            report = build_resolution_input_requests_for_workspace(document=_active_document())
            details = format_resolution_input_requests_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-input-requests] {report.get('request_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_input_requests")
            if artifact:
                self.log.append(f"[hardware-input-requests:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-input-requests:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_inputs_button.setEnabled(True)

    def _on_resolution_template_clicked(self):
        self.resolution_template_button.setEnabled(False)
        try:
            report = build_resolution_input_submission_template_for_workspace(document=_active_document())
            summary = format_resolution_input_template_summary(report)
            self.hardware_report_preview.setPlainText(summary)
            self.log.append(f"[hardware-input-template] {summary}")
        except Exception as exc:
            self.log.append(f"[hardware-input-template:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_template_button.setEnabled(True)

    def _on_resolution_input_drafts_clicked(self):
        self.resolution_input_drafts_button.setEnabled(False)
        try:
            report = build_resolution_input_drafts_for_workspace(document=_active_document())
            details = format_resolution_input_draft_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-input-drafts] {report.get('draft_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_input_draft_report")
            if artifact:
                self.log.append(f"[hardware-input-drafts:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-input-drafts:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_input_drafts_button.setEnabled(True)

    def _on_resolution_blocker_packet_clicked(self):
        self.resolution_blocker_packet_button.setEnabled(False)
        try:
            report = build_resolution_blocker_packet_for_workspace(document=_active_document())
            details = format_resolution_blocker_packet_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-blocker-packet] {report.get('packet_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_blocker_packet")
            if artifact:
                self.log.append(f"[hardware-blocker-packet:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-blocker-packet:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_blocker_packet_button.setEnabled(True)

    def _on_resolution_answer_candidates_clicked(self):
        self.resolution_answer_candidates_button.setEnabled(False)
        try:
            report = build_resolution_answer_candidates_for_workspace(document=_active_document())
            details = format_resolution_answer_candidates_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-answer-candidates] {report.get('candidate_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_answer_candidates")
            if artifact:
                self.log.append(f"[hardware-answer-candidates:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-answer-candidates:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_answer_candidates_button.setEnabled(True)

    def _on_resolution_evidence_pack_clicked(self):
        self.resolution_evidence_pack_button.setEnabled(False)
        try:
            report = build_resolution_evidence_pack_for_workspace(document=_active_document())
            details = format_resolution_evidence_pack_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-evidence-pack] {report.get('pack_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_evidence_pack")
            if artifact:
                self.log.append(f"[hardware-evidence-pack:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-evidence-pack:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_evidence_pack_button.setEnabled(True)

    def _on_resolution_manual_completion_evidence_draft_clicked(self):
        self.resolution_manual_completion_evidence_draft_button.setEnabled(False)
        try:
            report = draft_resolution_manual_completion_from_evidence_pack_for_workspace(document=_active_document())
            details = format_resolution_manual_completion_evidence_draft_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-manual-completion-evidence-draft] "
                f"{report.get('draft_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get("hardware_resolution_manual_completion_review_template")
            if artifact:
                self.log.append(f"[hardware-manual-completion-evidence-draft:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-manual-completion-evidence-draft:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_manual_completion_evidence_draft_button.setEnabled(True)

    def _on_resolution_hitl_question_packet_clicked(self):
        self.resolution_hitl_question_packet_button.setEnabled(False)
        try:
            report = build_resolution_hitl_question_packet_for_workspace(document=_active_document())
            details = format_resolution_hitl_question_packet_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-hitl-questions] {report.get('question_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_hitl_question_packet")
            if artifact:
                self.log.append(f"[hardware-hitl-questions:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-questions:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_hitl_question_packet_button.setEnabled(True)

    def _on_resolution_apply_hitl_answers_clicked(self):
        self.resolution_apply_hitl_answers_button.setEnabled(False)
        try:
            report = apply_resolution_hitl_answers_for_workspace(document=_active_document())
            details = format_resolution_hitl_answer_apply_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-hitl-answer-apply] {report.get('apply_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_hitl_answer_apply_report")
            if artifact:
                self.log.append(f"[hardware-hitl-answer-apply:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-answer-apply:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_apply_hitl_answers_button.setEnabled(True)

    def _on_resolution_hitl_answer_patch_template_clicked(self):
        self.resolution_hitl_answer_patch_template_button.setEnabled(False)
        try:
            report = build_resolution_hitl_answer_patch_template_for_workspace(document=_active_document())
            details = format_resolution_hitl_answer_patch_template_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-hitl-answer-patch-template] "
                f"{report.get('patch_template_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get("hardware_resolution_hitl_answer_patch_template")
            if artifact:
                self.log.append(f"[hardware-hitl-answer-patch-template:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-answer-patch-template:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_hitl_answer_patch_template_button.setEnabled(True)

    def _on_resolution_hitl_evidence_review_clicked(self):
        self.resolution_hitl_evidence_review_button.setEnabled(False)
        try:
            report = build_resolution_hitl_evidence_review_packet_for_workspace(document=_active_document())
            details = format_resolution_hitl_evidence_review_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-hitl-evidence-review] {report.get('review_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_hitl_evidence_review_packet")
            if artifact:
                self.log.append(f"[hardware-hitl-evidence-review:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-evidence-review:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_hitl_evidence_review_button.setEnabled(True)

    def _on_resolution_patch_hitl_answers_clicked(self):
        self.resolution_patch_hitl_answers_button.setEnabled(False)
        try:
            report = patch_resolution_hitl_answer_template_for_workspace(document=_active_document())
            details = format_resolution_hitl_answer_patch_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-hitl-answer-patch] {report.get('patch_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_hitl_answer_patch_apply_report")
            if artifact:
                self.log.append(f"[hardware-hitl-answer-patch:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-answer-patch:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_patch_hitl_answers_button.setEnabled(True)

    def _on_resolution_preflight_hitl_answer_patch_clicked(self):
        self.resolution_preflight_hitl_answer_patch_button.setEnabled(False)
        try:
            report = preflight_resolution_hitl_answer_patch_for_workspace(document=_active_document())
            details = format_resolution_hitl_answer_patch_preflight_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-hitl-answer-patch-preflight] "
                f"{report.get('preflight_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get("hardware_resolution_hitl_answer_patch_preflight_report")
            if artifact:
                self.log.append(f"[hardware-hitl-answer-patch-preflight:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-answer-patch-preflight:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_preflight_hitl_answer_patch_button.setEnabled(True)

    def _on_resolution_hitl_source_assertion_clicked(self):
        self.resolution_hitl_source_assertion_button.setEnabled(False)
        try:
            report = build_resolution_hitl_source_assertion_packet_for_workspace(document=_active_document())
            details = format_resolution_hitl_source_assertion_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-hitl-source-assertion] "
                f"{report.get('assertion_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get("hardware_resolution_hitl_source_assertion_packet")
            if artifact:
                self.log.append(f"[hardware-hitl-source-assertion:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-source-assertion:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_hitl_source_assertion_button.setEnabled(True)

    def _on_resolution_hitl_source_response_template_clicked(self):
        self.resolution_hitl_source_response_template_button.setEnabled(False)
        try:
            report = build_resolution_hitl_source_assertion_response_template_for_workspace(
                document=_active_document()
            )
            summary = format_resolution_hitl_source_assertion_response_template_summary(report)
            self.hardware_report_preview.setPlainText(summary)
            self.log.append(f"[hardware-hitl-source-response-template] {summary}")
            artifact = report.get("artifacts", {}).get(
                "hardware_resolution_hitl_source_assertion_response_template"
            )
            if artifact:
                self.log.append(f"[hardware-hitl-source-response-template:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-source-response-template:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_hitl_source_response_template_button.setEnabled(True)

    def _on_resolution_hitl_source_disposition_clicked(self):
        self.resolution_hitl_source_disposition_button.setEnabled(False)
        try:
            report = build_resolution_hitl_source_assertion_disposition_report_for_workspace(
                document=_active_document()
            )
            details = format_resolution_hitl_source_assertion_disposition_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-hitl-source-disposition] "
                f"{report.get('disposition_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get(
                "hardware_resolution_hitl_source_assertion_disposition_report"
            )
            if artifact:
                self.log.append(f"[hardware-hitl-source-disposition:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-source-disposition:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_hitl_source_disposition_button.setEnabled(True)

    def _on_resolution_apply_hitl_source_response_clicked(self):
        self.resolution_apply_hitl_source_response_button.setEnabled(False)
        try:
            report = apply_resolution_hitl_source_assertion_response_for_workspace(document=_active_document())
            details = format_resolution_hitl_source_assertion_response_apply_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-hitl-source-response-apply] "
                f"{report.get('apply_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get("hardware_resolution_hitl_source_assertion_response_apply_report")
            if artifact:
                self.log.append(f"[hardware-hitl-source-response-apply:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-source-response-apply:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_apply_hitl_source_response_button.setEnabled(True)

    def _on_resolution_run_guarded_hitl_submission_clicked(self):
        self.resolution_run_guarded_hitl_submission_button.setEnabled(False)
        try:
            report = run_guarded_hitl_submission_for_workspace(document=_active_document())
            details = format_resolution_hitl_guarded_submission_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-hitl-guarded-submission] "
                f"{report.get('guarded_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get("hardware_resolution_hitl_guarded_submission_report")
            if artifact:
                self.log.append(f"[hardware-hitl-guarded-submission:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-guarded-submission:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_run_guarded_hitl_submission_button.setEnabled(True)

    def _on_resolution_run_guarded_hitl_patch_submission_clicked(self):
        self.resolution_run_guarded_hitl_patch_submission_button.setEnabled(False)
        try:
            report = run_guarded_hitl_patch_submission_for_workspace(document=_active_document())
            details = format_resolution_hitl_patch_guarded_submission_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-hitl-patch-guarded-submission] "
                f"{report.get('guarded_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get("hardware_resolution_hitl_patch_guarded_submission_report")
            if artifact:
                self.log.append(f"[hardware-hitl-patch-guarded-submission:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-patch-guarded-submission:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_run_guarded_hitl_patch_submission_button.setEnabled(True)

    def _on_resolution_run_guarded_hitl_source_response_submission_clicked(self):
        self.resolution_run_guarded_hitl_source_response_submission_button.setEnabled(False)
        try:
            report = run_guarded_hitl_source_response_submission_for_workspace(document=_active_document())
            details = format_resolution_hitl_source_response_guarded_submission_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-hitl-source-response-guarded-submission] "
                f"{report.get('guarded_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get(
                "hardware_resolution_hitl_source_response_guarded_submission_report"
            )
            if artifact:
                self.log.append(f"[hardware-hitl-source-response-guarded-submission:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-hitl-source-response-guarded-submission:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_run_guarded_hitl_source_response_submission_button.setEnabled(True)

    def _on_resolution_manual_completion_template_clicked(self):
        self.resolution_manual_completion_template_button.setEnabled(False)
        try:
            report = build_resolution_manual_completion_template_for_workspace(document=_active_document())
            summary = format_resolution_manual_completion_template_summary(report)
            self.hardware_report_preview.setPlainText(summary)
            self.log.append(f"[hardware-manual-completion-template] {summary}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_manual_completion_template")
            if artifact:
                self.log.append(f"[hardware-manual-completion-template:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-manual-completion-template:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_manual_completion_template_button.setEnabled(True)

    def _on_resolution_apply_manual_completion_clicked(self):
        self.resolution_apply_manual_completion_button.setEnabled(False)
        try:
            report = apply_resolution_manual_completion_for_workspace(document=_active_document())
            details = format_resolution_manual_completion_apply_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-manual-completion-apply] {report.get('apply_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("manual_completion_apply_report")
            if artifact:
                self.log.append(f"[hardware-manual-completion-apply:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-manual-completion-apply:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_apply_manual_completion_button.setEnabled(True)

    def _on_resolution_preflight_manual_completion_clicked(self):
        self.resolution_preflight_manual_completion_button.setEnabled(False)
        try:
            report = preflight_resolution_manual_completion_for_workspace(document=_active_document())
            details = format_resolution_manual_completion_preflight_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-manual-completion-preflight] "
                f"{report.get('preflight_status')} ok={report.get('ok_to_submit')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get("hardware_resolution_manual_completion_preflight_report")
            if artifact:
                self.log.append(f"[hardware-manual-completion-preflight:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-manual-completion-preflight:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_preflight_manual_completion_button.setEnabled(True)

    def _on_resolution_answer_selection_template_clicked(self):
        self.resolution_answer_selection_template_button.setEnabled(False)
        try:
            report = build_resolution_answer_selection_template_for_workspace(document=_active_document())
            summary = format_resolution_answer_selection_template_summary(report)
            self.hardware_report_preview.setPlainText(summary)
            self.log.append(f"[hardware-answer-selection-template] {summary}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_answer_selection_template")
            if artifact:
                self.log.append(f"[hardware-answer-selection-template:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-answer-selection-template:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_answer_selection_template_button.setEnabled(True)

    def _on_resolution_apply_answer_selection_clicked(self):
        self.resolution_apply_answer_selection_button.setEnabled(False)
        try:
            report = apply_resolution_answer_selection_for_workspace(document=_active_document())
            details = format_resolution_answer_selection_apply_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-answer-selection-apply] {report.get('apply_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("answer_selection_apply_report")
            if artifact:
                self.log.append(f"[hardware-answer-selection-apply:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-answer-selection-apply:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_apply_answer_selection_button.setEnabled(True)

    def _on_resolution_preflight_answer_selection_clicked(self):
        self.resolution_preflight_answer_selection_button.setEnabled(False)
        try:
            report = preflight_resolution_answer_selection_for_workspace(document=_active_document())
            details = format_resolution_answer_preflight_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-answer-preflight] {report.get('preflight_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_answer_preflight_report")
            if artifact:
                self.log.append(f"[hardware-answer-preflight:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-answer-preflight:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_preflight_answer_selection_button.setEnabled(True)

    def _on_resolution_run_guarded_submission_clicked(self):
        self.resolution_run_guarded_submission_button.setEnabled(False)
        try:
            report = run_guarded_resolution_submission_for_workspace(document=_active_document())
            details = format_resolution_guarded_submission_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-guarded-submission] {report.get('guarded_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("guarded_submission_report")
            if artifact:
                self.log.append(f"[hardware-guarded-submission:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-guarded-submission:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_run_guarded_submission_button.setEnabled(True)

    def _on_resolution_run_guarded_manual_submission_clicked(self):
        self.resolution_run_guarded_manual_submission_button.setEnabled(False)
        try:
            report = run_guarded_manual_completion_submission_for_workspace(document=_active_document())
            details = format_resolution_guarded_submission_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-manual-guarded-submission] "
                f"{report.get('guarded_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get("guarded_submission_report")
            if artifact:
                self.log.append(f"[hardware-manual-guarded-submission:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-manual-guarded-submission:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_run_guarded_manual_submission_button.setEnabled(True)

    def _on_resolution_blocker_response_template_clicked(self):
        self.resolution_blocker_response_template_button.setEnabled(False)
        try:
            report = build_resolution_blocker_response_template_for_workspace(document=_active_document())
            summary = format_resolution_blocker_response_template_summary(report)
            self.hardware_report_preview.setPlainText(summary)
            self.log.append(f"[hardware-blocker-response-template] {summary}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_blocker_response_template")
            if artifact:
                self.log.append(f"[hardware-blocker-response-template:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-blocker-response-template:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_blocker_response_template_button.setEnabled(True)

    def _on_resolution_apply_blocker_responses_clicked(self):
        self.resolution_apply_blocker_responses_button.setEnabled(False)
        try:
            report = apply_resolution_blocker_responses_for_workspace(document=_active_document())
            details = format_resolution_blocker_response_apply_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(f"[hardware-blocker-response-apply] {report.get('apply_status')} {report.get('summary', {})}")
            artifact = report.get("artifacts", {}).get("blocker_response_apply_report")
            if artifact:
                self.log.append(f"[hardware-blocker-response-apply:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-blocker-response-apply:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_apply_blocker_responses_button.setEnabled(True)

    def _on_resolution_input_confirmations_clicked(self):
        self.resolution_input_confirmations_button.setEnabled(False)
        try:
            report = build_resolution_input_confirmation_requests_for_workspace(document=_active_document())
            details = format_resolution_input_confirmation_details(report)
            self.hardware_report_preview.setPlainText(details)
            self.log.append(
                f"[hardware-input-confirmations] {report.get('confirmation_status')} {report.get('summary', {})}"
            )
            artifact = report.get("artifacts", {}).get("hardware_resolution_input_confirmation_requests")
            if artifact:
                self.log.append(f"[hardware-input-confirmations:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-input-confirmations:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_input_confirmations_button.setEnabled(True)

    def _on_resolution_confirm_input_candidate_clicked(self):
        self.resolution_confirm_input_candidate_button.setEnabled(False)
        try:
            document = _active_document()
            selected = _choose_input_confirmation_candidate(document)
            report = confirm_resolution_input_candidate_for_workspace(
                document=document,
                request_id=selected["request_id"],
                candidate_id=selected["candidate_id"],
            )
            summary = format_resolution_input_confirmation_apply_summary(report)
            self.hardware_report_preview.setPlainText(summary)
            self.log.append(f"[hardware-input-confirmation-applied] {summary}")
            artifact = report.get("artifacts", {}).get("hardware_resolution_input_confirmed_template")
            if artifact:
                self.log.append(f"[hardware-input-confirmed-template:file] {artifact}")
        except Exception as exc:
            self.log.append(f"[hardware-input-confirmation-applied:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_confirm_input_candidate_button.setEnabled(True)

    def _on_resolution_submit_template_clicked(self):
        self.resolution_submit_template_button.setEnabled(False)
        try:
            report = submit_resolution_input_template_for_workspace(document=_active_document())
            summary = format_resolution_input_template_submit_summary(report)
            self.hardware_report_preview.setPlainText(summary)
            self.log.append(f"[hardware-input-template-submit] {summary}")
        except Exception as exc:
            self.log.append(f"[hardware-input-template-submit:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_submit_template_button.setEnabled(True)

    def _on_resolution_submit_confirmed_template_clicked(self):
        self.resolution_submit_confirmed_template_button.setEnabled(False)
        try:
            report = submit_confirmed_resolution_input_template_for_workspace(
                document=_active_document(),
                rationale="submitted from Agentic CAD confirmed input button",
            )
            summary = format_resolution_input_template_submit_summary(report)
            self.hardware_report_preview.setPlainText(summary)
            self.log.append(f"[hardware-input-confirmed-template-submit] {summary}")
        except Exception as exc:
            self.log.append(f"[hardware-input-confirmed-template-submit:error] {exc}")
            self.hardware_report_preview.setPlainText(str(exc))
        finally:
            self.resolution_submit_confirmed_template_button.setEnabled(True)

    def _on_plan_clicked(self):
        text = self.input.text().strip()
        if not text:
            return
        self.log.append(f"> {text}")
        self.plan_button.setEnabled(False)
        self._reset_approval_ui()
        self._set_plan_diff_preview([])
        self.input.setEnabled(False)
        try:
            context = get_document_context()
            capabilities = list_capabilities()
            self.log.append(f"[context] objects={len(context.get('objects', []))}, selection={len(context.get('selection', []))}")
            plan = self.client.plan_freecad(text, context, capabilities)
            self.pending_plan = plan if plan.get("status") == "ready" else None
            self._log_plan(plan, context)
            if plan.get("status") != "ready":
                for question in plan.get("questions", []):
                    self.log.append(f"[question] {question}")
                return
            if requires_user_approval(plan):
                self.log.append("[approval] This plan will mutate the document. Review the diff and check approval before executing.")
                self._set_approval_required(True)
            else:
                self.log.append("[approval] Non-mutating plan is ready.")
                self._set_approval_required(False)
        except Exception as exc:
            self.log.append(f"[error] {exc}")
        finally:
            self.plan_button.setEnabled(True)
            self.input.setEnabled(True)
            self.input.clear()

    def _on_agent_episode_clicked(self):
        text = self.input.text().strip()
        if not text:
            return
        self.log.append(f"> {text}")
        self.agent_episode_button.setEnabled(False)
        self.input.setEnabled(False)
        try:
            context = get_document_context()
            capabilities = list_capabilities()
            episode = self.client.run_freecad_agent_episode(
                text,
                context,
                capabilities,
                approved=False,
                simulate_execution=True,
            )
            self.log.append(
                f"[agent] status={episode.get('status')} iterations={episode.get('iterations')}"
            )
            for question in episode.get("questions", []):
                self.log.append(f"[agent:question] {question}")
            for event in episode.get("trace_events", []):
                self.log.append(f"[agent:trace] {event.get('event')}")
        except Exception as exc:
            self.log.append(f"[agent:error] {exc}")
        finally:
            self.agent_episode_button.setEnabled(True)
            self.input.setEnabled(True)

    def _on_run_agent_loop_clicked(self):
        text = self.input.text().strip()
        if not text:
            return
        self.log.append(f"> {text}")
        self.run_agent_loop_button.setEnabled(False)
        self.plan_button.setEnabled(False)
        self._reset_approval_ui()
        self.input.setEnabled(False)
        try:
            report = run_approved_local_agent_loop(text)
            self.log.append(
                f"[agent:run] status={report.get('status')} iterations={report.get('iterations')}"
            )
            verification = report.get("verification") or {}
            if verification:
                self.log.append(
                    f"[agent:verify] {verification.get('status')} {verification.get('summary')}"
                )
            for result in report.get("tool_results", []):
                output = result.get("output") or {}
                self.log.append(f"[agent:tool] ok={result.get('ok')} {output.get('summary', '')}")
            if report.get("report_path"):
                self.log.append(f"[agent:trace:file] {report.get('report_path')}")
        except Exception as exc:
            self.log.append(f"[agent:run:error] {exc}")
        finally:
            self.run_agent_loop_button.setEnabled(True)
            self.plan_button.setEnabled(True)
            self.input.setEnabled(True)

    def _on_execute_clicked(self):
        if not self.pending_plan:
            self.log.append("[execute] No ready plan to execute.")
            return
        if requires_user_approval(self.pending_plan) and not self.approval_checkbox.isChecked():
            self.log.append("[approval:error] Review and approve the mutating plan before execution.")
            self.execute_button.setEnabled(False)
            return
        self.execute_button.setEnabled(False)
        self.plan_button.setEnabled(False)
        self.input.setEnabled(False)
        try:
            self.log.append("[execute] Running approved typed plan...")
            result = execute_plan(self.pending_plan, approved=True)
            self.pending_plan = None
            summary = f"[executed] {result.get('summary', '')}"
            self._set_plan_diff_preview([])
            self._reset_approval_ui()
            _console_message(summary)
            for evidence in result.get("evidence", []):
                obj = evidence.get("object", {})
                shape = obj.get("shape") or {}
                _console_message(
                    f"[evidence] {obj.get('label') or obj.get('name')}: "
                    f"bbox={shape.get('bbox_mm')} volume={shape.get('volume_mm3')}"
                )
            _show_info("Agentic CAD Execute", summary)
        except Exception as exc:
            self.log.append(f"[error] {exc}")
        finally:
            self.plan_button.setEnabled(True)
            self.input.setEnabled(True)

    def _log_plan(self, plan, context=None):
        self.log.append(f"[plan] {plan.get('status')} {plan.get('plan_id', '')}")
        explanation = plan.get("explanation")
        if explanation:
            self.log.append(f"[plan] {explanation}")
        for operation in plan.get("operations", []):
            self.log.append(f"[operation] {operation.get('type')} {operation.get('arguments', {})}")
        if plan.get("status") == "ready":
            preview = build_plan_preview(plan, context)
            self._set_plan_diff_preview(format_plan_preview(preview))
            for line in preview.get("lines", []):
                self.log.append(line)
        else:
            self._set_plan_diff_preview("")

    def _on_approval_changed(self, _state):
        self._update_execute_enabled()

    def _set_approval_required(self, required):
        self.approval_checkbox.setEnabled(bool(required))
        self.approval_checkbox.setChecked(not required)
        self._update_execute_enabled()

    def _reset_approval_ui(self):
        self.approval_checkbox.setEnabled(False)
        self.approval_checkbox.setChecked(False)
        self.execute_button.setEnabled(False)

    def _update_execute_enabled(self):
        if not self.pending_plan:
            self.execute_button.setEnabled(False)
            return
        needs_approval = requires_user_approval(self.pending_plan)
        self.execute_button.setEnabled((not needs_approval) or self.approval_checkbox.isChecked())

    def _set_plan_diff_preview(self, text):
        if text:
            if isinstance(text, (list, tuple)):
                text = "\n".join(str(line) for line in text)
            self.plan_diff_preview.setPlainText(str(text))
        else:
            self.plan_diff_preview.clear()


def show_chat_panel():
    """Open the chat panel as a dock when FreeCADGui is available."""
    try:
        import FreeCADGui as Gui  # type: ignore

        main_window = Gui.getMainWindow()
        existing = _existing_chat_dock(main_window)
        if existing is not None:
            existing.show()
            existing.raise_()
            visible = existing
        else:
            panel = ChatPanel()
            dock = QtWidgets.QDockWidget("Agentic CAD", main_window)
            dock.setObjectName("AgenticCADDock")
            dock.setWidget(panel)
            main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
            dock.show()
            visible = dock
        try:
            main_window.activateWindow()
        except Exception:
            pass
    except Exception:
        panel = ChatPanel()
        panel.show()
        visible = panel

    # Prevent the widget from being GC'd immediately in FreeCAD's Python runtime.
    global _LAST_PANEL  # noqa: PLW0603
    _LAST_PANEL = visible
    return visible


def describe_chat_panel(widget=None):
    """Return a machine-readable report of the chat Dock/Panel state."""
    try:
        import FreeCADGui as Gui  # type: ignore

        main_window = Gui.getMainWindow()
    except Exception:
        main_window = None
    if widget is None and main_window is not None:
        widget = _existing_chat_dock(main_window)
    panel = _panel_from_widget(widget)
    controls = []
    for attribute, label in CHAT_PANEL_REQUIRED_CONTROLS:
        control = getattr(panel, attribute, None) if panel is not None else None
        controls.append({
            "attribute": attribute,
            "label": label,
            "present": control is not None,
            "enabled": bool(control.isEnabled()) if control is not None and hasattr(control, "isEnabled") else None,
            "object_name": str(control.objectName()) if control is not None and hasattr(control, "objectName") else "",
        })
    return {
        "schema_version": "agentic_cad_chat_panel_state.v1",
        "dock_present": widget is not None,
        "dock_visible": bool(widget.isVisible()) if widget is not None and hasattr(widget, "isVisible") else None,
        "panel_present": panel is not None,
        "all_controls_present": all(item["present"] for item in controls),
        "controls": controls,
    }


def format_chat_panel_state(report):
    """Format a short user-facing chat Dock diagnostic summary."""
    missing = [item["label"] for item in report.get("controls", []) if not item.get("present")]
    if missing:
        return "Agentic CAD chat panel: missing controls: " + ", ".join(missing)
    if report.get("dock_present") and report.get("dock_visible") is False:
        return "Agentic CAD chat panel: dock exists but is hidden"
    if report.get("panel_present"):
        return "Agentic CAD chat panel: ready"
    return "Agentic CAD chat panel: not open"


def _existing_chat_dock(main_window):
    for dock in main_window.findChildren(QtWidgets.QDockWidget):
        if dock.objectName() == "AgenticCADDock":
            return dock
    return None


def _panel_from_widget(widget):
    if widget is None:
        return None
    if isinstance(widget, QtWidgets.QDockWidget):
        widget = widget.widget()
    if isinstance(widget, ChatPanel):
        return widget
    if hasattr(widget, "findChild"):
        return widget.findChild(ChatPanel, "AgenticCADChatPanel")
    return None


def _console_message(message):
    try:
        import FreeCAD  # type: ignore

        FreeCAD.Console.PrintMessage(str(message) + "\n")
    except Exception:
        print(message)


def _active_document():
    try:
        import FreeCAD  # type: ignore

        return FreeCAD.ActiveDocument
    except Exception:
        return None


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
    selected_label, accepted = QtWidgets.QInputDialog.getItem(
        None,
        "Confirm Agentic CAD Input Candidate",
        "Choose the candidate to confirm:",
        [candidate["label"] for candidate in candidates],
        0,
        False,
    )
    if not accepted:
        raise ValueError("input candidate confirmation was cancelled")
    for candidate in candidates:
        if candidate["label"] == selected_label:
            return candidate
    raise ValueError("selected input confirmation candidate was not found")


def _show_info(title, message):
    try:
        QtWidgets.QMessageBox.information(None, title, str(message))
    except Exception:
        return
