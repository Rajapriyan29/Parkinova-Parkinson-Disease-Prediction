"""
results.py
==========
Medical Assessment Report Dashboard for Parkinova.
Consolidates Brain MRI Scan Analysis and Archimedean Spiral Analysis
into a unified, compact, professional clinical assessment report.

Features:
- Streamlined single-page medical report layout (sub-tabs removed)
- Top Report Header with status indicator and export actions (Print, Export JSON, Download PDF)
- Compact Patient & Assessment Information meta strip
- Prominent Combined Summary card comparing MRI and Spiral outputs side-by-side
- Transparent concordance and divergence handling without fake scores
- Side-by-side MRI and Spiral Analysis cards with image thumbnails and actual model outputs
- Automatic data synchronization via refresh() on navigation
- Native Print and JSON export integration
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Any, Optional, Dict
import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

logger = logging.getLogger(__name__)

# Vintage Editorial Palette (Warm Cream, Deep Forest Green, Coral Red)
PALETTE = {
    "bg": "#F5F0D8",               # Primary Background: Warm cream / vintage ivory
    "card": "#FFF9E9",             # Highlight Color: Warm off-white
    "primary": "#F0442E",          # Accent Color: Vibrant coral red
    "primary_hover": "#D43823",    # Slightly darker coral
    "primary_text": "#FFF9E9",     # Warm off-white
    "secondary": "#FFF9E9",        # Cream background for secondary buttons
    "secondary_border": "#123F2D", # Forest green border for secondary buttons
    "secondary_text": "#123F2D",   # Forest green text
    "secondary_hover": "#EAE5CC",  # Pale beige hover
    "text_dark": "#123F2D",        # Primary Text: Deep forest green
    "text_muted": "#365747",       # Secondary Text: Muted dark green
    "border": "#B8C4A5",           # Border Color: Muted sage green
    "pd_badge_bg": "#FDF0EE",      # Coral tint
    "pd_badge_text": "#F0442E",    # Coral red
    "pd_badge_border": "#F8C0B8",  # Soft coral border
    "normal_badge_bg": "#EAE5CC",  # Subtle Background: Pale beige
    "normal_badge_text": "#123F2D",# Deep forest green
    "normal_badge_border": "#B8C4A5",# Muted sage green
    "amber_bg": "#FDF4F0",         # Soft terracotta tint
    "amber_text": "#D77B65",       # Soft terracotta
    "amber_border": "#EBC6BC",
    "warn": "#D77B65",             # Soft terracotta
    "success": "#123F2D",          # Deep forest green
    "error": "#F0442E",            # Coral red
    "box_bg": "#EAE5CC",           # Card section fill
}

THUMB_SIZE = (180, 180)


class ResultsFrame(ctk.CTkFrame):
    """
    Compact, professional Medical Assessment Report combining MRI and Spiral analysis outputs.
    """

    def __init__(self, parent: Any, app_controller: Any) -> None:
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0)
        self.app_controller = app_controller

        self._result: Optional[dict] = None
        self._analysis_id: str = ""
        self._patient_code: str = ""
        self._ctk_mri_image: Optional[ctk.CTkImage] = None
        self._ctk_spiral_image: Optional[ctk.CTkImage] = None

        self.build_ui()

    def build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_scroll_content()

    # ── Report Header ─────────────────────────────────────────────────────────
    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=PALETTE["card"], corner_radius=0, height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, padx=32, pady=12, sticky="w")

        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.pack(anchor="w")

        ctk.CTkLabel(
            title_row,
            text="Medical Assessment Report",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left", padx=(0, 14))

        # Professional report status indicator badge
        self.report_status_badge = ctk.CTkLabel(
            title_row,
            text="● Awaiting Analysis Inputs",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=PALETTE["warn"],
        )
        self.report_status_badge.pack(side="left")

        self.timestamp_label = ctk.CTkLabel(
            left,
            text="Awaiting assessment evaluation…",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
        )
        self.timestamp_label.pack(anchor="w", pady=(1, 0))

        # Action Buttons: Print, Export JSON, Download PDF
        actions_frame = ctk.CTkFrame(header, fg_color="transparent")
        actions_frame.grid(row=0, column=1, padx=32, pady=16, sticky="e")

        ctk.CTkButton(
            actions_frame,
            text="🖨️  Print",
            height=34,
            width=80,
            corner_radius=6,
            fg_color=PALETTE["secondary"],
            hover_color=PALETTE["secondary_hover"],
            border_width=1,
            border_color=PALETTE["secondary_border"],
            text_color=PALETTE["secondary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._print_report,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions_frame,
            text="💾  Export JSON",
            height=34,
            width=110,
            corner_radius=6,
            fg_color=PALETTE["secondary"],
            hover_color=PALETTE["secondary_hover"],
            border_width=1,
            border_color=PALETTE["secondary_border"],
            text_color=PALETTE["secondary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._export_json,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions_frame,
            text="📄  Download PDF",
            height=34,
            corner_radius=6,
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            text_color=PALETTE["primary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._export_pdf,
        ).pack(side="left")

        # Bottom 1px border
        ctk.CTkFrame(self, height=1, fg_color=PALETTE["border"]).grid(
            row=0, column=0, sticky="sew"
        )

    # ── Scrollable Report Body ────────────────────────────────────────────────
    def _build_scroll_content(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self._scroll.grid_columnconfigure(0, weight=1)

        # 1. Patient & Report Information Strip
        self._build_patient_info_strip()

        # 2. Combined Summary (Prominent at Top)
        self._build_combined_summary_card()

        # 3. Side-by-Side MRI and Spiral Analysis Cards
        self._build_analyses_grid()

        # 4. Regulatory Notice
        self._build_disclaimer_card()

    # ── 1. Patient Info Strip ─────────────────────────────────────────────────
    def _build_patient_info_strip(self) -> None:
        card = ctk.CTkFrame(
            self._scroll,
            fg_color=PALETTE["card"],
            corner_radius=10,
            border_width=1,
            border_color=PALETTE["border"],
        )
        card.pack(fill="x", padx=32, pady=(16, 12))
        card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.lbl_pid = self._make_meta_cell(card, 0, 0, "Patient Reference", "—")
        self.lbl_demographics = self._make_meta_cell(card, 0, 1, "Age & Gender", "Not specified")
        self.lbl_date = self._make_meta_cell(card, 0, 2, "Assessment Date", "—")
        self.lbl_ref_id = self._make_meta_cell(card, 0, 3, "Report Reference ID", "—")

    # ── 2. Combined Summary Card (Prominent at Top) ───────────────────────────
    def _build_combined_summary_card(self) -> None:
        self.synth_card = ctk.CTkFrame(
            self._scroll,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.synth_card.pack(fill="x", padx=32, pady=(0, 12))

        # Title Row
        s_header = ctk.CTkFrame(self.synth_card, fg_color="transparent")
        s_header.pack(fill="x", padx=20, pady=(14, 8))

        ctk.CTkLabel(
            s_header,
            text="Combined Summary",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left")

        self.synth_badge = ctk.CTkLabel(
            s_header,
            text="● Awaiting Inputs",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=PALETTE["text_muted"],
        )
        self.synth_badge.pack(side="right")

        # Synthesis Banner (Highlighted)
        self.synth_banner = ctk.CTkFrame(
            self.synth_card,
            fg_color=PALETTE["normal_badge_bg"],
            corner_radius=8,
            border_width=1,
            border_color=PALETTE["normal_badge_border"],
        )
        self.synth_banner.pack(fill="x", padx=20, pady=(0, 12))

        self.synth_banner_title = ctk.CTkLabel(
            self.synth_banner,
            text="Combined Multi-Modal Synthesis: Awaiting Analysis Inputs",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=PALETTE["normal_badge_text"],
            anchor="w",
        )
        self.synth_banner_title.pack(fill="x", padx=16, pady=(10, 4))

        self.synth_banner_desc = ctk.CTkLabel(
            self.synth_banner,
            text="Please upload and evaluate an MRI scan and Archimedean spiral sketch to generate the combined multi-modal synthesis.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_dark"],
            wraplength=840,
            justify="left",
            anchor="w",
        )
        self.synth_banner_desc.pack(fill="x", padx=16, pady=(0, 10))

        # Side-by-Side Status & Prediction Summary Boxes
        modules_grid = ctk.CTkFrame(self.synth_card, fg_color="transparent")
        modules_grid.pack(fill="x", padx=20, pady=(0, 16))
        modules_grid.grid_columnconfigure((0, 1), weight=1)

        # Left: MRI Summary Box
        self.mri_summary_box = ctk.CTkFrame(
            modules_grid,
            fg_color=PALETTE["box_bg"],
            corner_radius=8,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.mri_summary_box.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")

        mri_sum_hdr = ctk.CTkFrame(self.mri_summary_box, fg_color="transparent")
        mri_sum_hdr.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            mri_sum_hdr,
            text="🧠  Brain MRI Scan Analysis",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left")

        self.mri_sum_status_badge = ctk.CTkLabel(
            mri_sum_hdr,
            text="○ Pending",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=PALETTE["warn"],
        )
        self.mri_sum_status_badge.pack(side="right")

        self.mri_sum_pred = ctk.CTkLabel(
            self.mri_summary_box,
            text="Prediction: Awaiting scan evaluation",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_muted"],
            anchor="w",
        )
        self.mri_sum_pred.pack(anchor="w", padx=14, pady=(0, 2))

        self.mri_sum_conf = ctk.CTkLabel(
            self.mri_summary_box,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
            anchor="w",
        )
        self.mri_sum_conf.pack(anchor="w", padx=14, pady=(0, 10))

        # Right: Spiral Summary Box
        self.spiral_summary_box = ctk.CTkFrame(
            modules_grid,
            fg_color=PALETTE["box_bg"],
            corner_radius=8,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.spiral_summary_box.grid(row=0, column=1, padx=(8, 0), pady=0, sticky="nsew")

        spiral_sum_hdr = ctk.CTkFrame(self.spiral_summary_box, fg_color="transparent")
        spiral_sum_hdr.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            spiral_sum_hdr,
            text="🌀  Spiral Drawing Analysis",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left")

        self.spiral_sum_status_badge = ctk.CTkLabel(
            spiral_sum_hdr,
            text="○ Pending",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=PALETTE["warn"],
        )
        self.spiral_sum_status_badge.pack(side="right")

        self.spiral_sum_pred = ctk.CTkLabel(
            self.spiral_summary_box,
            text="Prediction: Awaiting drawing submission",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_muted"],
            anchor="w",
        )
        self.spiral_sum_pred.pack(anchor="w", padx=14, pady=(0, 2))

        self.spiral_sum_conf = ctk.CTkLabel(
            self.spiral_summary_box,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
            anchor="w",
        )
        self.spiral_sum_conf.pack(anchor="w", padx=14, pady=(0, 10))

    # ── 3. Detailed Analyses Grid (Side-by-Side Cards) ────────────────────────
    def _build_analyses_grid(self) -> None:
        grid = ctk.CTkFrame(self._scroll, fg_color="transparent")
        grid.pack(fill="x", padx=32, pady=(0, 14))
        grid.grid_columnconfigure((0, 1), weight=1)

        # ── Left: MRI Scan Analysis Card ──
        self.mri_card = ctk.CTkFrame(
            grid,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.mri_card.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")

        mri_header = ctk.CTkFrame(self.mri_card, fg_color="transparent")
        mri_header.pack(fill="x", padx=18, pady=(14, 8))

        ctk.CTkLabel(
            mri_header,
            text="🧠  Brain MRI Scan Analysis",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left")

        self.mri_card_status = ctk.CTkLabel(
            mri_header,
            text="○ Pending",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=PALETTE["warn"],
        )
        self.mri_card_status.pack(side="right")

        # MRI Image Preview Frame (Centered, compact 180x180)
        self.mri_preview_frame = ctk.CTkFrame(
            self.mri_card,
            fg_color="#0A0A0A",
            width=THUMB_SIZE[0],
            height=THUMB_SIZE[1],
            corner_radius=8,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.mri_preview_frame.pack(pady=(4, 10))
        self.mri_preview_frame.pack_propagate(False)

        self.mri_preview_label = ctk.CTkLabel(
            self.mri_preview_frame,
            text="No MRI scan loaded",
            text_color=PALETTE["text_muted"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.mri_preview_label.place(relx=0.5, rely=0.5, anchor="center")

        # MRI Prediction Tag
        self.mri_pred_tag = ctk.CTkFrame(
            self.mri_card,
            fg_color=PALETTE["normal_badge_bg"],
            corner_radius=6,
            border_width=1,
            border_color=PALETTE["normal_badge_border"],
        )
        self.mri_pred_tag.pack(fill="x", padx=18, pady=(0, 10))

        self.mri_pred_label = ctk.CTkLabel(
            self.mri_pred_tag,
            text="Model prediction: Awaiting MRI scan upload.",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["normal_badge_text"],
            wraplength=380,
            justify="left",
            anchor="w",
        )
        self.mri_pred_label.pack(fill="x", padx=12, pady=8)

        # MRI Technical Meta Table
        mri_meta_frame = ctk.CTkFrame(self.mri_card, fg_color="transparent")
        mri_meta_frame.pack(fill="x", padx=18, pady=(0, 8))
        mri_meta_frame.grid_columnconfigure((0, 1), weight=1)

        self.mri_meta_arch = self._make_meta_cell(mri_meta_frame, 0, 0, "Model Architecture", "Parkinson CNN (244×244×3)")
        self.mri_meta_prep = self._make_meta_cell(mri_meta_frame, 0, 1, "Preprocessing", "Lanczos 244×244 Rescaling")
        self.mri_meta_file = self._make_meta_cell(mri_meta_frame, 1, 0, "Scan File", "Not selected")

        # MRI Findings
        ctk.CTkLabel(
            self.mri_card,
            text="Model Findings & Pattern Interpretation:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        ).pack(fill="x", padx=18, pady=(2, 2))

        self.mri_explanation_label = ctk.CTkLabel(
            self.mri_card,
            text="The deep learning convolutional model evaluates structural intensity variations across axial brain MRI slices.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=PALETTE["text_muted"],
            wraplength=400,
            justify="left",
            anchor="w",
        )
        self.mri_explanation_label.pack(fill="x", padx=18, pady=(0, 16))

        # ── Right: Spiral Drawing Analysis Card ──
        self.spiral_card = ctk.CTkFrame(
            grid,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.spiral_card.grid(row=0, column=1, padx=(8, 0), pady=0, sticky="nsew")

        spiral_header = ctk.CTkFrame(self.spiral_card, fg_color="transparent")
        spiral_header.pack(fill="x", padx=18, pady=(14, 8))

        ctk.CTkLabel(
            spiral_header,
            text="🌀  Archimedean Spiral Analysis",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left")

        self.spiral_card_status = ctk.CTkLabel(
            spiral_header,
            text="○ Pending",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=PALETTE["warn"],
        )
        self.spiral_card_status.pack(side="right")

        # Spiral Image Preview Frame (Centered, compact 180x180)
        self.spiral_preview_frame = ctk.CTkFrame(
            self.spiral_card,
            fg_color="#FFFFFF",
            width=THUMB_SIZE[0],
            height=THUMB_SIZE[1],
            corner_radius=8,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.spiral_preview_frame.pack(pady=(4, 10))
        self.spiral_preview_frame.pack_propagate(False)

        self.spiral_preview_label = ctk.CTkLabel(
            self.spiral_preview_frame,
            text="No spiral drawing loaded",
            text_color=PALETTE["text_muted"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.spiral_preview_label.place(relx=0.5, rely=0.5, anchor="center")

        # Spiral Prediction Tag
        self.spiral_pred_tag = ctk.CTkFrame(
            self.spiral_card,
            fg_color=PALETTE["normal_badge_bg"],
            corner_radius=6,
            border_width=1,
            border_color=PALETTE["normal_badge_border"],
        )
        self.spiral_pred_tag.pack(fill="x", padx=18, pady=(0, 10))

        self.spiral_pred_label = ctk.CTkLabel(
            self.spiral_pred_tag,
            text="Spiral drawing status: Awaiting drawing submission.",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["normal_badge_text"],
            wraplength=380,
            justify="left",
            anchor="w",
        )
        self.spiral_pred_label.pack(fill="x", padx=12, pady=8)

        # Spiral Technical Meta Table
        spiral_meta_frame = ctk.CTkFrame(self.spiral_card, fg_color="transparent")
        spiral_meta_frame.pack(fill="x", padx=18, pady=(0, 8))
        spiral_meta_frame.grid_columnconfigure((0, 1), weight=1)

        self.spiral_meta_arch = self._make_meta_cell(spiral_meta_frame, 0, 0, "Model Architecture", "Archimedean Spiral CNN (244×244×3)")
        self.spiral_meta_file = self._make_meta_cell(spiral_meta_frame, 0, 1, "Drawing File", "Not selected")
        self.spiral_meta_geo = self._make_meta_cell(spiral_meta_frame, 1, 0, "Geometry & Stroke", "Verified on submit")

        # Spiral Observations
        ctk.CTkLabel(
            self.spiral_card,
            text="Visual & Kinematic Observations:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        ).pack(fill="x", padx=18, pady=(2, 2))

        self.spiral_explanation_label = ctk.CTkLabel(
            self.spiral_card,
            text="Evaluates fine-motor kinematics, stroke irregularity, and tremor deviations on Archimedean spiral sketches.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=PALETTE["text_muted"],
            wraplength=400,
            justify="left",
            anchor="w",
        )
        self.spiral_explanation_label.pack(fill="x", padx=18, pady=(0, 16))

    # ── 4. Disclaimer Box ─────────────────────────────────────────────────────
    def _build_disclaimer_card(self) -> None:
        card = ctk.CTkFrame(
            self._scroll,
            fg_color=PALETTE["amber_bg"],
            corner_radius=10,
            border_width=1,
            border_color=PALETTE["amber_border"],
        )
        card.pack(fill="x", padx=32, pady=(0, 20))

        ctk.CTkLabel(
            card,
            text="⚠️  Academic Research & Non-Diagnostic Notice",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=PALETTE["amber_text"],
        ).pack(anchor="w", padx=18, pady=(8, 2))

        disclaimer_text = (
            "This software is an academic AI research prototype developed exclusively for scientific investigation. "
            "It is NOT a certified medical device, nor a clinically validated diagnostic tool. Neither an automated MRI scan "
            "nor an Archimedean spiral sketch can independently confirm or exclude Parkinson's disease. Comprehensive medical "
            "evaluation requires in-person clinical assessment by a licensed neurologist, including motor UPDRS scoring, "
            "patient history, and expert radiologist review."
        )
        ctk.CTkLabel(
            card,
            text=disclaimer_text,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=PALETTE["text_dark"],
            wraplength=840,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 8))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _make_meta_cell(self, parent: Any, r: int, c: int, title: str, val: str) -> ctk.CTkLabel:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=r, column=c, sticky="w", padx=12, pady=6)

        ctk.CTkLabel(
            box,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=PALETTE["text_muted"],
        ).pack(anchor="w")

        lbl = ctk.CTkLabel(
            box,
            text=val,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_dark"],
        )
        lbl.pack(anchor="w")
        return lbl

    # ── Data Synchronization & Dynamic Refresh ────────────────────────────────
    def refresh(self) -> None:
        """
        Called when navigating to this frame.
        Pulls latest data from the app controller and refreshes all sections.
        """
        mri_res = getattr(self.app_controller, "current_result", None)
        spiral_res = getattr(self.app_controller, "current_spiral_result", None)
        p_data = getattr(self.app_controller, "patient_data", {})
        aid = getattr(self.app_controller, "current_analysis_id", self._analysis_id)
        pt_code = getattr(self.app_controller, "current_patient_code", self._patient_code)

        if mri_res:
            self._result = mri_res
        if aid:
            self._analysis_id = aid
        if pt_code:
            self._patient_code = pt_code

        self._update_ui_state(self._result, spiral_res, p_data)

    def display_result(self, result: dict, analysis_id: str = "", patient_code: str = "") -> None:
        """Update report with fresh analysis data from MRI and Spiral modules."""
        self._result = result
        self._analysis_id = analysis_id
        self._patient_code = patient_code

        spiral_res = getattr(self.app_controller, "current_spiral_result", None)
        p_data = getattr(self.app_controller, "patient_data", {})
        self._update_ui_state(result, spiral_res, p_data)

    def _update_ui_state(self, mri_res: Optional[dict], spiral_res: Optional[dict], p_data: dict) -> None:
        mri_available = bool(mri_res and mri_res.get("success"))
        spiral_available = bool(spiral_res and spiral_res.get("success"))

        # ── 1. Update Header Timestamp & Status ──
        ts_str = ""
        if mri_res and mri_res.get("analysis_timestamp"):
            ts_str = mri_res["analysis_timestamp"]
        elif spiral_res and spiral_res.get("timestamp"):
            ts_str = spiral_res["timestamp"]

        if ts_str:
            try:
                dt = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                self.timestamp_label.configure(text=f"Evaluated on {dt.strftime('%B %d, %Y at %H:%M:%S UTC')}")
                self.lbl_date.configure(text=dt.strftime("%Y-%m-%d %H:%M"))
            except Exception:
                self.timestamp_label.configure(text=f"Evaluated at {ts_str[:19]}")
                self.lbl_date.configure(text=ts_str[:19])

        if mri_available and spiral_available:
            self.report_status_badge.configure(text="● Multi-Modal Complete", text_color=PALETTE["success"])
        elif mri_available:
            self.report_status_badge.configure(text="● Partial Evaluation (Awaiting Spiral)", text_color=PALETTE["warn"])
        elif spiral_available:
            self.report_status_badge.configure(text="● Partial Evaluation (Awaiting MRI)", text_color=PALETTE["warn"])
        else:
            self.report_status_badge.configure(text="● Awaiting Analysis Inputs", text_color=PALETTE["text_muted"])

        # ── 2. Patient Demographics ──
        pid_val = self._patient_code or (p_data.get("patient_code") if p_data else "Anonymous Patient")
        self.lbl_pid.configure(text=pid_val or "Anonymous Patient")

        aid_disp = self._analysis_id[:13] + "…" if len(self._analysis_id) > 13 else (self._analysis_id or "—")
        self.lbl_ref_id.configure(text=aid_disp)

        age_text = f"{p_data.get('age')} years" if p_data.get("age") else "Age: N/A"
        gender_text = str(p_data.get("gender")) if p_data.get("gender") else "Gender: N/A"
        self.lbl_demographics.configure(text=f"{age_text} · {gender_text}")

        # ── 3. MRI Analysis Card & Status ──
        mri_is_pd = False
        if mri_available:
            self.mri_card_status.configure(text="● Completed", text_color=PALETTE["success"])
            self.mri_sum_status_badge.configure(text="● Completed", text_color=PALETTE["success"])

            pred_idx = mri_res.get("predicted_index", -1)
            pred_class = mri_res.get("predicted_class", "")
            mri_is_pd = (
                pred_idx == 1 or
                "parkinson" in pred_class.lower() and "no" not in pred_class.lower()
            )

            raw_score = mri_res.get("raw_score")  # noqa: F841 (retained for future use)

            img_p = mri_res.get("image_path", "")
            if img_p:
                self.mri_meta_file.configure(text=Path(img_p).name[:20])

            if mri_is_pd:
                self.mri_pred_tag.configure(fg_color=PALETTE["pd_badge_bg"], border_color=PALETTE["pd_badge_border"])
                self.mri_pred_label.configure(text="Model prediction: Parkinson's-related pattern detected.", text_color=PALETTE["pd_badge_text"])
                self.mri_sum_pred.configure(text="Pattern detected", text_color=PALETTE["primary"])
            else:
                self.mri_pred_tag.configure(fg_color=PALETTE["normal_badge_bg"], border_color=PALETTE["normal_badge_border"])
                self.mri_pred_label.configure(text="Model prediction: No Parkinson's-related pattern detected.", text_color=PALETTE["normal_badge_text"])
                self.mri_sum_pred.configure(text="No pattern detected (Control)", text_color=PALETTE["text_dark"])

            expl = mri_res.get("explanation")
            if expl:
                self.mri_explanation_label.configure(text=expl)

            # Thumbnail
            orig_arr = mri_res.get("original_array")
            if orig_arr is not None and len(orig_arr) > 0:
                try:
                    if hasattr(self.app_controller, "preprocessor") and self.app_controller.preprocessor:
                        pil_img = self.app_controller.preprocessor.array_to_display_image(orig_arr)
                    else:
                        pil_img = Image.fromarray(orig_arr)
                    pil_img = pil_img.resize(THUMB_SIZE, Image.LANCZOS)
                    self._ctk_mri_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=THUMB_SIZE)
                    self.mri_preview_label.configure(image=self._ctk_mri_image, text="")
                except Exception as e:
                    logger.warning("Could not render MRI thumbnail: %s", e)
            elif img_p and os.path.isfile(img_p):
                try:
                    pil_img = Image.open(img_p).convert("RGB")
                    pil_img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                    self._ctk_mri_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                    self.mri_preview_label.configure(image=self._ctk_mri_image, text="")
                except Exception as e:
                    logger.warning("Could not render MRI thumbnail from path: %s", e)
        else:
            self.mri_card_status.configure(text="○ Pending", text_color=PALETTE["warn"])
            self.mri_sum_status_badge.configure(text="○ Pending", text_color=PALETTE["warn"])
            self.mri_sum_pred.configure(text="Status: Pending scan evaluation", text_color=PALETTE["text_muted"])
            self.mri_sum_conf.configure(text="")
            self.mri_preview_label.configure(image="", text="No MRI scan loaded")

        # ── 4. Spiral Analysis Card & Status ──
        spiral_is_pd = False
        spiral_has_active_score = False
        if spiral_available:
            sp_status = spiral_res.get("status", "Completed")
            sp_pred = spiral_res.get("model_prediction", "Standby")
            sp_raw = spiral_res.get("raw_score")

            self.spiral_card_status.configure(text=f"● {sp_status[:12]}", text_color=PALETTE["success"])
            self.spiral_sum_status_badge.configure(text="● Completed", text_color=PALETTE["success"])

            if "is_parkinson" in spiral_res:
                spiral_has_active_score = True
                spiral_is_pd = bool(spiral_res["is_parkinson"])
            elif sp_raw is not None:
                spiral_has_active_score = True
                if "motor irregularities" in sp_pred.lower() or "parkinson" in sp_pred.lower() or "irregular" in sp_pred.lower():
                    spiral_is_pd = True
                elif "without" in sp_pred.lower() or "healthy" in sp_pred.lower() or "control" in sp_pred.lower():
                    spiral_is_pd = False
                else:
                    spiral_is_pd = (sp_raw >= 0.5)

            sp_path = spiral_res.get("image_path", "")
            if sp_path:
                self.spiral_meta_file.configure(text=Path(sp_path).name[:20])

            sp_mod_info = spiral_res.get("model_info", {})
            if sp_mod_info.get("is_yolo"):
                self.spiral_meta_arch.configure(text="YOLO Classifier (224×224×3)")
            else:
                self.spiral_meta_arch.configure(text="Archimedean Spiral CNN (244×244×3)")

            obs = spiral_res.get("observations", {})
            geo = obs.get("Image Geometry") or obs.get("dimensions", "Verified")
            density = obs.get("Stroke Coverage") or "Analyzed"
            self.spiral_meta_geo.configure(text=f"{geo} · {density}")

            if spiral_is_pd:
                self.spiral_pred_tag.configure(fg_color=PALETTE["pd_badge_bg"], border_color=PALETTE["pd_badge_border"])
                self.spiral_pred_label.configure(text=f"Prediction: {sp_pred}", text_color=PALETTE["pd_badge_text"])
                self.spiral_sum_pred.configure(text="Parkinson's pattern detected", text_color=PALETTE["primary"])
            else:
                self.spiral_pred_tag.configure(fg_color=PALETTE["normal_badge_bg"], border_color=PALETTE["normal_badge_border"])
                self.spiral_pred_label.configure(text=f"Prediction: {sp_pred}", text_color=PALETTE["normal_badge_text"])
                self.spiral_sum_pred.configure(text="No pattern detected", text_color=PALETTE["text_dark"])

            if obs:
                obs_bullets = [f"• {k}: {v}" for k, v in obs.items()]
                self.spiral_explanation_label.configure(text="\n".join(obs_bullets[:3]))

            # Thumbnail
            if sp_path and os.path.isfile(sp_path):
                try:
                    sp_pil = Image.open(sp_path).convert("RGB")
                    sp_pil.thumbnail(THUMB_SIZE, Image.LANCZOS)
                    self._ctk_spiral_image = ctk.CTkImage(light_image=sp_pil, dark_image=sp_pil, size=sp_pil.size)
                    self.spiral_preview_label.configure(image=self._ctk_spiral_image, text="")
                except Exception as e:
                    logger.warning("Could not render spiral thumbnail: %s", e)
        else:
            self.spiral_card_status.configure(text="○ Pending", text_color=PALETTE["warn"])
            self.spiral_sum_status_badge.configure(text="○ Pending", text_color=PALETTE["warn"])
            self.spiral_sum_pred.configure(text="Status: Pending drawing submission", text_color=PALETTE["text_muted"])
            self.spiral_sum_conf.configure(text="")
            self.spiral_preview_label.configure(image="", text="No spiral drawing loaded")

        # ── 5. Combined Summary Synthesis ──
        if mri_available and spiral_available:
            if spiral_has_active_score:
                if mri_is_pd and spiral_is_pd:
                    self.synth_badge.configure(text="● Concordant (Detected)", text_color=PALETTE["primary"])
                    self.synth_banner.configure(fg_color=PALETTE["pd_badge_bg"], border_color=PALETTE["pd_badge_border"])
                    self.synth_banner_title.configure(text="Concordant Multi-Modal Findings (Pattern Detected)", text_color=PALETTE["pd_badge_text"])
                    self.synth_banner_desc.configure(
                        text="Both the deep learning MRI model and the Archimedean spiral drawing analysis identified patterns "
                             "associated with Parkinsonian disease features. Concordance across independent structural imaging and "
                             "motor drawing modalities warrants clinical review with a movement disorder specialist. "
                             "This automated synthesis does not constitute a clinical diagnosis."
                    )
                elif not mri_is_pd and not spiral_is_pd:
                    self.synth_badge.configure(text="● Concordant (Control)", text_color=PALETTE["success"])
                    self.synth_banner.configure(fg_color=PALETTE["normal_badge_bg"], border_color=PALETTE["normal_badge_border"])
                    self.synth_banner_title.configure(text="Concordant Negative Findings (No Pattern Detected)", text_color=PALETTE["normal_badge_text"])
                    self.synth_banner_desc.configure(
                        text="Neither the brain MRI neuroimaging scan nor the spiral drawing exhibited distinctive features correlated with "
                             "the Parkinson's training cohort. This observational finding does not exclude early pathology or non-motor onset."
                    )
                else:
                    self.synth_badge.configure(text="● Divergent Findings", text_color=PALETTE["warn"])
                    self.synth_banner.configure(fg_color=PALETTE["amber_bg"], border_color=PALETTE["amber_border"])
                    self.synth_banner_title.configure(text="Divergent Multi-Modal Findings (Disagreement Across Modalities)", text_color=PALETTE["warn"])
                    self.synth_banner_desc.configure(
                        text="The MRI scan evaluation and spiral sketch findings diverge. In clinical neurology, divergence between "
                             "structural imaging and motor manifestations is common: early structural alterations can precede tremor, "
                             "or essential tremor may affect motor sketches while 3T MRI is unremarkable. Both results are presented "
                             "transparently without forcing a single diagnosis; comprehensive in-person neurological examination is essential."
                    )
            else:
                self.synth_badge.configure(text="● MRI Complete · Spiral Verified", text_color=PALETTE["text_dark"])
                self.synth_banner.configure(fg_color=PALETTE["normal_badge_bg"], border_color=PALETTE["normal_badge_border"])
                self.synth_banner_title.configure(text="Multi-Modal Synthesis: MRI Evaluated · Spiral Verified", text_color=PALETTE["text_dark"])
                self.synth_banner_desc.configure(
                    text="The MRI convolutional model completed inference. The uploaded Archimedean spiral sketch was verified "
                         "for geometry and stroke contrast and remains on integration standby. "
                         "No synthetic numerical combined risk score is calculated to protect medical integrity."
                )
        elif mri_available:
            self.synth_badge.configure(text="● Partial Evaluation (MRI Complete)", text_color=PALETTE["warn"])
            self.synth_banner.configure(fg_color=PALETTE["normal_badge_bg"], border_color=PALETTE["normal_badge_border"])
            self.synth_banner_title.configure(text="Assessment Synthesis: Partial Evaluation (Awaiting Spiral Analysis)", text_color=PALETTE["normal_badge_text"])
            self.synth_banner_desc.configure(
                text="Brain MRI scan was evaluated successfully. The Archimedean spiral drawing has not yet been submitted. "
                     "The multi-modal combined assessment is incomplete and currently reflects only neuroimaging findings."
            )
        elif spiral_available:
            self.synth_badge.configure(text="● Partial Evaluation (Spiral Complete)", text_color=PALETTE["warn"])
            self.synth_banner.configure(fg_color=PALETTE["normal_badge_bg"], border_color=PALETTE["normal_badge_border"])
            self.synth_banner_title.configure(text="Assessment Synthesis: Partial Evaluation (Awaiting MRI Scan)", text_color=PALETTE["normal_badge_text"])
            self.synth_banner_desc.configure(
                text="Archimedean spiral drawing was analyzed successfully. The Brain MRI scan has not yet been submitted. "
                     "The multi-modal combined assessment is incomplete and currently reflects only fine-motor drawing data."
            )
        else:
            self.synth_badge.configure(text="● Awaiting Inputs", text_color=PALETTE["text_muted"])
            self.synth_banner.configure(fg_color=PALETTE["normal_badge_bg"], border_color=PALETTE["normal_badge_border"])
            self.synth_banner_title.configure(text="Combined Multi-Modal Synthesis: Awaiting Analysis Inputs", text_color=PALETTE["normal_badge_text"])
            self.synth_banner_desc.configure(
                text="Please upload and evaluate an MRI scan and Archimedean spiral sketch to generate the combined multi-modal synthesis."
            )

    # ── Export & Print Handlers ───────────────────────────────────────────────
    def _export_pdf(self) -> None:
        """Export comprehensive combined PDF report."""
        spiral_res = getattr(self.app_controller, "current_spiral_result", None)
        if not self._result and not spiral_res:
            messagebox.showinfo("Export Notice", "No analysis result is currently available to export.")
            return

        if hasattr(self.app_controller, "generate_report") and self._result:
            self.app_controller.generate_report(
                self._result, self._analysis_id, self._patient_code
            )
        else:
            # Standalone export if app_controller is not hooked
            from app.reports import ReportGenerator
            save_path = filedialog.asksaveasfilename(
                title="Export Assessment PDF",
                defaultextension=".pdf",
                filetypes=[("PDF Documents", "*.pdf")],
                initialfile=f"Parkinova_Assessment_{self._analysis_id[:8] if self._analysis_id else 'Report'}.pdf",
            )
            if save_path:
                gen = ReportGenerator()
                ok = gen.generate_combined_report(
                    mri_result=self._result or {},
                    spiral_result=spiral_res,
                    analysis_id=self._analysis_id or "ASSESSMENT",
                    patient_code=self._patient_code or "Anonymous",
                    include_images=True,
                    save_path=save_path,
                    patient_data=getattr(self.app_controller, "patient_data", {}),
                )
                if ok:
                    messagebox.showinfo("Report Exported", f"PDF report saved successfully to:\n{save_path}")

    def _export_json(self) -> None:
        """Export complete structured assessment data to JSON file."""
        spiral_res = getattr(self.app_controller, "current_spiral_result", None)
        if not self._result and not spiral_res:
            messagebox.showinfo("Export Notice", "No analysis result is currently available to export.")
            return

        aid = self._analysis_id or "Assessment"
        save_path = filedialog.asksaveasfilename(
            title="Export Assessment JSON",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile=f"Parkinova_Assessment_{aid[:8]}_{datetime.datetime.now():%Y%m%d_%H%M%S}.json",
        )
        if not save_path:
            return

        patient_data = getattr(self.app_controller, "patient_data", {})

        mri_dict = {}
        if self._result:
            mri_dict = {
                "status": "Completed" if self._result.get("success") else "Failed",
                "predicted_class": self._result.get("predicted_class"),
                "predicted_index": self._result.get("predicted_index"),
                "raw_score": self._result.get("raw_score"),
                "model_name": "parkinson_cnn",
                "image_filename": Path(self._result.get("image_path", "")).name if self._result.get("image_path") else "",
                "preprocessing_info": self._result.get("preprocessing_info"),
                "explanation": self._result.get("explanation"),
            }
        else:
            mri_dict = {"status": "Pending"}

        spiral_dict = {}
        if spiral_res:
            spiral_dict = {
                "status": spiral_res.get("status"),
                "model_prediction": spiral_res.get("model_prediction"),
                "raw_score": spiral_res.get("raw_score"),
                "observations": spiral_res.get("observations"),
                "image_filename": Path(spiral_res.get("image_path", "")).name if spiral_res.get("image_path") else "",
            }
        else:
            spiral_dict = {"status": "Pending"}

        export_data = {
            "application": "Parkinova Parkinson's Analysis Platform",
            "version": "2.0.0",
            "report_title": "Medical Assessment Report",
            "analysis_id": self._analysis_id,
            "patient_code": self._patient_code,
            "timestamp": (self._result.get("analysis_timestamp") if self._result else spiral_res.get("timestamp") if spiral_res else datetime.datetime.now().isoformat()),
            "patient_demographics": {
                "age": patient_data.get("age"),
                "gender": patient_data.get("gender"),
                "responses": patient_data.get("responses"),
            },
            "mri_analysis": mri_dict,
            "spiral_analysis": spiral_dict,
            "regulatory_notice": "Academic research prototype. Not for clinical diagnosis.",
        }

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            messagebox.showinfo("Export Successful", f"Structured JSON data saved to:\n{save_path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Could not write JSON file: {exc}")

    def _print_report(self) -> None:
        """Trigger printing of generated PDF via system default PDF viewer."""
        spiral_res = getattr(self.app_controller, "current_spiral_result", None)
        if not self._result and not spiral_res:
            messagebox.showinfo("Print Notice", "No analysis result is currently available to print.")
            return

        import tempfile
        from app.reports import ReportGenerator

        gen = ReportGenerator()
        temp_dir = tempfile.gettempdir()
        aid = self._analysis_id or "Assessment"
        print_pdf = os.path.join(temp_dir, f"Parkinova_Print_{aid[:8]}.pdf")

        try:
            ok = gen.generate_combined_report(
                mri_result=self._result or {},
                spiral_result=spiral_res,
                analysis_id=self._analysis_id or "ASSESSMENT",
                patient_code=self._patient_code or "Anonymous",
                include_images=True,
                save_path=print_pdf,
                patient_data=getattr(self.app_controller, "patient_data", {}),
            )
            if ok and os.path.exists(print_pdf):
                try:
                    os.startfile(print_pdf)
                except Exception:
                    try:
                        import subprocess
                        subprocess.Popen(["explorer", print_pdf.replace("/", "\\")])
                    except Exception:
                        pass
                messagebox.showinfo(
                    "Print Ready",
                    f"Assessment report compiled for printing.\nOpened in default PDF reader at:\n{print_pdf}",
                )
            else:
                messagebox.showerror("Print Failed", "Could not compile print report.")
        except Exception as exc:
            messagebox.showerror("Print Error", f"Print failed: {exc}")
