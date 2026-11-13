"""
settings.py
-----------
Settings page for Parkinova.

Provides a scrollable, card-based settings panel allowing the user to:
  - Browse and load a new Keras/H5 model.
  - Inspect model information.
  - Manage the local analysis database.
  - Open the reports folder.
  - View application and environment information.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vintage Editorial Palette (Warm Cream, Deep Forest Green, Coral Red)
# ---------------------------------------------------------------------------
BG_COLOR      = "#F5F0D8"   # Warm cream
CARD_COLOR    = "#FFF9E9"   # Warm off-white
NAVY          = "#123F2D"   # Deep forest green
CYAN          = "#F0442E"   # Vibrant coral red
CYAN_HOVER    = "#D43823"
RED           = "#F0442E"   # Coral red
RED_HOVER     = "#D43823"
GRAY_TEXT     = "#365747"   # Muted dark green
BORDER_COLOR  = "#B8C4A5"   # Muted sage green
GREEN         = "#123F2D"
ORANGE        = "#D77B65"   # Soft terracotta

FONT_HEADING  = ("Segoe UI", 22, "bold")
FONT_SUBHEAD  = ("Segoe UI", 13, "bold")
FONT_BODY     = ("Segoe UI", 12)
FONT_SMALL    = ("Segoe UI", 11)
FONT_TINY     = ("Segoe UI", 10)

# Supported image formats (informational — actual validation lives in model.py)
SUPPORTED_FORMATS = ".png, .jpg, .jpeg, .bmp, .tiff"

# Default reports folder (relative to project root)
if getattr(sys, "frozen", False):
    _ROOT_DIR = Path(sys.executable).resolve().parent
else:
    _ROOT_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_REPORTS_DIR = str(_ROOT_DIR / "reports")


# ---------------------------------------------------------------------------
# SettingsFrame
# ---------------------------------------------------------------------------

class SettingsFrame(ctk.CTkFrame):
    """
    Settings page for Parkinova.

    Renders a vertically scrollable collection of grouped setting cards.
    All write actions (model load, db clear, etc.) delegate to the provided
    *app_controller*.

    Parameters
    ----------
    parent : widget
        Parent CTk container.
    app_controller : object
        Application controller exposing:

        * ``reload_model(path: str) -> None``
        * ``model_loaded: bool``
        * ``model_info: dict | None``  – keys: input_shape, output_classes,
          output_type, loaded_at
        * ``db`` – ``AnalysisDatabase`` instance
    """

    def __init__(self, parent, app_controller) -> None:
        super().__init__(parent, fg_color=BG_COLOR, corner_radius=0)
        self.app_controller = app_controller
        initial_path = getattr(self.app_controller, "_model_path", "")
        self._model_path_var   = tk.StringVar(value=initial_path)
        self._spiral_path_var  = tk.StringVar(value="")
        self._status_var       = tk.StringVar(value="")
        self.build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def build_ui(self) -> None:
        """Construct the full layout: header + scrollable card body."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Page header ────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        ctk.CTkLabel(
            header,
            text="Settings",
            font=FONT_HEADING,
            text_color=NAVY,
            anchor="w",
        ).pack(side="left", padx=28, pady=20)

        # ── Scrollable body ────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=BG_COLOR,
            scrollbar_button_color=CYAN,
            scrollbar_button_hover_color=CYAN_HOVER,
            corner_radius=0,
        )
        self._scroll.grid(row=1, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        row = 0
        row = self._build_model_card(row)
        row = self._build_spiral_card(row)
        row = self._build_image_card(row)
        row = self._build_database_card(row)
        row = self._build_reports_card(row)
        row = self._build_account_card(row)
        row = self._build_appinfo_card(row)

        # ── Status bar ─────────────────────────────────────────────────
        status_bar = ctk.CTkFrame(self, fg_color=CARD_COLOR,
                                  corner_radius=0, height=36)
        status_bar.grid(row=2, column=0, sticky="ew")
        status_bar.grid_propagate(False)

        self._status_lbl = ctk.CTkLabel(
            status_bar,
            textvariable=self._status_var,
            font=FONT_TINY,
            text_color=GRAY_TEXT,
            anchor="w",
        )
        self._status_lbl.pack(side="left", padx=28, pady=8)

    # ------------------------------------------------------------------
    # Card builders
    # ------------------------------------------------------------------

    def _build_model_card(self, start_row: int) -> int:
        """Model Configuration card."""
        card, body, row = self._make_card(
            self._scroll, "🧠  Model Configuration", start_row
        )

        # Current model path
        self._add_field_label(body, row, "Current Model Path")
        self._model_path_entry = ctk.CTkEntry(
            body,
            textvariable=self._model_path_var,
            font=FONT_SMALL,
            fg_color="#EAE5CC",
            border_color=BORDER_COLOR,
            text_color=NAVY,
            state="readonly",
            height=34,
        )
        self._model_path_entry.grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=(0, 14), pady=6
        )
        row += 1

        # Browse / Load buttons
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.grid(row=row, column=1, columnspan=2, sticky="w",
                     padx=(0, 14), pady=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="Browse Model…",
            font=FONT_SMALL,
            fg_color="#FFF9E9",
            hover_color="#EAE5CC",
            border_width=1,
            border_color="#123F2D",
            text_color=NAVY,
            corner_radius=8,
            width=140,
            height=34,
            command=self._browse_model,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="Load Model",
            font=FONT_SMALL,
            fg_color=CYAN,
            hover_color=CYAN_HOVER,
            text_color="#FFF9E9",
            corner_radius=8,
            width=120,
            height=34,
            command=self._load_model,
        ).pack(side="left")
        row += 1

        # Status indicator
        self._add_field_label(body, row, "Model Status")
        self._model_status_frame = ctk.CTkFrame(body, fg_color="transparent")
        self._model_status_frame.grid(row=row, column=1, sticky="w",
                                      padx=(0, 14), pady=6)
        self._status_dot = ctk.CTkLabel(
            self._model_status_frame,
            text="●",
            font=("Segoe UI", 14),
            text_color=GRAY_TEXT,
        )
        self._status_dot.pack(side="left", padx=(0, 6))
        self._model_status_lbl = ctk.CTkLabel(
            self._model_status_frame,
            text="Not loaded",
            font=FONT_SMALL,
            text_color=GRAY_TEXT,
        )
        self._model_status_lbl.pack(side="left")
        row += 1

        # Model info fields
        info_fields = [
            ("Input Shape",    "_info_input_shape"),
            ("Output Classes", "_info_output_classes"),
            ("Output Type",    "_info_output_type"),
            ("Loaded At",      "_info_loaded_at"),
        ]
        for label_text, attr in info_fields:
            self._add_field_label(body, row, label_text)
            lbl = ctk.CTkLabel(
                body, text="—",
                font=FONT_SMALL, text_color=GRAY_TEXT, anchor="w"
            )
            lbl.grid(row=row, column=1, sticky="w", padx=(0, 14), pady=4)
            setattr(self, attr, lbl)
            row += 1

        return start_row + 1

    def _build_spiral_card(self, start_row: int) -> int:
        """Spiral Drawing Analysis Model card."""
        card, body, row = self._make_card(
            self._scroll, "🌀  Spiral Model Configuration", start_row
        )

        # Current spiral model path
        self._add_field_label(body, row, "Spiral Model Path")
        self._spiral_path_entry = ctk.CTkEntry(
            body,
            textvariable=self._spiral_path_var,
            font=FONT_SMALL,
            fg_color="#EAE5CC",
            border_color=BORDER_COLOR,
            text_color=NAVY,
            state="readonly",
            height=34,
        )
        self._spiral_path_entry.grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=(0, 14), pady=6
        )
        row += 1

        # Browse / Load buttons
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.grid(row=row, column=1, columnspan=2, sticky="w",
                     padx=(0, 14), pady=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="Browse Model…",
            font=FONT_SMALL,
            fg_color="#FFF9E9",
            hover_color="#EAE5CC",
            border_width=1,
            border_color="#123F2D",
            text_color=NAVY,
            corner_radius=8,
            width=140,
            height=34,
            command=self._browse_spiral_model,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="Load Model",
            font=FONT_SMALL,
            fg_color=CYAN,
            hover_color=CYAN_HOVER,
            text_color="#FFF9E9",
            corner_radius=8,
            width=120,
            height=34,
            command=self._load_spiral_model,
        ).pack(side="left")
        row += 1

        # Status indicator
        self._add_field_label(body, row, "Spiral Status")
        self._spiral_status_frame = ctk.CTkFrame(body, fg_color="transparent")
        self._spiral_status_frame.grid(row=row, column=1, sticky="w", padx=(0, 14), pady=6)
        self._spiral_status_dot = ctk.CTkLabel(
            self._spiral_status_frame,
            text="●",
            font=("Segoe UI", 14),
            text_color=GRAY_TEXT,
        )
        self._spiral_status_dot.pack(side="left", padx=(0, 6))
        self._spiral_status_lbl = ctk.CTkLabel(
            self._spiral_status_frame,
            text="Checking…",
            font=FONT_SMALL,
            text_color=GRAY_TEXT,
        )
        self._spiral_status_lbl.pack(side="left")
        row += 1

        # Spiral model info fields
        sp_fields = [
            ("Input Shape", "_info_sp_input_shape"),
            ("Output Classes", "_info_sp_output_classes"),
            ("Architecture", "_info_sp_arch"),
        ]
        for label_text, attr in sp_fields:
            self._add_field_label(body, row, label_text)
            lbl = ctk.CTkLabel(
                body, text="—",
                font=FONT_SMALL, text_color=GRAY_TEXT, anchor="w"
            )
            lbl.grid(row=row, column=1, sticky="w", padx=(0, 14), pady=4)
            setattr(self, attr, lbl)
            row += 1

        return start_row + 1

    def _build_image_card(self, start_row: int) -> int:
        """Image Settings card."""
        card, body, row = self._make_card(
            self._scroll, "🖼  Image Settings", start_row
        )

        self._add_field_label(body, row, "Supported Formats")
        ctk.CTkLabel(
            body, text=SUPPORTED_FORMATS,
            font=FONT_SMALL, text_color=GRAY_TEXT, anchor="w"
        ).grid(row=row, column=1, sticky="w", padx=(0, 14), pady=6)
        row += 1

        self._add_field_label(body, row, "Expected Dimensions")
        self._img_dims_lbl = ctk.CTkLabel(
            body, text="—",
            font=FONT_SMALL, text_color=GRAY_TEXT, anchor="w"
        )
        self._img_dims_lbl.grid(row=row, column=1, sticky="w",
                                padx=(0, 14), pady=6)

        return start_row + 1

    def _build_database_card(self, start_row: int) -> int:
        """Database card."""
        card, body, row = self._make_card(
            self._scroll, "🗄  Database", start_row
        )

        self._add_field_label(body, row, "DB File Path")
        self._db_path_lbl = ctk.CTkLabel(
            body, text="—",
            font=FONT_SMALL, text_color=GRAY_TEXT, anchor="w", wraplength=420
        )
        self._db_path_lbl.grid(row=row, column=1, sticky="w",
                               padx=(0, 14), pady=6)
        row += 1

        self._add_field_label(body, row, "Actions")
        db_btn_row = ctk.CTkFrame(body, fg_color="transparent")
        db_btn_row.grid(row=row, column=1, columnspan=2, sticky="w",
                        padx=(0, 14), pady=(0, 12))

        ctk.CTkButton(
            db_btn_row,
            text="Open DB Location",
            font=FONT_SMALL,
            fg_color="#FFF9E9",
            hover_color="#EAE5CC",
            border_width=1,
            border_color="#123F2D",
            text_color=NAVY,
            corner_radius=8,
            width=150,
            height=34,
            command=self._open_db_location,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            db_btn_row,
            text="Clear History",
            font=FONT_SMALL,
            fg_color="#FFF9E9",
            hover_color="#FDF0EE",
            border_width=1,
            border_color="#F8C0B8",
            text_color=RED,
            corner_radius=8,
            width=130,
            height=34,
            command=self._confirm_clear_history,
        ).pack(side="left")

        return start_row + 1

    def _build_reports_card(self, start_row: int) -> int:
        """Reports card."""
        card, body, row = self._make_card(
            self._scroll, "📄  Reports", start_row
        )

        self._add_field_label(body, row, "Reports Folder")
        self._reports_path_lbl = ctk.CTkLabel(
            body, text=_DEFAULT_REPORTS_DIR,
            font=FONT_SMALL, text_color=GRAY_TEXT, anchor="w", wraplength=420
        )
        self._reports_path_lbl.grid(row=row, column=1, sticky="w",
                                    padx=(0, 14), pady=6)
        row += 1

        self._add_field_label(body, row, "")
        ctk.CTkButton(
            body,
            text="Open Reports Folder",
            font=FONT_SMALL,
            fg_color="#FFF9E9",
            hover_color="#EAE5CC",
            border_width=1,
            border_color="#123F2D",
            text_color=NAVY,
            corner_radius=8,
            width=170,
            height=34,
            command=self._open_reports_folder,
        ).grid(row=row, column=1, sticky="w", padx=(0, 14), pady=(0, 12))

        return start_row + 1

    def _build_account_card(self, start_row: int) -> int:
        """Account & Security card."""
        card, body, row = self._make_card(
            self._scroll, "👤  Account & Security", start_row
        )

        user = getattr(self.app_controller, "logged_in_user", "admin") or "admin"
        display = getattr(self.app_controller, "logged_in_display", "Administrator") or "Administrator"

        self._add_field_label(body, row, "Current User")
        ctk.CTkLabel(
            body,
            text=f"{display} ({user})",
            font=FONT_SMALL,
            text_color=NAVY,
            anchor="w",
        ).grid(row=row, column=1, sticky="w", padx=(0, 14), pady=6)
        row += 1

        self._add_field_label(body, row, "Actions")
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.grid(row=row, column=1, columnspan=2, sticky="w", padx=(0, 14), pady=(0, 12))

        ctk.CTkButton(
            btn_row,
            text="Change Password",
            font=FONT_SMALL,
            fg_color="#FFF9E9",
            hover_color="#EAE5CC",
            border_width=1,
            border_color="#123F2D",
            text_color=NAVY,
            corner_radius=8,
            width=140,
            height=34,
            command=self._show_change_password_dialog,
        ).pack(side="left", padx=(0, 8))

        if user == "admin" or "@" in user:
            ctk.CTkButton(
                btn_row,
                text="Add Researcher",
                font=FONT_SMALL,
                fg_color=CYAN,
                hover_color=CYAN_HOVER,
                text_color="#FFF9E9",
                corner_radius=8,
                width=130,
                height=34,
                command=self._show_add_user_dialog,
            ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="🚪  Sign Out",
            font=FONT_SMALL,
            fg_color="#FFF9E9",
            hover_color="#FDF0EE",
            border_width=1,
            border_color="#F8C0B8",
            text_color=RED,
            corner_radius=8,
            width=110,
            height=34,
            command=self._on_logout,
        ).pack(side="left")

        return start_row + 1

    def _on_logout(self) -> None:
        """Handle logout action."""
        if messagebox.askyesno("Sign Out", "Are you sure you want to end your current session and sign out?"):
            if hasattr(self.app_controller, "logout"):
                self.app_controller.logout()

    def _show_change_password_dialog(self) -> None:
        """Modal dialog to change the current user's password."""
        from app.auth import auth_service

        dialog = ctk.CTkToplevel(self)
        dialog.title("Change Password")
        dialog.geometry("400x340")
        dialog.resizable(False, False)
        dialog.configure(fg_color=BG_COLOR)
        dialog.grab_set()
        dialog.lift()

        ctk.CTkLabel(dialog, text="Change Password", font=FONT_SUBHEAD, text_color=NAVY).pack(pady=(20, 10))

        user = getattr(self.app_controller, "logged_in_user", "admin") or "admin"

        old_var = tk.StringVar()
        new_var = tk.StringVar()
        confirm_var = tk.StringVar()

        frame = ctk.CTkFrame(dialog, fg_color=CARD_COLOR, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        frame.pack(fill="x", padx=24, pady=10)

        ctk.CTkLabel(frame, text="Current Password", font=FONT_TINY, text_color=GRAY_TEXT).pack(anchor="w", padx=16, pady=(10, 2))
        ctk.CTkEntry(frame, textvariable=old_var, show="•", height=32).pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(frame, text="New Password (min 8 chars)", font=FONT_TINY, text_color=GRAY_TEXT).pack(anchor="w", padx=16, pady=(4, 2))
        ctk.CTkEntry(frame, textvariable=new_var, show="•", height=32).pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(frame, text="Confirm New Password", font=FONT_TINY, text_color=GRAY_TEXT).pack(anchor="w", padx=16, pady=(4, 2))
        ctk.CTkEntry(frame, textvariable=confirm_var, show="•", height=32).pack(fill="x", padx=16, pady=(0, 12))

        def submit():
            old = old_var.get().strip()
            new = new_var.get().strip()
            conf = confirm_var.get().strip()
            if not old or not new:
                messagebox.showerror("Error", "Please fill in all fields.", parent=dialog)
                return
            if new != conf:
                messagebox.showerror("Error", "New passwords do not match.", parent=dialog)
                return
            ok, msg = auth_service.change_password(user, old, new)
            if ok:
                messagebox.showinfo("Success", msg, parent=dialog)
                dialog.destroy()
                self._set_status(msg, GREEN)
            else:
                messagebox.showerror("Error", msg, parent=dialog)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=12)
        ctk.CTkButton(btn_row, text="Update Password", fg_color=CYAN, hover_color=CYAN_HOVER, text_color="#FFF9E9", width=140, height=34, command=submit).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="Cancel", fg_color="#FFF9E9", border_width=1, border_color="#123F2D", text_color=NAVY, hover_color="#EAE5CC", width=80, height=34, command=dialog.destroy).pack(side="left", padx=6)

    def _show_add_user_dialog(self) -> None:
        """Modal dialog for admin to register a new user."""
        from app.auth import auth_service

        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Researcher Account")
        dialog.geometry("400x340")
        dialog.resizable(False, False)
        dialog.configure(fg_color=BG_COLOR)
        dialog.grab_set()
        dialog.lift()

        ctk.CTkLabel(dialog, text="Add Researcher Account", font=FONT_SUBHEAD, text_color=NAVY).pack(pady=(20, 10))

        u_var = tk.StringVar()
        d_var = tk.StringVar()
        p_var = tk.StringVar()

        frame = ctk.CTkFrame(dialog, fg_color=CARD_COLOR, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        frame.pack(fill="x", padx=24, pady=10)

        ctk.CTkLabel(frame, text="Email Address (e.g. user@gmail.com)", font=FONT_TINY, text_color=GRAY_TEXT).pack(anchor="w", padx=16, pady=(10, 2))
        ctk.CTkEntry(frame, textvariable=u_var, height=32).pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(frame, text="Display Name (e.g. Dr. Jane Smith)", font=FONT_TINY, text_color=GRAY_TEXT).pack(anchor="w", padx=16, pady=(4, 2))
        ctk.CTkEntry(frame, textvariable=d_var, height=32).pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(frame, text="Password (min 8 chars)", font=FONT_TINY, text_color=GRAY_TEXT).pack(anchor="w", padx=16, pady=(4, 2))
        ctk.CTkEntry(frame, textvariable=p_var, show="•", height=32).pack(fill="x", padx=16, pady=(0, 12))

        def submit():
            u = u_var.get().strip()
            d = d_var.get().strip()
            p = p_var.get().strip()
            if not u or not p:
                messagebox.showerror("Error", "Email and password are required.", parent=dialog)
                return
            if len(p) < 8:
                messagebox.showerror("Error", "Password must be at least 8 characters.", parent=dialog)
                return
            ok, msg = auth_service.add_user(u, p, d)
            if ok:
                messagebox.showinfo("Success", msg, parent=dialog)
                dialog.destroy()
                self._set_status(msg, GREEN)
            else:
                messagebox.showerror("Error", msg, parent=dialog)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=12)
        ctk.CTkButton(btn_row, text="Add User", fg_color=CYAN, hover_color=CYAN_HOVER, text_color="#FFF9E9", width=120, height=34, command=submit).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="Cancel", fg_color="#FFF9E9", border_width=1, border_color="#123F2D", text_color=NAVY, hover_color="#EAE5CC", width=80, height=34, command=dialog.destroy).pack(side="left", padx=6)

    def _build_appinfo_card(self, start_row: int) -> int:
        """Application Info card."""
        card, body, row = self._make_card(
            self._scroll, "ℹ  Application Info", start_row
        )

        # Safely attempt TF version retrieval
        tf_version = _get_tf_version()

        info_rows = [
            ("App Name",       "Parkinova"),
            ("Version",        "1.0.0"),
            ("Description",    "Academic Research Prototype"),
            ("Python Version", platform.python_version()),
            ("Platform",       platform.system() + " " + platform.release()),
            ("TensorFlow",     tf_version),
        ]

        for label_text, value in info_rows:
            self._add_field_label(body, row, label_text)
            ctk.CTkLabel(
                body, text=value,
                font=FONT_SMALL, text_color=GRAY_TEXT, anchor="w"
            ).grid(row=row, column=1, sticky="w", padx=(0, 14), pady=4)
            row += 1

        return start_row + 1

    # ------------------------------------------------------------------
    # Card factory helper
    # ------------------------------------------------------------------

    def _make_card(
        self, parent, title: str, grid_row: int
    ) -> tuple[ctk.CTkFrame, ctk.CTkFrame, int]:
        """
        Create a labeled card frame inside *parent*.

        Returns
        -------
        tuple
            (card_outer_frame, body_frame, body_start_row)
        """
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_COLOR,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.grid(row=grid_row, column=0, sticky="ew", padx=24, pady=10)
        card.grid_columnconfigure(0, weight=1)

        # Card title
        ctk.CTkLabel(
            card, text=title,
            font=FONT_SUBHEAD, text_color=NAVY, anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))

        ctk.CTkFrame(card, fg_color=BORDER_COLOR, height=1).grid(
            row=1, column=0, sticky="ew", padx=18, pady=(0, 8)
        )

        # Body frame with two-column grid (label | value)
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        body.grid_columnconfigure(1, weight=1)

        return card, body, 0

    @staticmethod
    def _add_field_label(parent, row: int, text: str) -> ctk.CTkLabel:
        """Render a right-aligned field label in the left column."""
        lbl = ctk.CTkLabel(
            parent, text=text,
            font=("Segoe UI", 10, "bold"),
            text_color=GRAY_TEXT,
            anchor="e",
            width=140,
        )
        lbl.grid(row=row, column=0, sticky="e", padx=(0, 14), pady=4)
        return lbl

    # ------------------------------------------------------------------
    # Refresh / update displayed values
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """
        Re-read live state from ``app_controller`` and update all
        displayed values.  Safe to call at any time.
        """
        # ── Model status ───────────────────────────────────────────────
        model_loaded: bool = getattr(self.app_controller, "model_loaded", False)
        is_loading: bool = getattr(self.app_controller, "is_loading_model", False)
        model_info: dict | None = getattr(self.app_controller, "model_info", None)

        if model_loaded and model_info:
            dot_color  = GREEN
            status_txt = "Loaded ✓"
            status_clr = GREEN

            current_path = model_info.get("model_path", "")
            if current_path:
                self._model_path_var.set(current_path)

            input_shape = str(model_info.get("input_shape", "—"))
            self._info_input_shape.configure(text=input_shape, text_color=NAVY)

            out_classes = str(model_info.get("num_classes", model_info.get("output_classes", "—")))
            self._info_output_classes.configure(text=out_classes, text_color=NAVY)

            out_type = str(model_info.get("output_type", "—"))
            self._info_output_type.configure(text=out_type, text_color=NAVY)

            loaded_at = str(model_info.get("loaded_at", "—"))
            if loaded_at != "—" and "T" in loaded_at:
                loaded_at = loaded_at.split(".")[0].replace("T", " ") + " UTC"
            self._info_loaded_at.configure(text=loaded_at, text_color=NAVY)

            # Image expected dims from model info
            dims_str = _shape_to_dims(model_info.get("input_shape"))
            self._img_dims_lbl.configure(text=dims_str, text_color=NAVY)
        elif is_loading:
            dot_color  = ORANGE
            status_txt = "Loading model…"
            status_clr = ORANGE
            for attr in ("_info_input_shape", "_info_output_classes",
                         "_info_output_type", "_info_loaded_at"):
                getattr(self, attr).configure(text="—", text_color=GRAY_TEXT)
            self._img_dims_lbl.configure(text="—", text_color=GRAY_TEXT)
        else:
            dot_color  = GRAY_TEXT
            status_txt = "Not loaded"
            status_clr = GRAY_TEXT
            for attr in ("_info_input_shape", "_info_output_classes",
                         "_info_output_type", "_info_loaded_at"):
                getattr(self, attr).configure(text="—", text_color=GRAY_TEXT)
            self._img_dims_lbl.configure(text="—", text_color=GRAY_TEXT)

        self._status_dot.configure(text_color=dot_color)
        self._model_status_lbl.configure(text=status_txt, text_color=status_clr)

        # ── Spiral model status ────────────────────────────────────────
        try:
            from app.spiral_analysis import spiral_engine, CANDIDATE_SPIRAL_MODELS
            sp_path = spiral_engine.model_path or (CANDIDATE_SPIRAL_MODELS[0] if CANDIDATE_SPIRAL_MODELS else "")
            self._spiral_path_var.set(sp_path if sp_path else "Interface Standby")

            if spiral_engine.model_loaded and spiral_engine.model_info:
                self._spiral_status_dot.configure(text_color=GREEN)
                self._spiral_status_lbl.configure(text="Loaded ✓", text_color=GREEN)
                self._info_sp_input_shape.configure(
                    text=_shape_to_dims(spiral_engine.model_info.get("input_shape")),
                    text_color=NAVY,
                )
                self._info_sp_output_classes.configure(
                    text=str(spiral_engine.model_info.get("num_classes", 2)),
                    text_color=NAVY,
                )
                arch_name = "YOLO Classifier" if spiral_engine.model_info.get("is_yolo") else "Archimedean Spiral CNN"
                dims = _shape_to_dims(spiral_engine.model_info.get("input_shape"))
                self._info_sp_arch.configure(
                    text=f"{arch_name} ({dims})",
                    text_color=NAVY,
                )
            elif getattr(spiral_engine, "load_error", None):
                self._spiral_status_dot.configure(text_color=RED)
                err_text = str(spiral_engine.load_error)
                lbl_text = "Error: " + (err_text[:35] + "…" if len(err_text) > 35 else err_text)
                self._spiral_status_lbl.configure(text=lbl_text, text_color=RED)
                self._info_sp_input_shape.configure(text="—", text_color=GRAY_TEXT)
                self._info_sp_output_classes.configure(text="—", text_color=GRAY_TEXT)
                self._info_sp_arch.configure(text=err_text[:50], text_color=RED)
            else:
                self._spiral_status_dot.configure(text_color=ORANGE)
                self._spiral_status_lbl.configure(text="Standby", text_color=ORANGE)
                self._info_sp_input_shape.configure(text="—", text_color=GRAY_TEXT)
                self._info_sp_output_classes.configure(text="—", text_color=GRAY_TEXT)
                self._info_sp_arch.configure(text="—", text_color=GRAY_TEXT)
        except Exception as exc:
            logger.warning("Could not refresh spiral settings card: %s", exc)

        # ── Database path ──────────────────────────────────────────────
        try:
            db_path = self.app_controller.db.get_db_path()
            self._db_path_lbl.configure(text=db_path, text_color=NAVY)
        except Exception:  # noqa: BLE001
            self._db_path_lbl.configure(text="Unavailable", text_color=GRAY_TEXT)

    # ------------------------------------------------------------------
    # Action callbacks
    # ------------------------------------------------------------------

    def _browse_model(self) -> None:
        """Open a file dialog to select a Keras / H5 model file."""
        path = filedialog.askopenfilename(
            title="Select Model File",
            filetypes=[
                ("Neural Network models", "*.keras;*.h5;*.tflite"),
                ("Keras models", "*.keras;*.h5"),
                ("TFLite models", "*.tflite"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._model_path_var.set(path)
            self._set_status(f"Model path set: {os.path.basename(path)}", CYAN)

    def _load_model(self) -> None:
        """Validate the selected path and ask ``app_controller`` to load it."""
        path = self._model_path_var.get().strip()
        if not path:
            self._set_status("No model path selected. Use 'Browse Model…' first.", ORANGE)
            return
        if not os.path.isfile(path):
            self._set_status(f"File not found: {path}", RED)
            return
        if not path.lower().endswith((".keras", ".h5", ".tflite")):
            self._set_status("Unsupported file type. Please select a .keras, .h5, or .tflite file.", ORANGE)
            return

        self._set_status("Loading model in background… please wait.", CYAN)
        self._status_dot.configure(text_color=ORANGE)
        self._model_status_lbl.configure(text="Loading model…", text_color=ORANGE)
        try:
            self.app_controller.reload_model(path)
            self.after(1500, self.refresh)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load model '%s': %s", path, exc)
            self._set_status(f"Error loading model: {exc}", RED)
            self._status_dot.configure(text_color=GRAY_TEXT)
            self._model_status_lbl.configure(text="Not loaded", text_color=GRAY_TEXT)

    def _browse_spiral_model(self) -> None:
        """Open a file dialog to select a spiral model file (.pt, .keras, .h5, etc)."""
        path = filedialog.askopenfilename(
            title="Select Spiral Model File",
            filetypes=[
                ("Neural Network models", "*.pt;*.keras;*.h5;*.tflite;*.onnx"),
                ("PyTorch / YOLO models", "*.pt"),
                ("Keras models", "*.keras;*.h5"),
                ("TFLite models", "*.tflite"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._spiral_path_var.set(path)
            self._set_status(f"Spiral model selected: {os.path.basename(path)}", CYAN)

    def _load_spiral_model(self) -> None:
        """Validate the selected spiral model path and load it."""
        path = self._spiral_path_var.get().strip()
        if not path or path == "Interface Standby":
            self._set_status("No spiral model path selected. Use 'Browse Model…' first.", ORANGE)
            return
        if not os.path.isfile(path):
            self._set_status(f"File not found: {path}", RED)
            return

        self._set_status("Loading spiral model in background… please wait.", CYAN)
        self._spiral_status_dot.configure(text_color=ORANGE)
        self._spiral_status_lbl.configure(text="Loading model…", text_color=ORANGE)
        try:
            from app.spiral_analysis import spiral_engine
            spiral_engine.reload_model(path)
            self.after(1200, self.refresh)
        except Exception as exc:
            logger.error("Failed to load spiral model '%s': %s", path, exc)
            self._set_status(f"Error loading spiral model: {exc}", RED)
            self._spiral_status_dot.configure(text_color=GRAY_TEXT)
            self._spiral_status_lbl.configure(text="Not loaded", text_color=GRAY_TEXT)

    def _open_db_location(self) -> None:
        """Open the directory containing the database file in File Explorer."""
        try:
            db_path = self.app_controller.db.get_db_path()
            folder = os.path.dirname(db_path)
            _open_folder(folder)
            self._set_status(f"Opened: {folder}", CYAN)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to open DB location: %s", exc)
            self._set_status(f"Error opening DB location: {exc}", RED)

    def _confirm_clear_history(self) -> None:
        """Confirm before clearing all database records."""
        confirmed = messagebox.askyesno(
            title="Clear All History",
            message=(
                "Are you sure you want to delete ALL analysis records?\n\n"
                "This action cannot be undone."
            ),
            icon="warning",
        )
        if confirmed:
            try:
                count = self.app_controller.db.clear_all_history()
                self._set_status(f"History cleared — {count} record(s) deleted.", GREEN)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error clearing history: %s", exc)
                self._set_status(f"Error clearing history: {exc}", RED)

    def _open_reports_folder(self) -> None:
        """Open the default reports folder in File Explorer."""
        folder = _DEFAULT_REPORTS_DIR
        os.makedirs(folder, exist_ok=True)
        try:
            _open_folder(folder)
            self._set_status(f"Opened: {folder}", CYAN)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to open reports folder: %s", exc)
            self._set_status(f"Error opening reports folder: {exc}", RED)

    # ------------------------------------------------------------------
    # Status bar helper
    # ------------------------------------------------------------------

    def _set_status(self, message: str, color: str = GRAY_TEXT) -> None:
        """Update the status bar label and auto-clear after 6 seconds."""
        self._status_var.set(message)
        self._status_lbl.configure(text_color=color)
        self.after(6000, lambda: self._status_var.set(""))


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _open_folder(folder: str) -> None:
    """
    Open *folder* in the platform's native file manager.

    Parameters
    ----------
    folder : str
        Absolute path of the directory to reveal.

    Raises
    ------
    OSError
        If the platform command fails.
    """
    folder = os.path.normpath(folder)
    system = platform.system()
    if system == "Windows":
        os.startfile(folder)  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", folder])
    else:
        subprocess.Popen(["xdg-open", folder])


def _get_tf_version() -> str:
    """
    Attempt to import TensorFlow and return its version string.

    Returns
    -------
    str
        Version string (e.g. ``"2.16.1"``) or a human-readable message
        when TensorFlow is not installed or cannot be imported.
    """
    try:
        import tensorflow as tf  # noqa: PLC0415
        return tf.__version__
    except ImportError:
        return "Not installed"
    except Exception as exc:  # noqa: BLE001
        return f"Error ({exc})"


def _shape_to_dims(input_shape) -> str:
    """
    Convert a model input-shape value to a human-readable dimensions string.

    Parameters
    ----------
    input_shape : tuple | list | str | None
        The raw input shape from model_info.

    Returns
    -------
    str
        E.g. ``"224 × 224 × 3"`` or ``"—"`` when not available.
    """
    if input_shape is None:
        return "—"
    try:
        if isinstance(input_shape, (list, tuple)):
            # Drop batch dim (first element) if it is None
            dims = [d for d in input_shape if d is not None]
            return " × ".join(str(d) for d in dims)
        return str(input_shape)
    except Exception:  # noqa: BLE001
        return str(input_shape)
