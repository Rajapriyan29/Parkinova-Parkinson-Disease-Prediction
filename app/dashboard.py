"""
dashboard.py
============
Clinical Research Dashboard for Parkinova.
Features:
- Professional healthcare research interface in clinical light theme
- Welcome banner with live timestamp and researcher display
- Quick-access "Start MRI Analysis" card
- Live CNN model readiness indicator with model specifications
- Real session and database analysis metrics (no fake statistics)
- Recent analysis history table with prediction status badges (no confidence scores)
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import customtkinter as ctk

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
    "success": "#123F2D",          # Deep forest green
    "success_bg": "#EAE5CC",       # Pale beige
    "success_border": "#B8C4A5",   # Muted sage green
    "error": "#F0442E",            # Coral red
    "error_bg": "#FDF0EE",         # Soft coral tint
    "error_border": "#F8C0B8",     # Coral border
    "warn": "#D77B65",             # Soft terracotta
    "warn_bg": "#FDF4F0",          # Soft terracotta tint
    "warn_border": "#EBC6BC",      # Soft terracotta border
    "row_alt": "#EAE5CC",          # Subtle Background: Pale beige alternating row
}


class DashboardFrame(ctk.CTkFrame):
    """
    Main overview and dashboard landing screen.
    """

    def __init__(self, parent, app_controller) -> None:
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0)
        self.app_controller = app_controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_top_cards()
        self._build_recent_table()

    def _build_header(self):
        """Top welcome and system status header."""
        header_card = ctk.CTkFrame(
            self._scroll,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        header_card.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 16))
        header_card.grid_columnconfigure(0, weight=1)
        header_card.grid_columnconfigure(1, weight=0)

        left = ctk.CTkFrame(header_card, fg_color="transparent")
        left.grid(row=0, column=0, padx=24, pady=20, sticky="w")

        user_display = getattr(self.app_controller, "logged_in_display", "Researcher")
        self.welcome_label = ctk.CTkLabel(
            left,
            text=f"Welcome, {user_display}",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=PALETTE["text_dark"],
        )
        self.welcome_label.pack(anchor="w")

        today = datetime.now().strftime("%A, %B %d, %Y")
        ctk.CTkLabel(
            left,
            text=f"Clinical Research Workspace  ·  {today}",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=PALETTE["text_muted"],
        ).pack(anchor="w", pady=(2, 0))

        # Right CTA
        right = ctk.CTkFrame(header_card, fg_color="transparent")
        right.grid(row=0, column=1, padx=24, pady=20, sticky="e")

        ctk.CTkButton(
            right,
            text="➕  New MRI Analysis",
            height=40,
            corner_radius=8,
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            text_color=PALETTE["primary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=lambda: self.app_controller.navigate_to("upload"),
        ).pack(side="right")

        ctk.CTkButton(
            right,
            text="📋  Go to Patient Form",
            height=40,
            corner_radius=8,
            fg_color=PALETTE["secondary"],
            hover_color=PALETTE["secondary_hover"],
            border_width=1,
            border_color=PALETTE["secondary_border"],
            text_color=PALETTE["secondary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=lambda: self.app_controller.navigate_to("patient_form"),
        ).pack(side="right", padx=(0, 10))

    def _build_top_cards(self):
        """Three clinical cards: Model Status, Quick Analysis, Session Metric."""
        container = ctk.CTkFrame(self._scroll, fg_color="transparent")
        container.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 16))
        container.grid_columnconfigure((0, 1, 2), weight=1, uniform="top_cards")

        # 1. Model Status Card
        self.model_card = ctk.CTkFrame(
            container,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.model_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # 2. Quick Workflow Card
        workflow_card = ctk.CTkFrame(
            container,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        workflow_card.grid(row=0, column=1, sticky="nsew", padx=5)

        # 3. Session Statistics Card
        self.stats_card = ctk.CTkFrame(
            container,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.stats_card.grid(row=0, column=2, sticky="nsew", padx=(10, 0))

        self._populate_model_card()
        self._populate_workflow_card(workflow_card)
        self._populate_stats_card()

    def _populate_model_card(self):
        loaded = bool(getattr(self.app_controller, "model_loaded", False))
        info = getattr(self.app_controller, "model_info", {}) or {}
        model_sig = (loaded, info.get("model_name"), str(info.get("input_shape")))
        if getattr(self, "_last_model_sig", None) == model_sig and len(self.model_card.winfo_children()) > 0:
            return
        self._last_model_sig = model_sig

        for w in self.model_card.winfo_children():
            w.destroy()

        inner = ctk.CTkFrame(self.model_card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=18)

        ctk.CTkLabel(
            inner,
            text="CNN Inference Engine",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_muted"],
        ).pack(anchor="w")

        badge_frame = ctk.CTkFrame(
            inner,
            fg_color=PALETTE["success_bg"] if loaded else PALETTE["warn_bg"],
            corner_radius=6,
            border_width=1,
            border_color=PALETTE["success_border"] if loaded else PALETTE["warn_border"],
        )
        badge_frame.pack(anchor="w", pady=(6, 8))

        status_text = "● Model Loaded & Ready" if loaded else "● Initializing Model…"
        badge_color = PALETTE["success"] if loaded else PALETTE["warn"]
        ctk.CTkLabel(
            badge_frame,
            text=status_text,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=badge_color,
        ).pack(padx=10, pady=4)

        dim = info.get("input_shape", (244, 244, 3))
        m_name = info.get("model_name", "parkinson_cnn")
        ctk.CTkLabel(
            inner,
            text=f"Model: {m_name}\nTarget Input: {dim}\nMode: Offline Local Inference",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
            justify="left",
            anchor="w",
        ).pack(anchor="w")

    def _populate_workflow_card(self, parent: ctk.CTkFrame):
        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=18)

        ctk.CTkLabel(
            inner,
            text="Analysis Pipeline",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_muted"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            inner,
            text="1. Patient Details\n2. MRI Scans\n3. Spiral Analysis\n4. Combined Assessment",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=PALETTE["text_dark"],
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(6, 8))

        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(anchor="w")

        ctk.CTkButton(
            btn_row,
            text="Patient Details →",
            height=28,
            corner_radius=6,
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            text_color=PALETTE["primary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=lambda: self.app_controller.navigate_to("patient_form"),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row,
            text="MRI Scans →",
            height=28,
            corner_radius=6,
            fg_color=PALETTE["secondary"],
            hover_color=PALETTE["secondary_hover"],
            border_width=1,
            border_color=PALETTE["secondary_border"],
            text_color=PALETTE["secondary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=lambda: self.app_controller.navigate_to("upload"),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row,
            text="Spiral →",
            height=28,
            corner_radius=6,
            fg_color=PALETTE["secondary"],
            hover_color=PALETTE["secondary_hover"],
            border_width=1,
            border_color=PALETTE["secondary_border"],
            text_color=PALETTE["secondary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=lambda: self.app_controller.navigate_to("spiral"),
        ).pack(side="left")

    def _populate_stats_card(self):
        total_count = 0
        if getattr(self.app_controller, "db", None):
            try:
                stats = self.app_controller.db.get_session_stats()
                total_count = stats.get("total_analyses", 0)
            except Exception:
                pass

        if getattr(self, "_last_total_count", None) == total_count and len(self.stats_card.winfo_children()) > 0:
            return
        self._last_total_count = total_count

        for w in self.stats_card.winfo_children():
            w.destroy()

        inner = ctk.CTkFrame(self.stats_card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=18)

        ctk.CTkLabel(
            inner,
            text="Historical Database",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_muted"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            inner,
            text=str(total_count),
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=PALETTE["primary"],
        ).pack(anchor="w", pady=(2, 2))

        ctk.CTkLabel(
            inner,
            text="Verified MRI scans recorded in local SQLite database",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
            wraplength=220,
            justify="left",
            anchor="w",
        ).pack(anchor="w")

    def _build_recent_table(self):
        """Recent evaluations list table without confidence scores."""
        card = ctk.CTkFrame(
            self._scroll,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        card.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 28))
        card.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 12))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="Recent Analysis Evaluations",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left")

        ctk.CTkButton(
            hdr,
            text="View Full History  →",
            height=30,
            corner_radius=6,
            fg_color="transparent",
            hover_color=PALETTE["secondary_hover"],
            text_color=PALETTE["text_dark"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=lambda: self.app_controller.navigate_to("history"),
        ).pack(side="right")

        self.recent_container = ctk.CTkFrame(card, fg_color="transparent")
        self.recent_container.pack(fill="x", padx=24, pady=(0, 20))
        self.recent_container.grid_columnconfigure(0, weight=1)

        self._populate_recent_records()

    def _populate_recent_records(self):
        records = []
        if getattr(self.app_controller, "db", None):
            try:
                records = self.app_controller.db.get_recent_analyses(limit=6)
            except Exception:
                pass

        sig = tuple((str(r.get("id")), str(r.get("created_at")), str(r.get("predicted_class"))) for r in records)
        if getattr(self, "_last_recent_sig", None) == sig and len(self.recent_container.winfo_children()) > 0:
            return
        self._last_recent_sig = sig

        for w in self.recent_container.winfo_children():
            w.destroy()

        if not records:
            empty_box = ctk.CTkFrame(self.recent_container, fg_color="transparent")
            empty_box.pack(fill="x", pady=30)
            ctk.CTkLabel(
                empty_box,
                text="No MRI evaluations recorded yet.\nClick 'New MRI Analysis' to upload and test your first scan.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=PALETTE["text_muted"],
                justify="center",
            ).pack()
            return

        # Table header row
        table_hdr = ctk.CTkFrame(self.recent_container, fg_color=PALETTE["row_alt"], height=36, corner_radius=6)
        table_hdr.pack(fill="x", pady=(0, 6))
        table_hdr.grid_columnconfigure(0, weight=2)
        table_hdr.grid_columnconfigure(1, weight=3)
        table_hdr.grid_columnconfigure(2, weight=4)
        table_hdr.grid_columnconfigure(3, weight=2)

        for col, title in enumerate(["Timestamp", "File Reference", "Model Finding", "Patient Code"]):
            ctk.CTkLabel(
                table_hdr,
                text=title,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=PALETTE["text_muted"],
                anchor="w",
            ).grid(row=0, column=col, padx=12, pady=6, sticky="w")

        # Table data rows
        for i, rec in enumerate(records):
            bg = PALETTE["card"] if i % 2 == 0 else PALETTE["row_alt"]
            row = ctk.CTkFrame(self.recent_container, fg_color=bg, height=44, corner_radius=6)
            row.pack(fill="x", pady=2)
            row.grid_columnconfigure(0, weight=2)
            row.grid_columnconfigure(1, weight=3)
            row.grid_columnconfigure(2, weight=4)
            row.grid_columnconfigure(3, weight=2)

            ts_raw = str(rec.get("created_at", ""))[:16].replace("T", " ")
            fname = str(rec.get("image_filename", "—"))
            pred = str(rec.get("predicted_class", "—"))
            patient = str(rec.get("patient_code") or "—")

            # Col 0: Timestamp
            ctk.CTkLabel(
                row,
                text=ts_raw,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=PALETTE["text_muted"],
                anchor="w",
            ).grid(row=0, column=0, padx=12, pady=8, sticky="w")

            # Col 1: Filename
            ctk.CTkLabel(
                row,
                text=fname[:26] + ("…" if len(fname) > 26 else ""),
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=PALETTE["text_dark"],
                anchor="w",
            ).grid(row=0, column=1, padx=12, pady=8, sticky="w")

            # Col 2: Prediction Badge
            is_pd = "parkinson" in pred.lower() and "no" not in pred.lower()
            badge_fg = PALETTE["error_bg"] if is_pd else PALETTE["success_bg"]
            badge_border = PALETTE["error_border"] if is_pd else PALETTE["success_border"]
            badge_text = PALETTE["error"] if is_pd else PALETTE["success"]

            clean_pred_txt = "Parkinson's Pattern" if is_pd else "No Pattern Detected"
            p_badge = ctk.CTkFrame(row, fg_color=badge_fg, border_width=1, border_color=badge_border, corner_radius=4)
            p_badge.grid(row=0, column=2, padx=12, pady=6, sticky="w")
            ctk.CTkLabel(
                p_badge,
                text=clean_pred_txt,
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color=badge_text,
            ).pack(padx=8, pady=2)

            # Col 3: Patient
            ctk.CTkLabel(
                row,
                text=patient,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=PALETTE["text_muted"],
                anchor="w",
            ).grid(row=0, column=3, padx=12, pady=8, sticky="w")

    def refresh(self):
        """Called when user navigates to the dashboard."""
        user_display = getattr(self.app_controller, "logged_in_display", "Researcher")
        if hasattr(self, "welcome_label"):
            self.welcome_label.configure(text=f"Welcome, {user_display}")
        self._populate_model_card()
        self._populate_stats_card()
        self._populate_recent_records()
