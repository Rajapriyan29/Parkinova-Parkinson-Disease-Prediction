"""
spiral.py
=========
Clinical Spiral Drawing Analysis Module for Parkinova.
Mirrors the visual layout, card structure, typography, and interaction
patterns of the MRI Scan Analysis page (UploadFrame).

Features:
- Professional light-theme clinical dropzone matching UploadFrame
- File browser & drag-and-drop integration
- Instant spiral drawing preview with dimensions and format detection
- Control & Tremor test sample buttons for quick evaluation
- Patient reference code entry synced with app controller
- Non-blocking spiral analysis execution with progress spinner
- Clean Drawing Guidelines (Clinical Protocol section removed)
- Module Specifications sidebar
"""

from __future__ import annotations

import os
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, Dict, Any
import threading

import customtkinter as ctk
from PIL import Image, UnidentifiedImageError

from app.spiral_analysis import spiral_engine, validate_spiral_image

# Vintage Editorial Palette (matching upload.py exactly)
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
    "border_hover": "#123F2D",     # Deep forest green
    "dropzone_bg": "#EAE5CC",      # Subtle Background: Pale beige
    "dropzone_hover": "#F5F0D8",   # Warm cream
    "success": "#123F2D",          # Forest green
    "error": "#F0442E",            # Coral red
    "error_bg": "#FDF0EE",         # Soft coral tint
    "error_border": "#F8C0B8",     # Coral border
    "warn": "#D77B65",             # Soft terracotta
    "disabled": "#B8C4A5",         # Muted sage
}

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}
THUMB_MAX = 300


class SpiralFrame(ctk.CTkFrame):
    """
    Interactive Spiral Drawing Analysis Screen.
    Follows the exact UI structure and conventions of the MRI Scan Analysis page.
    """

    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0)
        self.app_controller = app_controller
        self.current_spiral_path: Optional[str] = None
        self._ctk_image: Optional[ctk.CTkImage] = None
        self._spiral_result: Optional[Dict[str, Any]] = None
        self._loading = False
        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_idx = 0
        self._spinner_job = None

        self.build_ui()

    def build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_content()
        self._build_action_bar()
        self._refresh_model_status()

    # ── Header (Identical height & style to upload.py) ────────────────────────
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=PALETTE["card"], corner_radius=0, height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.grid(row=0, column=0, padx=32, pady=14, sticky="w")

        ctk.CTkLabel(
            inner,
            text="Spiral Drawing Analysis",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left", padx=(0, 16))

        self.model_badge = ctk.CTkLabel(
            inner,
            text="● Checking Model…",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_muted"],
        )
        self.model_badge.pack(side="left")

        # Bottom border
        ctk.CTkFrame(self, height=1, fg_color=PALETTE["border"]).grid(
            row=0, column=0, sticky="sew"
        )

    # ── Content: 2-column grid (3:2 ratio matching upload.py) ─────────────────
    def _build_content(self):
        content = ctk.CTkFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        content.grid(row=1, column=0, sticky="nsew", padx=32, pady=20)
        content.grid_columnconfigure(0, weight=3)  # Dropzone Card
        content.grid_columnconfigure(1, weight=2)  # Details Sidebar
        content.grid_rowconfigure(0, weight=1)

        # ── Left: Dropzone Card ──
        self._dropzone_card = ctk.CTkFrame(
            content,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self._dropzone_card.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self._dropzone_card.grid_columnconfigure(0, weight=1)
        self._dropzone_card.grid_rowconfigure(0, weight=1)

        # Dropzone Inner Container
        self._dropzone = ctk.CTkFrame(
            self._dropzone_card,
            fg_color=PALETTE["dropzone_bg"],
            corner_radius=10,
            border_width=2,
            border_color=PALETTE["border"],
        )
        self._dropzone.grid(row=0, column=0, padx=20, pady=(20, 12), sticky="nsew")
        self._dropzone.grid_columnconfigure(0, weight=1)
        self._dropzone.grid_rowconfigure(0, weight=1)

        # 1. Placeholder (Empty State)
        self._placeholder = ctk.CTkFrame(self._dropzone, fg_color="transparent")
        self._placeholder.grid(row=0, column=0, sticky="nsew")
        self._placeholder.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self._placeholder,
            text="🌀",
            font=ctk.CTkFont(size=44),
        ).pack(pady=(28, 6))

        ctk.CTkLabel(
            self._placeholder,
            text="Drag & drop your spiral drawing here",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            self._placeholder,
            text="Supports PNG, JPG, JPEG, and BMP formats (Archimedean spiral sketches)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=PALETTE["text_muted"],
        ).pack(pady=(0, 14))

        self._browse_btn = ctk.CTkButton(
            self._placeholder,
            text="Browse Files",
            height=38,
            corner_radius=8,
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            text_color=PALETTE["primary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._browse_file,
        )
        self._browse_btn.pack(pady=(0, 16))

        # Test Sample quick buttons
        sample_bar = ctk.CTkFrame(self._placeholder, fg_color="transparent")
        sample_bar.pack(pady=(0, 20))

        ctk.CTkLabel(
            sample_bar,
            text="Quick Test Samples:",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            sample_bar,
            text="Control Sample",
            height=28,
            corner_radius=6,
            fg_color=PALETTE["secondary"],
            hover_color=PALETTE["secondary_hover"],
            border_width=1,
            border_color=PALETTE["border"],
            text_color=PALETTE["text_dark"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=lambda: self._load_sample("samples/sample_spiral_control.png"),
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            sample_bar,
            text="Tremor Sample",
            height=28,
            corner_radius=6,
            fg_color=PALETTE["secondary"],
            hover_color=PALETTE["secondary_hover"],
            border_width=1,
            border_color=PALETTE["border"],
            text_color=PALETTE["text_dark"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=lambda: self._load_sample("samples/sample_spiral_patient.png"),
        ).pack(side="left", padx=4)

        # 2. Preview Container (When image is selected)
        self._preview_container = ctk.CTkFrame(self._dropzone, fg_color="transparent")
        self._preview_container.grid_columnconfigure(0, weight=1)
        self._preview_container.grid_rowconfigure(0, weight=1)

        self._thumb_label = ctk.CTkLabel(self._preview_container, text="")
        self._thumb_label.pack(expand=True, pady=12)

        preview_btns = ctk.CTkFrame(self._preview_container, fg_color="transparent")
        preview_btns.pack(pady=(0, 12))

        ctk.CTkButton(
            preview_btns,
            text="🔄  Replace Drawing",
            height=34,
            corner_radius=6,
            fg_color=PALETTE["secondary"],
            hover_color=PALETTE["secondary_hover"],
            border_width=1,
            border_color=PALETTE["secondary_border"],
            text_color=PALETTE["secondary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._browse_file,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            preview_btns,
            text="🗑️  Remove",
            height=34,
            corner_radius=6,
            fg_color="transparent",
            hover_color=PALETTE["error_bg"],
            border_width=1,
            border_color=PALETTE["error_border"],
            text_color=PALETTE["error"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self.clear_image,
        ).pack(side="left", padx=6)

        # 3. Loading Overlay (During inference)
        self._loading_overlay = ctk.CTkFrame(self._dropzone, fg_color="transparent")
        self._loading_spinner_lbl = ctk.CTkLabel(
            self._loading_overlay,
            text="⠋",
            font=ctk.CTkFont(size=36),
            text_color=PALETTE["primary"],
        )
        self._loading_spinner_lbl.pack(pady=(50, 8))

        self._loading_text_lbl = ctk.CTkLabel(
            self._loading_overlay,
            text="Running CNN inference on spiral drawing…",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=PALETTE["text_dark"],
        )
        self._loading_text_lbl.pack()

        ctk.CTkLabel(
            self._loading_overlay,
            text="Preprocessing image, validating drawing shape, and evaluating kinematic tremor patterns",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=PALETTE["text_muted"],
        ).pack(pady=(4, 50))

        # 4. Result Details Strip (Shows beneath dropzone when analysis is complete)
        self.result_box = ctk.CTkFrame(
            self._dropzone_card,
            fg_color="#EAE5CC",
            corner_radius=8,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.result_box.grid(row=1, column=0, padx=20, pady=(0, 16), sticky="ew")

        res_inner = ctk.CTkFrame(self.result_box, fg_color="transparent")
        res_inner.pack(fill="x", padx=16, pady=10)

        self.result_title = ctk.CTkLabel(
            res_inner,
            text="Spiral Assessment Status: Pending",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        )
        self.result_title.pack(fill="x")

        self.result_text = ctk.CTkLabel(
            res_inner,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
            justify="left",
            wraplength=480,
            anchor="w",
        )
        self.result_text.pack(fill="x", pady=(2, 0))

        # Initially hide result box until analysis is performed
        self.result_box.grid_remove()

        # ── Right: Details & Guidelines Sidebar ──
        details_card = ctk.CTkFrame(
            content,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        details_card.grid(row=0, column=1, sticky="nsew")

        inner_details = ctk.CTkFrame(details_card, fg_color="transparent")
        inner_details.pack(fill="both", expand=True, padx=24, pady=20)

        # Drawing Metadata section
        ctk.CTkLabel(
            inner_details,
            text="Selected Drawing Information",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self._meta_label = ctk.CTkLabel(
            inner_details,
            text="No drawing currently selected.\nChoose a spiral file to begin analysis.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=PALETTE["text_muted"],
            anchor="w",
            justify="left",
            wraplength=260,
        )
        self._meta_label.pack(fill="x", pady=(0, 14))

        ctk.CTkFrame(inner_details, height=1, fg_color=PALETTE["border"]).pack(fill="x", pady=(0, 14))

        # Patient Reference
        ctk.CTkLabel(
            inner_details,
            text="Patient or Study Reference",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self.patient_code_var = ctk.StringVar()
        self.patient_entry = ctk.CTkEntry(
            inner_details,
            textvariable=self.patient_code_var,
            placeholder_text="Optional reference (e.g. PT-204)",
            height=38,
            corner_radius=8,
            fg_color=PALETTE["card"],
            border_color=PALETTE["border"],
            text_color=PALETTE["text_dark"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.patient_entry.pack(fill="x", pady=(0, 14))

        ctk.CTkFrame(inner_details, height=1, fg_color=PALETTE["border"]).pack(fill="x", pady=(0, 14))

        # Drawing Guidelines (Clinical Protocol section removed, clean bullet points)
        ctk.CTkLabel(
            inner_details,
            text="Drawing Guidelines",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        guidelines = (
            "• Provide a continuous Archimedean spiral drawn from center outward.\n"
            "• Drawn on plain white paper or tablet without guide templates.\n"
            "• High-contrast pen strokes with minimal background shadowing.\n"
            "• The model automatically conditions drawings to 244×244×3.\n"
            "• Evaluates fine-motor kinematics, tremor, and trajectory deviation."
        )
        ctk.CTkLabel(
            inner_details,
            text=guidelines,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
            anchor="w",
            justify="left",
            wraplength=260,
        ).pack(fill="x", pady=(0, 14))

        ctk.CTkFrame(inner_details, height=1, fg_color=PALETTE["border"]).pack(fill="x", pady=(0, 14))

        # Module Specifications
        ctk.CTkLabel(
            inner_details,
            text="Module Specifications",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self._spec_label = ctk.CTkLabel(
            inner_details,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
            anchor="w",
            justify="left",
            wraplength=260,
        )
        self._spec_label.pack(fill="x")
        self._update_spec_text()

        # Drag and Drop support
        self._setup_drag_drop()

    # ── Action Bar (Identical height & style to upload.py) ─────────────────────
    def _build_action_bar(self):
        bar = ctk.CTkFrame(self, fg_color=PALETTE["card"], corner_radius=0, height=72)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_columnconfigure(1, weight=0)

        self.status_var = ctk.StringVar(value="Select a spiral drawing to begin.")
        self.status_label = ctk.CTkLabel(
            bar,
            textvariable=self.status_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=PALETTE["text_muted"],
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, padx=32, pady=18, sticky="w")

        btn_box = ctk.CTkFrame(bar, fg_color="transparent")
        btn_box.grid(row=0, column=1, padx=(0, 32), pady=15)

        ctk.CTkButton(
            btn_box,
            text="← Back to MRI Scans",
            height=42,
            corner_radius=8,
            fg_color=PALETTE["secondary"],
            hover_color=PALETTE["secondary_hover"],
            border_width=1,
            border_color=PALETTE["secondary_border"],
            text_color=PALETTE["secondary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=lambda: self.app_controller.navigate_to("upload"),
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_box,
            text="Assessment Report →",
            height=42,
            corner_radius=8,
            fg_color=PALETTE["secondary"],
            hover_color=PALETTE["secondary_hover"],
            border_width=1,
            border_color=PALETTE["secondary_border"],
            text_color=PALETTE["secondary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._proceed_to_report,
        ).pack(side="left", padx=(0, 10))

        self.analyze_btn = ctk.CTkButton(
            btn_box,
            text="Analyze Spiral Drawing",
            width=190,
            height=42,
            corner_radius=8,
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            text_color=PALETTE["primary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            state="disabled",
            command=self._on_analyze_clicked,
        )
        self.analyze_btn.pack(side="left")

    # ── Drag & Drop ───────────────────────────────────────────────────────────
    def _setup_drag_drop(self):
        try:
            self._dropzone.drop_target_register("DND_Files")
            self._dropzone.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event):
        raw = getattr(event, "data", "")
        path = str(raw).strip().strip("{}")
        if path:
            self.validate_and_set_spiral(path)

    # ── File Selection & Validation ───────────────────────────────────────────
    def _browse_file(self):
        if self._loading:
            return
        path = filedialog.askopenfilename(
            title="Select Archimedean Spiral Image",
            filetypes=[
                ("Spiral Drawing Files", "*.png *.jpg *.jpeg *.bmp"),
                ("PNG Drawings", "*.png"),
                ("JPEG Drawings", "*.jpg *.jpeg"),
                ("Bitmap Drawings", "*.bmp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.validate_and_set_spiral(path)

    def _load_sample(self, relative_path: str):
        full_path = Path(__file__).resolve().parent.parent / relative_path
        if full_path.exists():
            self.validate_and_set_spiral(str(full_path))
        else:
            self._set_status(f"Sample file not found: {full_path}", error=True)

    def validate_and_set_spiral(self, path: str):
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            self._set_status(f"File not found: {path}", error=True)
            return

        ext = Path(path).suffix.lower()
        if ext not in SUPPORTED_EXTS:
            self._set_status(
                f"Unsupported format '{ext}'. Please select a PNG, JPG, or BMP file.",
                error=True,
            )
            return

        is_valid, err_msg, obs = validate_spiral_image(path)
        if not is_valid:
            self._set_status(err_msg, error=True)
            return

        try:
            img = Image.open(path).convert("RGB")
        except UnidentifiedImageError:
            self._set_status("File could not be identified as a valid image format.", error=True)
            return
        except Exception as exc:
            self._set_status(f"Error reading image: {exc}", error=True)
            return

        self.current_spiral_path = path
        self.result_box.grid_remove()

        w, h = img.size
        size_kb = os.path.getsize(path) / 1024

        self._show_preview(img, w, h, path)

        density = obs.get("stroke_density_pct", 0)
        self._meta_label.configure(
            text=(
                f"File: {os.path.basename(path)}\n"
                f"Resolution: {w} × {h} pixels\n"
                f"Size: {size_kb:.1f} KB\n"
                f"Stroke Coverage: {density:.1f}% canvas"
            ),
            text_color=PALETTE["text_dark"],
        )

        self._set_status(f"Ready: {os.path.basename(path)} ({w}×{h})", error=False)
        self._update_analyze_state()

    def _show_preview(self, img: Image.Image, w: int, h: int, path: str):
        self._placeholder.grid_forget()
        self._loading_overlay.grid_forget()

        scale = min(THUMB_MAX / w, THUMB_MAX / h, 1.0)
        tw = max(1, int(w * scale))
        th = max(1, int(h * scale))

        thumb = img.copy()
        thumb.thumbnail((tw, th), Image.LANCZOS)
        self._ctk_image = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(tw, th))
        self._thumb_label.configure(image=self._ctk_image)

        self._preview_container.grid(row=0, column=0, sticky="nsew")
        self._dropzone.configure(border_color=PALETTE["primary"])

    def clear_image(self):
        self._remove_image()

    def _remove_image(self):
        self.current_spiral_path = None
        self._spiral_result = None
        self._preview_container.grid_forget()
        self._loading_overlay.grid_forget()
        self.result_box.grid_remove()
        self._placeholder.grid(row=0, column=0, sticky="nsew")
        self._dropzone.configure(border_color=PALETTE["border"])

        self._meta_label.configure(
            text="No drawing currently selected.\nChoose a spiral file to begin analysis.",
            text_color=PALETTE["text_muted"],
        )
        self._set_status("Select a spiral drawing to begin.", error=False)
        self._update_analyze_state()

        if hasattr(self.app_controller, "set_spiral_result"):
            self.app_controller.set_spiral_result(None)
        elif hasattr(self.app_controller, "current_spiral_result"):
            self.app_controller.current_spiral_result = None

    def _set_status(self, message: str, error: bool = False):
        self.status_var.set(message)
        self.status_label.configure(
            text_color=PALETTE["error"] if error else PALETTE["text_muted"]
        )

    def _update_analyze_state(self):
        image_ok = self.current_spiral_path is not None
        if image_ok and not self._loading:
            self.analyze_btn.configure(
                state="normal",
                text="Analyze Spiral Drawing",
                fg_color=PALETTE["primary"],
            )
        else:
            self.analyze_btn.configure(
                state="disabled",
                text="Analyze Spiral Drawing",
                fg_color=PALETTE["primary"],
            )

    def _update_spec_text(self):
        if not hasattr(self, "_spec_label"):
            return
        is_loaded = spiral_engine.model_loaded
        is_yolo = spiral_engine.model_info.get("is_yolo", False) if is_loaded else False
        arch = "YOLO Spiral Classifier" if is_yolo else "Archimedean Spiral CNN"
        m_status = "Active Model Loaded" if is_loaded else "Awaiting Trained Weights"
        spec_text = (
            f"• Architecture: {arch}\n"
            f"• Input Shape: 224 × 224 × 3 Tensor\n"
            f"• Engine Status: {m_status}\n"
            f"• Task: Tremor & Dysgraphia Classification"
        )
        self._spec_label.configure(text=spec_text)

    def _refresh_model_status(self):
        if spiral_engine.model_loaded:
            is_yolo = spiral_engine.model_info.get("is_yolo", False)
            label = "● YOLO Model Ready" if is_yolo else "● CNN Model Ready"
            self.model_badge.configure(
                text=label,
                text_color=PALETTE["success"],
            )
        else:
            self.model_badge.configure(
                text="● Standby (Integration Ready)",
                text_color=PALETTE["warn"],
            )
        self._update_spec_text()
        self._update_analyze_state()

    # ── Inference Execution ───────────────────────────────────────────────────
    def _on_analyze_clicked(self):
        if not self.current_spiral_path:
            messagebox.showwarning("Drawing Required", "Please select a spiral drawing image first.")
            return

        pt_code = self.patient_code_var.get().strip()
        self.set_loading(True)

        def worker():
            try:
                res = spiral_engine.analyze_spiral(self.current_spiral_path, pt_code)
                self.after(0, lambda: self._on_analysis_done(res))
            except Exception as exc:
                self.after(0, lambda: self._on_analysis_failed(str(exc)))

        threading.Thread(target=worker, daemon=True, name="SpiralAnalysisWorker").start()

    def set_loading(self, active: bool):
        self._loading = active
        if active:
            self._preview_container.grid_forget()
            self._placeholder.grid_forget()
            self.result_box.grid_remove()
            self._loading_overlay.grid(row=0, column=0, sticky="nsew")
            self.analyze_btn.configure(state="disabled", text="Evaluating Drawing…")
            self._set_status("Running CNN inference pipeline on spiral…", error=False)
            self._start_spinner()
        else:
            self._stop_spinner()
            self._loading_overlay.grid_forget()
            if self.current_spiral_path:
                self._preview_container.grid(row=0, column=0, sticky="nsew")
            else:
                self._placeholder.grid(row=0, column=0, sticky="nsew")
            self._update_analyze_state()

    def _start_spinner(self):
        self._spinner_idx = 0
        self._animate_spinner()

    def _animate_spinner(self):
        if not self._loading:
            return
        frame = self._spinner_frames[self._spinner_idx % len(self._spinner_frames)]
        self._loading_spinner_lbl.configure(text=frame)
        self._spinner_idx += 1
        self._spinner_job = self.after(100, self._animate_spinner)

    def _stop_spinner(self):
        if self._spinner_job:
            try:
                self.after_cancel(self._spinner_job)
            except Exception:
                pass
            self._spinner_job = None

    def _on_analysis_done(self, res: Dict[str, Any]):
        self.set_loading(False)
        self._spiral_result = res

        # Store in app controller
        if hasattr(self.app_controller, "set_spiral_result"):
            self.app_controller.set_spiral_result(res)
        elif hasattr(self.app_controller, "current_spiral_result"):
            self.app_controller.current_spiral_result = res

        # Display result box
        status = res.get("status", "Completed")
        pred = res.get("model_prediction", "Completed")
        is_pd = res.get("is_parkinson", False)

        if is_pd:
            self.result_title.configure(
                text="● Spiral Assessment: Parkinson's Pattern Detected",
                text_color=PALETTE["primary"],
            )
            self.result_text.configure(
                text="Spiral drawing shows motor irregularities correlated with Parkinsonian tremor patterns.",
                text_color=PALETTE["primary"],
            )
        else:
            self.result_title.configure(
                text="● Spiral Assessment: No Pattern Detected",
                text_color=PALETTE["success"],
            )
            self.result_text.configure(
                text="Spiral drawing exhibits regular trajectory without distinctive Parkinsonian tremor pattern.",
                text_color=PALETTE["text_dark"],
            )
        self.result_box.grid()

        self._set_status("Spiral analysis completed. View results below or open Assessment Report.", error=False)

    def _on_analysis_failed(self, err: str):
        self.set_loading(False)
        self._set_status(f"Spiral analysis error: {err}", error=True)

    def _proceed_to_report(self):
        if self._spiral_result and hasattr(self.app_controller, "set_spiral_result"):
            self.app_controller.set_spiral_result(self._spiral_result)
        self.app_controller.navigate_to("results")

    def refresh(self):
        """Called when navigating to this frame."""
        self._refresh_model_status()
        # Sync patient code from app controller if empty
        if hasattr(self.app_controller, "current_patient_code") and self.app_controller.current_patient_code:
            current_val = self.patient_code_var.get().strip()
            if not current_val:
                self.patient_code_var.set(self.app_controller.current_patient_code)
