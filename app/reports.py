"""
reports.py
----------
PDF report generator for Parkinova — Parkinson's MRI Analysis.

Uses ReportLab Platypus to produce a professional, structured PDF report
containing analysis metadata, model scores, an optional image thumbnail,
and a regulatory disclaimer.
"""

import logging
import os
from typing import Optional

# ReportLab imports — all wrapped so import errors surface clearly.
try:
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image as RLImage,
        HRFlowable,
        KeepTogether,
        PageBreak,
    )
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError as _rl_err:
    REPORTLAB_AVAILABLE = False
    logging.getLogger(__name__).error(
        "ReportLab is not installed. PDF generation will be unavailable. %s", _rl_err
    )

logger = logging.getLogger(__name__)

# ── Vintage Editorial Palette ───────────────────────────────────────────────────
_NAVY = colors.HexColor("#123F2D")       # Deep forest green
_LIGHT_GRAY = colors.HexColor("#F5F0D8") # Warm cream
_MID_GRAY = colors.HexColor("#B8C4A5")   # Muted sage green
_WHITE = colors.HexColor("#FFF9E9")      # Warm off-white
_BLACK = colors.HexColor("#123F2D")      # Deep forest green
_DARK_GRAY = colors.HexColor("#365747")  # Muted dark green
_CORAL = colors.HexColor("#F0442E")      # Vibrant coral red

# ── Disclaimer ─────────────────────────────────────────────────────────────────
_DISCLAIMER_TEXT = (
    "This application is an academic AI research prototype. Its output is generated "
    "by a machine-learning model and is not a medical diagnosis. The model's "
    "performance and reliability may vary depending on image quality, dataset "
    "characteristics, and the images used during training. Consult a qualified "
    "neurologist for medical evaluation."
)


class ReportGenerator:
    """
    Generates professional PDF analysis reports for Parkinova.

    The report layout:
    - Header with application branding
    - Analysis Info section
    - Model Info section
    - Preprocessing Details section
    - Results section (predicted class + confidence + per-class scores table)
    - Optional MRI image thumbnail
    - Disclaimer box
    - Footer
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_report(
        self,
        result: dict,
        analysis_id: str,
        patient_code: str,
        include_image: bool,
        save_path: str,
        patient_data: dict = None,
    ) -> bool:
        """
        Legacy/standard report generator for MRI analysis alone.
        """
        return self.generate_combined_report(
            mri_result=result,
            spiral_result=None,
            analysis_id=analysis_id,
            patient_code=patient_code,
            include_images=include_image,
            save_path=save_path,
            patient_data=patient_data,
        )

    def generate_combined_report(
        self,
        mri_result: dict,
        spiral_result: Optional[dict],
        analysis_id: str,
        patient_code: str,
        include_images: bool,
        save_path: str,
        patient_data: Optional[dict] = None,
        lifestyle_data: Optional[dict] = None,
    ) -> bool:
        """
        Generate a comprehensive 2-page multi-modal PDF report containing:
        - Page 1: Patient Demographics, Multi-Modal Synthesis Summary, and Full 13-Symptom Assessment.
        - Page 2: High-Resolution Brain MRI Scan Analysis Card, Archimedean Spiral Drawing Analysis Card,
                  and Regulatory Research Disclaimer.
        """
        if not REPORTLAB_AVAILABLE:
            logger.error("ReportLab is not available — cannot generate report.")
            return False

        try:
            mri_result = mri_result or {}
            spiral_result = spiral_result or {}
            patient_data = patient_data or {}

            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

            doc = SimpleDocTemplate(
                save_path,
                pagesize=A4,
                leftMargin=1.8 * cm,
                rightMargin=1.8 * cm,
                topMargin=1.5 * cm,
                bottomMargin=1.5 * cm,
                title=f"Parkinova Medical Assessment — {analysis_id}",
                author="Parkinova Research Platform",
                subject="Comprehensive Parkinson's Multi-Modal Assessment Report",
            )

            styles = self._build_styles()
            story = []

            # =========================================================================
            # PAGE 1: PATIENT PROFILE, SYNTHESIS SUMMARY & SYMPTOM QUESTIONNAIRE
            # =========================================================================

            # ── Header ─────────────────────────────────────────────────────────────
            story.append(Paragraph("PARKINOVA", styles["AppTitle"]))
            story.append(Paragraph("Medical Assessment Report", styles["AppSubtitle"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=_NAVY))
            story.append(Spacer(1, 0.2 * cm))

            # ── A. Patient & Report Information ────────────────────────────────────
            story.append(Paragraph("A. Patient & Assessment Information", styles["SectionHeading"]))
            
            p_code = patient_code or (patient_data.get("patient_code") if patient_data else "Not provided")
            age_val = patient_data.get("age") if patient_data else None
            gender_val = patient_data.get("gender") if patient_data else None
            
            mri_available = bool(mri_result and mri_result.get("success"))
            spiral_available = bool(spiral_result and spiral_result.get("success"))

            modules_list = []
            if mri_available:
                modules_list.append("Brain MRI Scan")
            if spiral_available:
                modules_list.append("Archimedean Spiral Analysis")
            if patient_data and patient_data.get("responses"):
                modules_list.append("Symptom Questionnaire")
            if not modules_list:
                modules_list.append("Multi-Modal Evaluation Pending")

            ts_display = (mri_result.get("analysis_timestamp") or spiral_result.get("timestamp") or "N/A")[:19].replace("T", " ")

            patient_table_data = [
                ["Patient Reference", str(p_code or "Not provided")],
                ["Age / Gender", f"{age_val or 'Not specified'} / {gender_val or 'Not specified'}"],
                ["Assessment Date", ts_display],
                ["Report Reference ID", str(analysis_id or "PARK-REPORT")],
                ["Completed Modules", ", ".join(modules_list)],
                ["Lead Evaluator", "Dr. Researcher"],
            ]
            story.append(self._build_info_table(patient_table_data))
            story.append(Spacer(1, 0.2 * cm))

            # ── B. Combined Assessment Summary ─────────────────────────────────────
            story.append(Paragraph("B. Combined Assessment Summary", styles["SectionHeading"]))

            # Extract MRI findings
            mri_is_pd = False
            mri_pred_str = "Not Evaluated (Pending Scan)"
            mri_status_str = "Pending Scan Upload"
            if mri_available:
                mri_status_str = "Completed"
                mri_pred_str = str(mri_result.get("predicted_class", "Evaluation Complete"))
                if mri_result.get("is_parkinson") is not None:
                    mri_is_pd = bool(mri_result.get("is_parkinson"))
                else:
                    mri_pred_lower = mri_pred_str.lower()
                    mri_is_pd = (
                        mri_result.get("predicted_index") == 1 or
                        ("parkinson" in mri_pred_lower and "no" not in mri_pred_lower and "without" not in mri_pred_lower)
                    )

            # Extract Spiral findings
            spiral_is_pd = False
            spiral_has_active_pred = False
            spiral_pred_str = "Not Evaluated (Pending Drawing)"
            spiral_status_str = "Pending Drawing Upload"
            if spiral_available:
                spiral_status_str = str(spiral_result.get("status", "Completed"))
                spiral_pred_str = str(spiral_result.get("model_prediction", "Standby"))
                spiral_raw = spiral_result.get("raw_score")
                pred_lower = spiral_pred_str.lower()

                if spiral_result.get("is_parkinson") is not None:
                    spiral_has_active_pred = True
                    spiral_is_pd = bool(spiral_result.get("is_parkinson"))
                elif spiral_raw is not None or "motor" in pred_lower or "pattern" in pred_lower or "trajectory" in pred_lower:
                    spiral_has_active_pred = True
                    if "motor irregularities" in pred_lower or "tremor" in pred_lower or ("parkinson" in pred_lower and "no" not in pred_lower):
                        spiral_is_pd = True
                    elif "without" in pred_lower or ("regular" in pred_lower and "irregular" not in pred_lower) or "control" in pred_lower or "no parkinson" in pred_lower:
                        spiral_is_pd = False
                    elif spiral_raw is not None:
                        spiral_is_pd = (spiral_raw >= 0.5)

            summary_table_data = [
                ["Analysis Component", "Completion Status", "Model Prediction"],
                ["Brain MRI Scan", mri_status_str, mri_pred_str],
                ["Spiral Drawing", spiral_status_str, spiral_pred_str],
            ]
            story.append(self._build_summary_table(summary_table_data, styles))
            story.append(Spacer(1, 0.15 * cm))

            # Synthesize combined interpretation
            if mri_available and spiral_available:
                if spiral_has_active_pred:
                    if mri_is_pd and spiral_is_pd:
                        synth_title = "<b>Multi-Modal Synthesis: Concordant Findings (Parkinsonian Pattern Detected)</b>"
                        synth_body = (
                            "Both the MRI convolutional model and the Archimedean spiral drawing analysis identified distinctive "
                            "features correlated with Parkinsonian disease patterns. Independent concordance across structural "
                            "neuroimaging and fine-motor kinematics suggests that comprehensive clinical evaluation with a movement "
                            "disorder specialist is warranted. This automated synthesis does not constitute a confirmed clinical diagnosis."
                        )
                    elif not mri_is_pd and not spiral_is_pd:
                        synth_title = "<b>Multi-Modal Synthesis: Concordant Findings (No Parkinsonian Pattern Detected)</b>"
                        synth_body = (
                            "Neither the evaluated brain MRI scan slice nor the Archimedean spiral drawing exhibited patterns "
                            "correlated with the Parkinson's cohort in the model training data. This observational finding "
                            "does not exclude early-stage disease, non-motor presentations, or atypical variants."
                        )
                    else:
                        synth_title = "<b>Multi-Modal Synthesis: Divergent Findings (Disagreement Across Modalities)</b>"
                        synth_body = (
                            "The MRI scan analysis and spiral drawing analysis yielded divergent results. In neurology, structural "
                            "imaging and motor performance frequently diverge: early structural changes can occur prior to tremor, "
                            "or physiological tremor may affect drawing sketches while 3T MRI is unremarkable. Both results are presented "
                            "transparently; direct clinical evaluation by a licensed neurologist is essential."
                        )
                else:
                    synth_title = "<b>Multi-Modal Synthesis: MRI Evaluated · Spiral Verified</b>"
                    synth_body = (
                        "Brain MRI deep learning inference was successfully completed. The uploaded Archimedean spiral sketch was verified "
                        "for geometry and stroke contrast and remains on integration standby. No synthetic combined risk score is calculated "
                        "to protect diagnostic integrity."
                    )
            elif mri_available and not spiral_available:
                synth_title = "<b>Assessment Synthesis: Partial Evaluation (Awaiting Spiral Analysis)</b>"
                synth_body = (
                    "Brain MRI neuroimaging analysis was completed successfully. Archimedean spiral drawing analysis has not "
                    "yet been completed. The multi-modal combined assessment is incomplete and relies currently on single-modality imaging."
                )
            elif not mri_available and spiral_available:
                synth_title = "<b>Assessment Synthesis: Partial Evaluation (Awaiting MRI Scan Analysis)</b>"
                synth_body = (
                    "Archimedean spiral drawing analysis was completed successfully. Brain MRI scan analysis has not yet been "
                    "completed. The multi-modal combined assessment is incomplete and relies currently on fine-motor drawing data."
                )
            else:
                synth_title = "<b>Assessment Synthesis: Awaiting Analysis Inputs</b>"
                synth_body = (
                    "Neither MRI neuroimaging nor spiral drawing analysis has been evaluated for this session. "
                    "Please upload the required scans and drawings to generate multi-modal synthesis."
                )

            story.append(Paragraph(synth_title, styles["SubSectionHeading"]))
            story.append(Paragraph(synth_body, styles["BodyText"]))
            story.append(Spacer(1, 0.2 * cm))

            # ── C. Patient Symptom & Cognitive Assessment Profile ───────────────────
            story.append(Paragraph("C. Patient Symptom & Cognitive Assessment Profile", styles["SectionHeading"]))
            responses = patient_data.get("responses") if patient_data else None
            if responses:
                answered_count = patient_data.get("answered_questions", len(responses))
                total_count = patient_data.get("total_questions", 13)
                completed_time = str(patient_data.get("completed_at", ts_display))[:19].replace("T", " ")

                story.append(self._build_patient_symptom_table(responses, styles))
                story.append(Spacer(1, 0.1 * cm))
                story.append(Paragraph(
                    f"<i>Note: {answered_count} of {total_count} self-reported questions completed on {completed_time}. "
                    "Symptom frequencies are self-reported for research and risk documentation purposes only; "
                    "they do not independently constitute a diagnostic evaluation.</i>",
                    styles["Disclaimer"],
                ))
            else:
                symptom_pending_data = [
                    ["Questionnaire Status", "Not Submitted / Incomplete"],
                    ["Documentation Note", "Self-reported cognitive, emotional, sleep, and functional assessment was not recorded."],
                ]
                story.append(self._build_info_table(symptom_pending_data))
                story.append(Spacer(1, 0.1 * cm))
                story.append(Paragraph(
                    "<i>Note: Comprehensive neurological assessment requires patient symptom history in addition to imaging.</i>",
                    styles["Disclaimer"],
                ))

            # Explicit clean page break separating clinical synthesis from imaging inspection
            story.append(PageBreak())

            # =========================================================================
            # PAGE 2: HIGH-RESOLUTION IMAGING, DRAWING INSPECTION & REGULATORY NOTICE
            # =========================================================================

            story.append(Paragraph("PARKINOVA &mdash; Multi-Modal Neuroimaging &amp; Fine-Motor Analysis", styles["AppSubtitle"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=_NAVY))
            story.append(Spacer(1, 0.2 * cm))

            # ── D. Brain MRI Scan Analysis ──────────────────────────────────────────
            story.append(Paragraph("D. Brain MRI Scan Analysis", styles["SectionHeading"]))
            mri_img_path = mri_result.get("image_path") if (include_images and mri_available) else None
            mri_details = [
                ["Analysis Status", mri_status_str],
                ["Model Prediction", mri_pred_str],
                ["Model Architecture", "Parkinson CNN (244x244x3)"],
                ["Input Preprocessing", "244x244 Lanczos Resizing, Channel Standardization"],
                ["Image Source", os.path.basename(str(mri_result.get("image_path", "None"))) if mri_available else "Not loaded"],
            ]
            mri_card = self._build_side_by_side_card(
                img_path=mri_img_path,
                details_rows=mri_details,
                styles=styles,
                placeholder_label="Brain MRI Scan",
            )
            mri_expl = mri_result.get("explanation", "Neuroimaging pattern analysis completed based on CNN model evaluation.")
            
            story.append(KeepTogether([
                mri_card,
                Spacer(1, 0.15 * cm),
                Paragraph("<b>Model Findings &amp; Interpretation:</b>", styles["SubSectionHeading"]),
                Paragraph(mri_expl, styles["BodyText"]),
            ]))
            story.append(Spacer(1, 0.3 * cm))

            # ── E. Archimedean Spiral Drawing Analysis ──────────────────────────────
            story.append(Paragraph("E. Archimedean Spiral Drawing Analysis", styles["SectionHeading"]))
            if spiral_available:
                spiral_obs = spiral_result.get("observations", {})
                sp_img_path = spiral_result.get("image_path") if include_images else None
                geom_str = str(spiral_obs.get('Image Geometry', 'Analyzed')).replace("×", "x")
                sp_details = [
                    ["Analysis Status", spiral_status_str],
                    ["Model Prediction", spiral_pred_str],
                    ["Model Architecture", "Archimedean Spiral YOLO / CNN (244x244x3)"],
                    ["Geometry & Stroke", f"{geom_str} | {spiral_obs.get('Stroke Coverage', 'Standard')}"],
                    ["Drawing Source", os.path.basename(str(spiral_result.get("image_path", "None")))],
                ]
                sp_card = self._build_side_by_side_card(
                    img_path=sp_img_path,
                    details_rows=sp_details,
                    styles=styles,
                    placeholder_label="Spiral Drawing",
                )
                obs_bullets = []
                for k, v in spiral_obs.items():
                    clean_v = str(v).replace("×", "x")
                    obs_bullets.append(f"&bull; <b>{k}:</b> {clean_v}")
                if not obs_bullets:
                    obs_bullets.append("&bull; <b>Trajectory Kinematics:</b> Fine-motor stroke dynamics and radial deviation analyzed.")

                story.append(KeepTogether([
                    sp_card,
                    Spacer(1, 0.15 * cm),
                    Paragraph("<b>Visual &amp; Kinematic Observations:</b>", styles["SubSectionHeading"]),
                    Paragraph("<br/>".join(obs_bullets), styles["BodyText"]),
                ]))
            else:
                spiral_pending_data = [
                    ["Analysis Status", "Pending / Not Submitted"],
                    ["Reason", "Patient has not yet submitted an Archimedean spiral sketch"],
                    ["Impact", "Combined multi-modal synthesis remains incomplete"],
                ]
                story.append(self._build_info_table(spiral_pending_data))

            story.append(Spacer(1, 0.3 * cm))

            # ── F. Regulatory Notice & Academic Disclaimer ──────────────────────────
            story.append(HRFlowable(width="100%", thickness=1, color=_MID_GRAY))
            story.append(Spacer(1, 0.15 * cm))
            story.append(Paragraph("Regulatory Notice & Academic Disclaimer", styles["SubSectionHeading"]))
            story.append(Paragraph(_DISCLAIMER_TEXT, styles["Disclaimer"]))
            story.append(Spacer(1, 0.2 * cm))

            story.append(Paragraph(
                "Parkinova Medical Assessment Report &nbsp;|&nbsp; Academic AI Research Prototype &nbsp;|&nbsp; Generated: " +
                ts_display[:10],
                styles["Footer"],
            ))

            doc.build(story)
            logger.info("Combined PDF report successfully compiled at '%s'", save_path)
            return True

        except Exception as exc:
            logger.exception("Failed to generate combined PDF report: %s", exc)
            return False

    def generate_legacy_report(
        self,
        result: dict,
        analysis_id: str,
        patient_code: str,
        include_image: bool,
        save_path: str,
        patient_data: dict = None,
    ) -> bool:

        try:
            # Ensure the destination directory exists.
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

            doc = SimpleDocTemplate(
                save_path,
                pagesize=A4,
                leftMargin=2 * cm,
                rightMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
                title=f"Parkinova Report — {analysis_id}",
                author="Parkinova",
                subject="Parkinson's MRI Analysis Report",
            )

            styles = self._build_styles()
            story = []

            # ── Header ────────────────────────────────────────────────
            story.append(Paragraph("Parkinova", styles["AppTitle"]))
            story.append(Paragraph("MRI Analysis Report", styles["AppSubtitle"]))
            story.append(HRFlowable(width="100%", thickness=2, color=_NAVY))
            story.append(Spacer(1, 0.4 * cm))

            # ── Analysis Info ─────────────────────────────────────────
            story.append(Paragraph("Analysis Information", styles["SectionHeading"]))
            analysis_data = [
                ["Analysis ID", analysis_id],
                ["Patient Code", patient_code],
                ["Timestamp", result.get("analysis_timestamp", "N/A")],
            ]
            story.append(self._build_info_table(analysis_data))
            story.append(Spacer(1, 0.4 * cm))

            # ── Model Info ────────────────────────────────────────────
            story.append(Paragraph("Model Information", styles["SectionHeading"]))
            model_info: dict = result.get("preprocessing_info", {}).get(
                "model_info", {}
            )
            # Fall back gracefully if model_info is stored elsewhere.
            model_name = model_info.get("name", "N/A")
            model_version = model_info.get("version", "N/A")
            input_shape = str(model_info.get("input_shape", "N/A"))
            output_type = result.get("output_type", "N/A")
            model_data = [
                ["Model Name", model_name],
                ["Version", model_version],
                ["Input Shape", input_shape],
                ["Output Type", output_type],
            ]
            story.append(self._build_info_table(model_data))
            story.append(Spacer(1, 0.4 * cm))

            # ── Preprocessing Details ─────────────────────────────────
            story.append(
                Paragraph("Preprocessing Details", styles["SectionHeading"])
            )
            preprocessing_info: dict = result.get("preprocessing_info", {})
            if preprocessing_info:
                prep_rows = [
                    [str(k).replace("_", " ").title(), str(v)]
                    for k, v in preprocessing_info.items()
                    if k != "model_info"  # avoid duplicating model info
                ]
            else:
                prep_rows = [["No preprocessing metadata available", ""]]
            story.append(self._build_info_table(prep_rows))
            story.append(Spacer(1, 0.4 * cm))

            # ── Results ───────────────────────────────────────────────
            story.append(Paragraph("Analysis Results", styles["SectionHeading"]))

            predicted_class = result.get("predicted_class", "N/A")
            explanation = result.get("explanation", "Pattern analysis completed based on CNN model evaluation.")

            result_summary = [
                ["Model Prediction", predicted_class],
                ["Evaluation Status", "Completed"],
            ]
            story.append(self._build_info_table(result_summary))
            story.append(Spacer(1, 0.3 * cm))

            story.append(Paragraph("Findings & Pattern Analysis Explanation", styles["SubSectionHeading"]))
            story.append(Paragraph(explanation, styles["BodyText"]))
            story.append(Spacer(1, 0.4 * cm))

            # ── Optional Image Thumbnail ───────────────────────────────
            if include_image:
                image_path = result.get("image_path") or result.get(
                    "preprocessing_info", {}
                ).get("image_path", None)
                if image_path and os.path.isfile(str(image_path)):
                    try:
                        story.append(
                            Paragraph("MRI Image", styles["SectionHeading"])
                        )
                        img = RLImage(image_path, width=7 * cm, height=7 * cm)
                        img.hAlign = "LEFT"
                        story.append(img)
                        story.append(Spacer(1, 0.4 * cm))
                    except Exception as img_exc:
                        logger.warning(
                            "Could not embed image thumbnail: %s", img_exc
                        )
                else:
                    logger.info(
                        "include_image=True but no valid image_path found; skipping thumbnail."
                    )

            # ── Patient Assessment Summary ─────────────────────────────
            if patient_data and patient_data.get("responses"):
                story.append(HRFlowable(width="100%", thickness=1, color=_MID_GRAY))
                story.append(Spacer(1, 0.3 * cm))
                story.append(
                    Paragraph("Patient Symptom Assessment", styles["SectionHeading"])
                )

                # Demographics
                demo_rows = [
                    ["Age", str(patient_data.get("age", "Not provided"))],
                    ["Gender", str(patient_data.get("gender", "Not provided"))],
                    ["Questions Answered",
                     f"{patient_data.get('answered_questions', 0)} / "
                     f"{patient_data.get('total_questions', 0)}"],
                    ["Assessment Date",
                     str(patient_data.get("completed_at", "N/A"))[:19]],
                ]
                story.append(self._build_info_table(demo_rows))
                story.append(Spacer(1, 0.3 * cm))

                # Response table
                story.append(
                    Paragraph("Symptom Responses", styles["SubSectionHeading"])
                )
                resp_header = [["Symptom", "Category", "Response"]]
                resp_rows = []
                for qid, r in patient_data["responses"].items():
                    resp_rows.append([
                        str(r.get("label", qid)),
                        str(r.get("category", "")),
                        str(r.get("answer", "Not answered")),
                    ])
                story.append(
                    self._build_score_table(resp_header + resp_rows, styles)
                )

                story.append(Spacer(1, 0.3 * cm))
                story.append(
                    Paragraph(
                        "<i>Note: These responses are self-reported and collected for "
                        "research documentation purposes only. They do not constitute "
                        "a clinical assessment.</i>",
                        styles["BodyText"],
                    )
                )
                story.append(Spacer(1, 0.4 * cm))

            # ── Disclaimer ────────────────────────────────────────────
            story.append(HRFlowable(width="100%", thickness=1, color=_MID_GRAY))
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph("Disclaimer", styles["SectionHeading"]))
            story.append(self._create_disclaimer_paragraph(styles))
            story.append(Spacer(1, 0.4 * cm))

            # ── Footer ────────────────────────────────────────────────
            story.append(HRFlowable(width="100%", thickness=1, color=_MID_GRAY))
            story.append(Spacer(1, 0.2 * cm))
            story.append(
                Paragraph(
                    "Generated by Parkinova &nbsp;|&nbsp; Academic Research Prototype",
                    styles["Footer"],
                )
            )

            # ── Build PDF ─────────────────────────────────────────────
            doc.build(story)
            logger.info("PDF report written to '%s'", save_path)
            return True

        except Exception as exc:
            logger.exception("Failed to generate PDF report: %s", exc)
            return False

    def _create_disclaimer_paragraph(self, styles: Optional[dict] = None) -> "Paragraph":
        """
        Return a styled Paragraph containing the full academic disclaimer.

        Parameters
        ----------
        styles : dict, optional
            Style sheet dict built by ``_build_styles()``. If not provided a
            fresh one is created (useful when calling this method in isolation).

        Returns
        -------
        reportlab.platypus.Paragraph
            A Paragraph object ready to be added to a Platypus story.
        """
        if styles is None:
            styles = self._build_styles()

        # Wrap in a single-cell table to create the bordered box effect.
        disclaimer_para = Paragraph(_DISCLAIMER_TEXT, styles["Disclaimer"])
        table = Table([[disclaimer_para]], colWidths=["100%"])
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 1, _MID_GRAY),
                    ("BACKGROUND", (0, 0), (-1, -1), _LIGHT_GRAY),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        # Wrap the table in a Paragraph-compatible object by returning it
        # directly — callers add it to the story.
        # For the method signature contract (returns Paragraph), we instead
        # return a plain styled Paragraph and let generate_report handle boxing.
        return Paragraph(_DISCLAIMER_TEXT, styles["Disclaimer"])

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_styles() -> dict:
        """
        Build and return a dictionary of named ParagraphStyles.

        Returns
        -------
        dict
            Maps style name (str) to ``ParagraphStyle`` instance.
        """
        base = getSampleStyleSheet()

        styles: dict = {}

        styles["AppTitle"] = ParagraphStyle(
            "AppTitle",
            parent=base["Title"],
            fontSize=18,
            textColor=_NAVY,
            spaceAfter=2,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )
        styles["AppSubtitle"] = ParagraphStyle(
            "AppSubtitle",
            parent=base["Normal"],
            fontSize=10.5,
            textColor=_DARK_GRAY,
            spaceAfter=4,
            alignment=TA_CENTER,
            fontName="Helvetica",
        )
        styles["SectionHeading"] = ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontSize=10.5,
            textColor=_NAVY,
            spaceBefore=6,
            spaceAfter=3,
            fontName="Helvetica-Bold",
        )
        styles["SubSectionHeading"] = ParagraphStyle(
            "SubSectionHeading",
            parent=base["Heading3"],
            fontSize=9,
            textColor=_DARK_GRAY,
            spaceBefore=4,
            spaceAfter=2,
            fontName="Helvetica-Bold",
        )
        styles["BodyText"] = ParagraphStyle(
            "BodyText",
            parent=base["Normal"],
            fontSize=8,
            textColor=_BLACK,
            leading=10.5,
            fontName="Helvetica",
        )
        styles["Disclaimer"] = ParagraphStyle(
            "Disclaimer",
            parent=base["Normal"],
            fontSize=7.5,
            textColor=_DARK_GRAY,
            fontName="Helvetica-Oblique",
            leading=9.5,
            alignment=TA_JUSTIFY,
        )
        styles["Footer"] = ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontSize=7,
            textColor=_MID_GRAY,
            alignment=TA_CENTER,
            fontName="Helvetica",
        )

        return styles

    @staticmethod
    def _build_info_table(rows: list) -> "Table":
        """
        Build a two-column key/value info table with alternating row shading.

        Parameters
        ----------
        rows : list[list[str]]
            Each inner list is ``[key, value]``.

        Returns
        -------
        reportlab.platypus.Table
        """
        page_width = A4[0] - 3.6 * cm  # account for left + right margins
        col_widths = [4.5 * cm, page_width - 4.5 * cm]

        table = Table(rows, colWidths=col_widths)

        row_commands = []
        for i, _ in enumerate(rows):
            bg = _LIGHT_GRAY if i % 2 == 0 else _WHITE
            row_commands.append(("BACKGROUND", (0, i), (-1, i), bg))

        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("TEXTCOLOR", (0, 0), (-1, -1), _BLACK),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("BOX", (0, 0), (-1, -1), 0.5, _MID_GRAY),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, _MID_GRAY),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
                + row_commands
            )
        )
        return table

    @staticmethod
    def _build_summary_table(rows: list, styles: dict) -> "Table":
        """
        Build a 3-column summary table (Analysis Component | Status | Model Prediction)
        with wrapped Paragraph cells that strictly fit the printable width (17.4 cm).
        """
        page_width = A4[0] - 3.6 * cm  # 17.4 cm
        col_widths = [4.2 * cm, 3.4 * cm, page_width - 7.6 * cm]

        header_style = ParagraphStyle(
            "SummaryHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            textColor=_WHITE,
            alignment=TA_LEFT,
        )
        cell_bold_style = ParagraphStyle(
            "SummaryCellBold",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=_NAVY,
            leading=10,
        )
        cell_normal_style = ParagraphStyle(
            "SummaryCellNormal",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            textColor=_BLACK,
            leading=10,
        )

        formatted_rows = []
        for i, row in enumerate(rows):
            if i == 0:
                formatted_rows.append([
                    Paragraph(str(col), header_style) for col in row
                ])
            else:
                formatted_rows.append([
                    Paragraph(str(row[0]), cell_bold_style),
                    Paragraph(str(row[1]), cell_normal_style),
                    Paragraph(str(row[2]), cell_normal_style),
                ])

        table = Table(formatted_rows, colWidths=col_widths)

        row_commands = []
        for i in range(1, len(rows)):
            bg = _LIGHT_GRAY if i % 2 == 1 else _WHITE
            row_commands.append(("BACKGROUND", (0, i), (-1, i), bg))

        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("BOX", (0, 0), (-1, -1), 0.5, _MID_GRAY),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, _MID_GRAY),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
                + row_commands
            )
        )
        return table

    @staticmethod
    def _build_patient_symptom_table(responses: dict, styles: dict) -> "Table":
        """
        Build a 3-column table displaying patient's 13 symptom questionnaire responses
        (Symptom Domain | Category | Patient Response) wrapped within 17.4 cm.
        """
        page_width = A4[0] - 3.6 * cm  # 17.4 cm
        col_widths = [6.2 * cm, 4.4 * cm, page_width - 10.6 * cm]

        header_style = ParagraphStyle(
            "SymptomHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=_WHITE,
            alignment=TA_LEFT,
        )
        domain_style = ParagraphStyle(
            "SymptomDomain",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            textColor=_NAVY,
            leading=9,
        )
        cat_style = ParagraphStyle(
            "SymptomCat",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            textColor=_DARK_GRAY,
            leading=9,
        )
        resp_style = ParagraphStyle(
            "SymptomResp",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            textColor=_BLACK,
            leading=9,
        )

        formatted_rows = [
            [
                Paragraph("Symptom Domain", header_style),
                Paragraph("Category", header_style),
                Paragraph("Patient Response", header_style),
            ]
        ]

        for qid, item in responses.items():
            domain_text = item.get("label") or qid.replace("_", " ").title()
            cat_text = item.get("category", "General")
            ans_text = item.get("answer", "Not answered")
            formatted_rows.append([
                Paragraph(domain_text, domain_style),
                Paragraph(cat_text, cat_style),
                Paragraph(ans_text, resp_style),
            ])

        table = Table(formatted_rows, colWidths=col_widths)
        row_commands = []
        for i in range(1, len(formatted_rows)):
            bg = _LIGHT_GRAY if i % 2 == 1 else _WHITE
            row_commands.append(("BACKGROUND", (0, i), (-1, i), bg))

        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("BOX", (0, 0), (-1, -1), 0.5, _MID_GRAY),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, _MID_GRAY),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
                + row_commands
            )
        )
        return table

    @staticmethod
    def _build_side_by_side_card(
        img_path: Optional[str],
        details_rows: list,
        styles: dict,
        placeholder_label: str = "Image Scan"
    ) -> "Table":
        """
        Build a 2-column card:
        Col 0 (5.0 cm): Thumbnail image (4.6 cm x 4.6 cm) or placeholder.
        Col 1 (12.4 cm): Details table (Key-Value metadata).
        Total width = 17.4 cm.
        """
        card_width = A4[0] - 3.6 * cm  # 17.4 cm
        col0_w = 5.0 * cm
        col1_w = card_width - col0_w   # 12.4 cm

        img_element = None
        if img_path and os.path.isfile(str(img_path)):
            try:
                img_element = RLImage(img_path, width=4.6 * cm, height=4.6 * cm)
                img_element.hAlign = "CENTER"
            except Exception as img_exc:
                logger.warning("Could not load image thumbnail '%s': %s", img_path, img_exc)

        if img_element is None:
            img_placeholder = Paragraph(
                f"<br/><br/><b>[{placeholder_label}]</b><br/>No thumbnail loaded",
                ParagraphStyle("ImgPh", parent=styles["BodyText"], alignment=TA_CENTER, fontSize=8, textColor=_DARK_GRAY)
            )
            left_content = img_placeholder
        else:
            left_content = img_element

        cell_bold_style = ParagraphStyle(
            "CardK",
            parent=styles["BodyText"],
            fontSize=8,
            textColor=_NAVY,
            fontName="Helvetica-Bold",
            leading=10,
        )
        cell_val_style = ParagraphStyle(
            "CardV",
            parent=styles["BodyText"],
            fontSize=8,
            textColor=_BLACK,
            leading=10,
        )

        detail_table_rows = []
        for k, v in details_rows:
            detail_table_rows.append([
                Paragraph(f"<b>{k}</b>", cell_bold_style),
                Paragraph(str(v), cell_val_style),
            ])

        right_table = Table(detail_table_rows, colWidths=[3.6 * cm, col1_w - 3.6 * cm])
        right_commands = []
        for i in range(len(details_rows)):
            bg = _LIGHT_GRAY if i % 2 == 0 else _WHITE
            right_commands.append(("BACKGROUND", (0, i), (-1, i), bg))

        right_table.setStyle(
            TableStyle(
                [
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("BOX", (0, 0), (-1, -1), 0.5, _MID_GRAY),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, _MID_GRAY),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
                + right_commands
            )
        )

        card_table = Table([[left_content, right_table]], colWidths=[col0_w, col1_w])
        card_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                    ("BOX", (0, 0), (-1, -1), 0.5, _MID_GRAY),
                    ("BACKGROUND", (0, 0), (0, 0), _LIGHT_GRAY),
                    ("BACKGROUND", (1, 0), (1, 0), _WHITE),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return card_table

    @staticmethod
    def _build_lifestyle_table(rows: list, styles: dict) -> "Table":
        """
        Build a formatted two-column table for Health & Lifestyle recommendations.
        """
        page_width = A4[0] - 3.6 * cm
        col_widths = [page_width * 0.32, page_width * 0.68]

        table = Table(rows, colWidths=col_widths)

        row_commands = []
        for i, _ in enumerate(rows):
            bg = _LIGHT_GRAY if i % 2 == 0 else _WHITE
            row_commands.append(("BACKGROUND", (0, i), (-1, i), bg))

        table.setStyle(
            TableStyle(
                [
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("BOX", (0, 0), (-1, -1), 0.5, _MID_GRAY),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, _MID_GRAY),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
                + row_commands
            )
        )
        return table

    @staticmethod
    def _build_score_table(rows: list, styles: dict) -> "Table":
        """
        Build a three-column scores table (Class | Score | Percentage)
        with a styled header row.

        Parameters
        ----------
        rows : list[list[str]]
            First row is the header; subsequent rows are data rows.
        styles : dict
            Style sheet from ``_build_styles()``.

        Returns
        -------
        reportlab.platypus.Table
        """
        page_width = A4[0] - 4 * cm
        col_widths = [page_width * 0.40, page_width * 0.30, page_width * 0.30]

        table = Table(rows, colWidths=col_widths)

        row_commands = []
        for i in range(1, len(rows)):
            bg = _LIGHT_GRAY if i % 2 == 1 else _WHITE
            row_commands.append(("BACKGROUND", (0, i), (-1, i), bg))

        table.setStyle(
            TableStyle(
                [
                    # Header row
                    ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Data rows
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 1), (-1, -1), _BLACK),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    # Shared
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("BOX", (0, 0), (-1, -1), 0.5, _MID_GRAY),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, _MID_GRAY),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
                + row_commands
            )
        )
        return table
