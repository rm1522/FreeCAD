"""FreeCAD GUI entrypoint for the Agentic CAD workbench."""

import FreeCADGui as Gui  # type: ignore

try:
    _WorkbenchBase = Workbench  # type: ignore[name-defined]
except NameError:
    # Headless FreeCAD smoke tests do not inject the Workbench base class.
    _WorkbenchBase = object


class AgenticCadWorkbench(_WorkbenchBase):
    """FreeCAD workbench that hosts agentic-cad panels and commands."""

    MenuText = "Agentic CAD"
    ToolTip = "AI-assisted CAD generation for agentic-cad"
    Icon = """
        /* XPM */
        static const char *agentic_cad_xpm[] = {
        "16 16 2 1",
        "  c None",
        ". c #2B6CB0",
        "                ",
        "      ....      ",
        "    ........    ",
        "   ...    ...   ",
        "  ...      ...  ",
        "  ...  ..  ...  ",
        " ...  ....  ... ",
        " ...  ....  ... ",
        " ...  ....  ... ",
        " ...  ....  ... ",
        "  ...  ..  ...  ",
        "  ...      ...  ",
        "   ...    ...   ",
        "    ........    ",
        "      ....      ",
        "                "};
    """

    def Initialize(self):
        import commands  # noqa: F401

        command_names = [
            "AgenticCad_OpenChat",
            "AgenticCad_RunSelfTest",
            "AgenticCad_ReportChatPanel",
            "AgenticCad_RunPlanExecuteSmoke",
            "AgenticCad_RunSelectionUpdateSmoke",
            "AgenticCad_BuildFocusedReprobeRequest",
            "AgenticCad_RebuildWoodScrewCandidateReport",
            "AgenticCad_RunFocusedReprobePipeline",
            "AgenticCad_BuildHardwareUnresolvedReport",
            "AgenticCad_BuildHardwareResolutionPlan",
            "AgenticCad_ConfirmResolutionReject",
            "AgenticCad_ExportFastenerRejectDecisions",
            "AgenticCad_BuildResolutionStatusReport",
            "AgenticCad_BuildResolutionPipelineQueue",
            "AgenticCad_ExecuteResolutionPipelineQueue",
            "AgenticCad_PrepareResolutionRegeneration",
            "AgenticCad_CheckResolutionRegeneration",
            "AgenticCad_ExecuteResolutionRegeneration",
            "AgenticCad_BuildResolutionLayoutPatchCandidates",
            "AgenticCad_ProbeResolutionLayoutPatchContacts",
            "AgenticCad_PreviewResolutionLayoutPatchMerge",
            "AgenticCad_ApproveResolutionLayoutPatchMerge",
            "AgenticCad_RegenerateResolutionLayoutPatchAssembly",
            "AgenticCad_BuildResolutionInputRequests",
            "AgenticCad_BuildResolutionInputTemplate",
            "AgenticCad_BuildResolutionInputDrafts",
            "AgenticCad_BuildResolutionBlockerPacket",
            "AgenticCad_BuildResolutionAnswerCandidates",
            "AgenticCad_BuildResolutionEvidencePack",
            "AgenticCad_DraftResolutionManualCompletionFromEvidence",
            "AgenticCad_BuildResolutionHitlQuestionPacket",
            "AgenticCad_BuildResolutionHitlAnswerPatchTemplate",
            "AgenticCad_BuildResolutionHitlEvidenceReviewPacket",
            "AgenticCad_PreflightResolutionHitlAnswerPatch",
            "AgenticCad_BuildResolutionHitlSourceAssertionPacket",
            "AgenticCad_BuildResolutionHitlSourceAssertionResponseTemplate",
            "AgenticCad_BuildResolutionHitlSourceAssertionDispositionReport",
            "AgenticCad_ApplyResolutionHitlSourceAssertionResponse",
            "AgenticCad_PatchResolutionHitlAnswers",
            "AgenticCad_ApplyResolutionHitlAnswers",
            "AgenticCad_RunGuardedResolutionHitlSubmission",
            "AgenticCad_RunGuardedResolutionHitlPatchSubmission",
            "AgenticCad_RunGuardedResolutionHitlSourceResponseSubmission",
            "AgenticCad_BuildResolutionManualCompletionTemplate",
            "AgenticCad_ApplyResolutionManualCompletion",
            "AgenticCad_PreflightResolutionManualCompletion",
            "AgenticCad_BuildResolutionAnswerSelectionTemplate",
            "AgenticCad_ApplyResolutionAnswerSelection",
            "AgenticCad_PreflightResolutionAnswerSelection",
            "AgenticCad_RunGuardedResolutionSubmission",
            "AgenticCad_RunGuardedManualCompletionSubmission",
            "AgenticCad_BuildResolutionBlockerResponseTemplate",
            "AgenticCad_ApplyResolutionBlockerResponses",
            "AgenticCad_BuildResolutionInputConfirmations",
            "AgenticCad_ConfirmResolutionInputCandidate",
            "AgenticCad_SubmitResolutionInputTemplate",
            "AgenticCad_SubmitConfirmedResolutionInputTemplate",
            "AgenticCad_VisualizeHumanReview",
            "AgenticCad_ApproveHumanReviewTarget",
            "AgenticCad_RejectHumanReviewCandidate",
            "AgenticCad_DeferHumanReviewCandidate",
            "AgenticCad_ApplyHumanReviewDecisions",
        ]
        self.appendToolbar("Agentic CAD", command_names)
        self.appendMenu("Agentic CAD", command_names)

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


if _WorkbenchBase is not object:
    Gui.addWorkbench(AgenticCadWorkbench())
