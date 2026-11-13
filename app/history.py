"""
history.py
----------
Local Analysis History screen for Parkinova.

Displays a scrollable list of past MRI analyses stored in the local SQLite
database, with options to view full record details, delete individual records,
or clear the entire history.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vintage Editorial Palette (Warm Cream, Deep Forest Green, Coral Red)
# ---------------------------------------------------------------------------
BG_COLOR       = "#F5F0D8"   # Warm cream
CARD_COLOR     = "#FFF9E9"   # Warm off-white
NAVY           = "#123F2D"   # Deep forest green
CYAN           = "#F0442E"   # Vibrant coral red
CYAN_HOVER     = "#D43823"
RED            = "#F0442E"   # Coral red
RED_HOVER      = "#D43823"
GRAY_TEXT      = "#365747"   # Muted dark green
BORDER_COLOR   = "#B8C4A5"   # Muted sage green
GREEN          = "#123F2D"
FONT_HEADING   = ("Segoe UI", 22, "bold")
FONT_SUBHEAD   = ("Segoe UI", 13, "bold")
FONT_BODY      = ("Segoe UI", 12)
FONT_SMALL     = ("Segoe UI", 11)
FONT_TINY      = ("Segoe UI", 10)


# ---------------------------------------------------------------------------
# HistoryFrame
# ---------------------------------------------------------------------------

class HistoryFrame(ctk.CTkFrame):
    """
    Analysis History screen.

    Renders a scrollable list of all MRI analysis records persisted in the
    local SQLite database.  Each record card shows a summary row with buttons
    to view full details or delete the record.

    Parameters
    ----------
    parent : widget
        Parent CTk container.
    app_controller : object
        Application controller.  Must expose a ``db`` attribute that is an
        ``AnalysisDatabase`` instance.
    """

    def __init__(self, parent, app_controller) -> None:
        super().__init__(parent, fg_color=BG_COLOR, corner_radius=0)
        self.app_controller = app_controller
        self._record_rows: list[dict] = []   # cache of rendered rows
        self.build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def build_ui(self) -> None:
        """Construct the full layout: header, list area, and footer."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────────
        self._header_frame = ctk.CTkFrame(self, fg_color=CARD_COLOR,
                                          corner_radius=0)
        self._header_frame.grid(row=0, column=0, sticky="ew",
                                padx=0, pady=(0, 2))
        self._header_frame.grid_columnconfigure(1, weight=1)

        self._title_label = ctk.CTkLabel(
            self._header_frame,
            text="Analysis History",
            font=FONT_HEADING,
            text_color=NAVY,
            anchor="w",
        )
        self._title_label.grid(row=0, column=0, padx=28, pady=20, sticky="w")

        # Header action buttons (right-aligned)
        btn_frame = ctk.CTkFrame(self._header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=20, pady=12, sticky="e")

        self._refresh_btn = ctk.CTkButton(
            btn_frame,
            text="⟳  Refresh",
            font=FONT_SMALL,
            fg_color=CYAN,
            hover_color=CYAN_HOVER,
            text_color="#FFF9E9",
            corner_radius=8,
            width=110,
            height=34,
            command=self.refresh,
        )
        self._refresh_btn.pack(side="left", padx=(0, 10))

        self._clear_btn = ctk.CTkButton(
            btn_frame,
            text="🗑  Clear All",
            font=FONT_SMALL,
            fg_color="#FFF9E9",
            hover_color="#FDF0EE",
            border_width=1,
            border_color="#F8C0B8",
            text_color=RED,
            corner_radius=8,
            width=130,
            height=34,
            command=self._confirm_clear_all,
        )
        self._clear_btn.pack(side="left")

        # ── Scrollable list area ───────────────────────────────────────
        self._list_container = ctk.CTkScrollableFrame(
            self,
            fg_color=BG_COLOR,
            scrollbar_button_color=CYAN,
            scrollbar_button_hover_color=CYAN_HOVER,
            corner_radius=0,
        )
        self._list_container.grid(row=1, column=0, sticky="nsew",
                                  padx=0, pady=0)
        self._list_container.grid_columnconfigure(0, weight=1)

        # Placeholder for empty state (shown conditionally)
        self._empty_label = ctk.CTkLabel(
            self._list_container,
            text="No analysis history yet.\nRun your first MRI analysis to see records here.",
            font=("Segoe UI", 13),
            text_color=GRAY_TEXT,
            justify="center",
        )

        # ── Footer / stats bar ─────────────────────────────────────────
        self._footer_frame = ctk.CTkFrame(self, fg_color=CARD_COLOR,
                                          corner_radius=0, height=38)
        self._footer_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        self._footer_frame.grid_propagate(False)

        self._stats_label = ctk.CTkLabel(
            self._footer_frame,
            text="Total records: 0",
            font=FONT_TINY,
            text_color=GRAY_TEXT,
            anchor="w",
        )
        self._stats_label.pack(side="left", padx=28, pady=8)

        # Status bar (inline feedback)
        self._status_label = ctk.CTkLabel(
            self._footer_frame,
            text="",
            font=FONT_TINY,
            text_color=GRAY_TEXT,
            anchor="e",
        )
        self._status_label.pack(side="right", padx=28, pady=8)

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """
        Reload analysis records from the database and re-render the list.

        Wraps all database access in try/except and surfaces errors in the
        status bar rather than crashing.
        """
        self._set_status("Loading…", GRAY_TEXT)
        db = getattr(self.app_controller, "db", None)
        if db is None:
            self._stats_label.configure(text="Total records: 0")
            self._set_status("Database not available", GRAY_TEXT)
            self._render_list([])
            return
        try:
            records: list[dict] = db.get_all_analyses(limit=200)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load history: %s", exc)
            self._set_status(f"Error loading history: {exc}", RED)
            return

        self._render_list(records)
        count = len(records)
        self._stats_label.configure(text=f"Total records: {count}")
        self._set_status(f"Loaded {count} record(s).", GREEN)

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_list(self, records: list[dict]) -> None:
        """Clear and re-populate the scrollable list with *records*."""
        # Remove existing widgets
        for widget in self._list_container.winfo_children():
            widget.destroy()
        self._record_rows.clear()

        if not records:
            self._empty_label = ctk.CTkLabel(
                self._list_container,
                text="No analysis history yet.\nRun your first MRI analysis to see records here.",
                font=("Segoe UI", 13),
                text_color=GRAY_TEXT,
                justify="center",
            )
            self._empty_label.grid(row=0, column=0, pady=60)
            return

        # Column header row
        self._build_column_headers()

        # Record cards
        for idx, record in enumerate(records):
            self._build_record_row(record, idx)

    def _build_column_headers(self) -> None:
        """Render a subtle column-header strip above the record cards."""
        hdr = ctk.CTkFrame(self._list_container, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(12, 4))
        hdr.grid_columnconfigure((0, 1, 2, 3), weight=1)

        labels = ["Analysis ID", "Timestamp", "Prediction", "Image File"]
        for col, text in enumerate(labels):
            ctk.CTkLabel(
                hdr, text=text, font=("Segoe UI", 10, "bold"),
                text_color=GRAY_TEXT, anchor="w"
            ).grid(row=0, column=col, sticky="w", padx=6)

    def _build_record_row(self, record: dict, idx: int) -> None:
        """
        Render a single history record as a card row.

        Parameters
        ----------
        record : dict
            A record dict from ``AnalysisDatabase.get_all_analyses()``.
        idx : int
            Zero-based row index (used for alternating shading).
        """
        row_bg = CARD_COLOR if idx % 2 == 0 else "#EAE5CC"

        card = ctk.CTkFrame(
            self._list_container,
            fg_color=row_bg,
            corner_radius=10,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.grid(row=idx + 1, column=0, sticky="ew", padx=20, pady=4)
        card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # ── Summary fields ──────────────────────────────────────────
        analysis_id    = str(record.get("id", ""))
        short_id       = analysis_id[:8] + "…" if len(analysis_id) > 8 else analysis_id
        timestamp_raw  = record.get("created_at", "")
        timestamp_disp = _fmt_timestamp(timestamp_raw)
        prediction     = record.get("predicted_class", "Unknown")
        filename       = record.get("image_filename", "—")
        if filename and len(filename) > 28:
            filename = "…" + filename[-25:]

        fields = [short_id, timestamp_disp, prediction, filename]
        pred_colors = {
            "Parkinson's": "#FDF0EE",
            "Healthy":     "#EAE5CC",
        }
        pred_text_colors = {
            "Parkinson's": "#F0442E",
            "Healthy":     "#123F2D",
        }

        for col, text in enumerate(fields):
            if col == 2:  # Prediction — badge style
                badge_bg   = pred_colors.get(prediction, "#EAE5CC")
                badge_fg   = pred_text_colors.get(prediction, NAVY)
                badge = ctk.CTkLabel(
                    card, text=text, font=("Segoe UI", 11, "bold"),
                    text_color=badge_fg, fg_color=badge_bg,
                    corner_radius=6, padx=8, pady=2,
                )
                badge.grid(row=0, column=col, sticky="w", padx=8, pady=10)
            else:
                ctk.CTkLabel(
                    card, text=text, font=FONT_SMALL,
                    text_color=NAVY if col == 0 else GRAY_TEXT, anchor="w",
                ).grid(row=0, column=col, sticky="w", padx=8, pady=10)

        # ── Action buttons ──────────────────────────────────────────
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=0, column=4, padx=12, pady=6, sticky="e")

        ctk.CTkButton(
            btn_frame,
            text="View Details",
            font=("Segoe UI", 10, "bold"),
            fg_color=CYAN,
            hover_color=CYAN_HOVER,
            text_color="#FFF9E9",
            corner_radius=6,
            width=90,
            height=28,
            command=lambda r=record: self.show_detail_popup(r),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame,
            text="Delete",
            font=("Segoe UI", 10),
            fg_color="#FFF9E9",
            hover_color="#FDF0EE",
            border_width=1,
            border_color="#F8C0B8",
            text_color=RED,
            corner_radius=6,
            width=60,
            height=28,
            command=lambda rid=analysis_id: self._confirm_delete(rid),
        ).pack(side="left")

        self._record_rows.append({"id": analysis_id, "card": card})

    # ------------------------------------------------------------------
    # Detail popup
    # ------------------------------------------------------------------

    def show_detail_popup(self, record: dict) -> None:
        """
        Open a CTkToplevel window showing all fields of *record* in a
        clean, read-only layout.

        Parameters
        ----------
        record : dict
            Full record dict from the database.
        """
        popup = ctk.CTkToplevel(self)
        popup.title("Analysis Detail")
        popup.geometry("560x580")
        popup.resizable(False, True)
        popup.configure(fg_color=BG_COLOR)
        popup.grab_set()   # modal
        popup.lift()
        popup.focus_force()

        # Title
        ctk.CTkLabel(
            popup, text="Analysis Details",
            font=("Segoe UI", 18, "bold"), text_color=NAVY
        ).pack(anchor="w", padx=28, pady=(22, 4))

        ctk.CTkFrame(popup, fg_color=CYAN, height=2).pack(
            fill="x", padx=28, pady=(0, 14)
        )

        # Scrollable body
        body = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=0)

        import json  # lazy import — only needed in popup

        field_meta = [
            ("Analysis ID",      "id"),
            ("Patient Code",     "patient_code"),
            ("Image Filename",   "image_filename"),
            ("Image Path",       "image_path"),
            ("Model Prediction", "predicted_class"),
            ("Model Architecture", "model_name"),
            ("Model Version",    "model_version"),
            ("Input Shape",      "input_shape"),
            ("Evaluation Date",  "created_at"),
            ("Researcher",       "logged_in_user"),
            ("Preprocessing",    "preprocessing_info"),
        ]

        for display_name, key in field_meta:
            value = record.get(key, "—")
            if value is None:
                value = "—"
            if isinstance(value, dict):
                value = json.dumps(value, indent=2)
            elif not isinstance(value, str):
                value = str(value)

            row_frame = ctk.CTkFrame(body, fg_color=CARD_COLOR,
                                     corner_radius=8,
                                     border_width=1,
                                     border_color=BORDER_COLOR)
            row_frame.pack(fill="x", pady=4, padx=4)

            ctk.CTkLabel(
                row_frame, text=display_name,
                font=("Segoe UI", 10, "bold"),
                text_color=GRAY_TEXT, anchor="w", width=130,
            ).grid(row=0, column=0, sticky="nw", padx=12, pady=8)

            ctk.CTkLabel(
                row_frame, text=value,
                font=("Segoe UI", 11),
                text_color=NAVY, anchor="w",
                justify="left", wraplength=340,
            ).grid(row=0, column=1, sticky="w", padx=8, pady=8)

        # Patient Assessment card (if available)
        patient_data = record.get("patient_data")
        if patient_data and isinstance(patient_data, dict):
            p_frame = ctk.CTkFrame(body, fg_color=CARD_COLOR, corner_radius=8,
                                   border_width=1, border_color=BORDER_COLOR)
            p_frame.pack(fill="x", pady=4, padx=4)
            ctk.CTkLabel(
                p_frame, text="Patient Assessment",
                font=("Segoe UI", 10, "bold"),
                text_color=GRAY_TEXT, anchor="w", width=130,
            ).grid(row=0, column=0, sticky="nw", padx=12, pady=8)

            p_summary = (
                f"Age: {patient_data.get('age', '—')}  ·  "
                f"Gender: {patient_data.get('gender', '—')}\n"
                f"Questions Answered: {patient_data.get('answered_questions', 0)} / "
                f"{patient_data.get('total_questions', 0)}"
            )
            ctk.CTkLabel(
                p_frame, text=p_summary,
                font=("Segoe UI", 11),
                text_color=NAVY, anchor="w", justify="left", wraplength=340,
            ).grid(row=0, column=1, sticky="w", padx=8, pady=8)

        # Bottom action buttons (Export PDF + Close)
        btn_bar = ctk.CTkFrame(popup, fg_color="transparent")
        btn_bar.pack(pady=16)

        ctk.CTkButton(
            btn_bar,
            text="📄  Export PDF",
            fg_color=CYAN,
            hover_color=CYAN_HOVER,
            text_color="#FFF9E9",
            corner_radius=8,
            width=120,
            height=34,
            command=lambda: self._export_history_report(record),
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_bar,
            text="Close",
            fg_color="#FFF9E9",
            hover_color="#EAE5CC",
            border_width=1,
            border_color="#123F2D",
            text_color=NAVY,
            corner_radius=8,
            width=100,
            height=34,
            command=popup.destroy,
        ).pack(side="left")

    def _export_history_report(self, record: dict) -> None:
        """Export a PDF report from a history record."""
        if not hasattr(self.app_controller, "generate_report"):
            messagebox.showwarning("Unavailable", "PDF export is not available.")
            return

        result = {
            "predicted_class": record.get("predicted_class", ""),
            "model_scores": record.get("model_scores", {}),
            "model_name": record.get("model_name", "parkinson_cnn"),
            "model_version": record.get("model_version", "1.0.0"),
            "input_shape": record.get("input_shape", ""),
            "preprocessing_info": record.get("preprocessing_info", {}),
            "image_path": record.get("image_path", ""),
        }
        self.app_controller.generate_report(
            result=result,
            analysis_id=str(record.get("id", "")),
            patient_code=str(record.get("patient_code", "")),
            patient_data=record.get("patient_data"),
        )

    # ------------------------------------------------------------------
    # Deletion helpers
    # ------------------------------------------------------------------

    def _confirm_delete(self, analysis_id: str) -> None:
        """Ask the user to confirm deletion of one record."""
        confirmed = messagebox.askyesno(
            title="Confirm Delete",
            message=(
                f"Delete analysis record\n{analysis_id[:8]}…?\n\n"
                "This action cannot be undone."
            ),
            icon="warning",
        )
        if confirmed:
            self._delete_record(analysis_id)

    def _delete_record(self, analysis_id: str) -> None:
        """Delete a single record and refresh the list."""
        try:
            deleted = self.app_controller.db.delete_analysis(analysis_id)
            if deleted:
                self._set_status("Record deleted successfully.", GREEN)
            else:
                self._set_status("Record not found — may have been already deleted.", GRAY_TEXT)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error deleting record %s: %s", analysis_id, exc)
            self._set_status(f"Error deleting record: {exc}", RED)
        finally:
            self.refresh()

    def _confirm_clear_all(self) -> None:
        """Ask the user to confirm clearing the entire history."""
        confirmed = messagebox.askyesno(
            title="Clear All History",
            message=(
                "Are you sure you want to delete ALL analysis records?\n\n"
                "This action cannot be undone."
            ),
            icon="warning",
        )
        if confirmed:
            self._clear_all_history()

    def _clear_all_history(self) -> None:
        """Delete every record from the database."""
        try:
            count = self.app_controller.db.clear_all_history()
            self._set_status(f"Cleared {count} record(s).", GREEN)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error clearing history: %s", exc)
            self._set_status(f"Error clearing history: {exc}", RED)
        finally:
            self.refresh()

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _set_status(self, message: str, color: str = GRAY_TEXT) -> None:
        """Update the footer status label."""
        self._status_label.configure(text=message, text_color=color)
        # Auto-clear after 5 seconds
        self.after(5000, lambda: self._status_label.configure(text=""))


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _fmt_timestamp(raw: str) -> str:
    """
    Format an ISO-8601 UTC timestamp string for display.

    Parameters
    ----------
    raw : str
        Raw timestamp from the database (e.g. ``"2024-06-01T12:30:00+00:00"``).

    Returns
    -------
    str
        Human-friendly string, e.g. ``"2024-06-01  12:30:00 UTC"``.
        Falls back to the raw string on any parse error.
    """
    if not raw:
        return "—"
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(raw)
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%d  %H:%M:%S UTC")
    except Exception:  # noqa: BLE001
        return raw
