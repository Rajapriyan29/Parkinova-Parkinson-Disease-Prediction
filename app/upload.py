"""
upload.py
=========
Clinical MRI Upload Module for Parkinova.
Features:
- Professional light-theme clinical dropzone
- File browser & drag-and-drop integration
- Instant MRI image preview with dimensions and format detection
- Patient reference code entry
- Validated image replacement and removal
- Non-blocking analysis execution with single-click guard and progress spinner
- Strict validation for supported image formats (.png, .jpg, .jpeg, .bmp)
"""

from __future__ import annotations

import os
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk
from PIL import Image, UnidentifiedImageError

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
THUMB_MAX = 320


class UploadFrame(ctk.CTkFrame):
    """
    Interactive MRI Upload and Evaluation Screen.
    """

    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0)
        self.app_controller = app_controller
        self.current_image_path: Optional[str] = None
        self._ctk_image: Optional[ctk.CTkImage] = None
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

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=PALETTE["card"], corner_radius=0, height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.grid(row=0, column=0, padx=32, pady=14, sticky="w")

        ctk.CTkLabel(
            inner,
            text="Upload Brain MRI Scan",
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

    def _build_content(self):
        content = ctk.CTkFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        content.grid(row=1, column=0, sticky="nsew", padx=32, pady=24)
        content.grid_columnconfigure(0, weight=3)  # Dropzone
        content.grid_columnconfigure(1, weight=2)  # Information & metadata panel
        content.grid_rowconfigure(0, weight=1)

        # ── Dropzone Card ──
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

        self._dropzone = ctk.CTkFrame(
            self._dropzone_card,
            fg_color=PALETTE["dropzone_bg"],
            corner_radius=10,
            border_width=2,
            border_color=PALETTE["border"],
        )
        self._dropzone.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self._dropzone.grid_columnconfigure(0, weight=1)
        self._dropzone.grid_rowconfigure(0, weight=1)

        # Placeholder (Empty state)
        self._placeholder = ctk.CTkFrame(self._dropzone, fg_color="transparent")
        self._placeholder.grid(row=0, column=0, sticky="nsew")
        self._placeholder.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self._placeholder,
            text="🧠",
            font=ctk.CTkFont(size=48),
        ).pack(pady=(40, 10))

        ctk.CTkLabel(
            self._placeholder,
            text="Drag & drop your brain MRI scan here",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            self._placeholder,
            text="Supports PNG, JPG, JPEG, and BMP formats (Axial, Coronal, or Sagittal views)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=PALETTE["text_muted"],
        ).pack(pady=(0, 16))

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
        self._browse_btn.pack(pady=(0, 32))

        # Preview Container (Populated when image is selected)
        self._preview_container = ctk.CTkFrame(self._dropzone, fg_color="transparent")
        self._preview_container.grid_columnconfigure(0, weight=1)
        self._preview_container.grid_rowconfigure(0, weight=1)

        self._thumb_label = ctk.CTkLabel(self._preview_container, text="")
        self._thumb_label.pack(expand=True, pady=16)

        # Overlay Controls (Remove / Replace)
        preview_btns = ctk.CTkFrame(self._preview_container, fg_color="transparent")
        preview_btns.pack(pady=(0, 16))

        ctk.CTkButton(
            preview_btns,
            text="🔄  Replace Scan",
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

        # Loading Overlay (Shown during analysis)
        self._loading_overlay = ctk.CTkFrame(self._dropzone, fg_color="transparent")
        self._loading_spinner_lbl = ctk.CTkLabel(
            self._loading_overlay,
            text="⠋",
            font=ctk.CTkFont(size=36),
            text_color=PALETTE["primary"],
        )
        self._loading_spinner_lbl.pack(pady=(60, 8))

        self._loading_text_lbl = ctk.CTkLabel(
            self._loading_overlay,
            text="Running CNN inference on MRI scan…",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=PALETTE["text_dark"],
        )
        self._loading_text_lbl.pack()

        ctk.CTkLabel(
            self._loading_overlay,
            text="Preprocessing image, validating input shape, and computing neural activations",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=PALETTE["text_muted"],
        ).pack(pady=(4, 60))

        # ── Details & Guidelines Sidebar ──
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

        # Image Metadata section
        ctk.CTkLabel(
            inner_details,
            text="Selected Scan Information",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self._meta_label = ctk.CTkLabel(
            inner_details,
            text="No scan currently selected.\nChoose an MRI file to begin analysis.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=PALETTE["text_muted"],
            anchor="w",
            justify="left",
            wraplength=260,
        )
        self._meta_label.pack(fill="x", pady=(0, 16))

        ctk.CTkFrame(inner_details, height=1, fg_color=PALETTE["border"]).pack(fill="x", pady=(0, 16))

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
        self.patient_entry.pack(fill="x", pady=(0, 16))

        ctk.CTkFrame(inner_details, height=1, fg_color=PALETTE["border"]).pack(fill="x", pady=(0, 16))

        # Clinical Guidelines
        ctk.CTkLabel(
            inner_details,
            text="Scan Guidelines",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        guidelines = (
            "• Provide high-contrast T1, T2, or Diffusion brain MRI scans.\n"
            "• Ensure scan has a standard black background without document borders.\n"
            "• The model automatically resizes and conditions scans to 244×244×3.\n"
            "• Never upload unanonymized patient personal health information."
        )
        ctk.CTkLabel(
            inner_details,
            text=guidelines,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
            anchor="w",
            justify="left",
            wraplength=260,
        ).pack(fill="x")

        # Setup drop target if available
        self._setup_drag_drop()

    def _build_action_bar(self):
        bar = ctk.CTkFrame(self, fg_color=PALETTE["card"], corner_radius=0, height=72)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_columnconfigure(1, weight=0)

        self.status_var = ctk.StringVar(value="Select an MRI scan to begin.")
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
            text="Spiral Analysis →",
            height=42,
            corner_radius=8,
            fg_color=PALETTE["secondary"],
            hover_color=PALETTE["secondary_hover"],
            border_width=1,
            border_color=PALETTE["secondary_border"],
            text_color=PALETTE["secondary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=lambda: self.app_controller.navigate_to("spiral"),
        ).pack(side="left", padx=(0, 10))

        self.analyze_btn = ctk.CTkButton(
            btn_box,
            text="Analyze MRI Scan",
            width=180,
            height=42,
            corner_radius=8,
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            text_color=PALETTE["primary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            state="disabled",
            command=self._on_analyze,
        )
        self.analyze_btn.pack(side="left")

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
            self.validate_and_set_image(path)

    def _browse_file(self):
        if self._loading:
            return
        path = filedialog.askopenfilename(
            title="Select Brain MRI Scan",
            filetypes=[
                ("MRI Image Files", "*.png *.jpg *.jpeg *.bmp"),
                ("PNG Scans", "*.png"),
                ("JPEG Scans", "*.jpg *.jpeg"),
                ("Bitmap Scans", "*.bmp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.validate_and_set_image(path)

    def validate_and_set_image(self, path: str):
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            self._set_status(f"File not found: {path}", error=True)
            return

        ext = Path(path).suffix.lower()
        if ext not in SUPPORTED_EXTS:
            self._set_status(
                f"Unsupported format '{ext}'. Please select a PNG, JPG, or BMP scan.",
                error=True,
            )
            return

        try:
            img = Image.open(path)
            img.verify()
            img = Image.open(path)
        except UnidentifiedImageError:
            self._set_status("File could not be identified as a valid image format.", error=True)
            return
        except Exception as exc:
            self._set_status(f"Error reading image: {exc}", error=True)
            return

        self.current_image_path = path
        if hasattr(self.app_controller, "set_current_image"):
            self.app_controller.set_current_image(path)

        w, h = img.size
        size_kb = os.path.getsize(path) / 1024

        self._show_preview(img, w, h, path)

        self._meta_label.configure(
            text=(
                f"File: {os.path.basename(path)}\n"
                f"Resolution: {w} × {h} pixels\n"
                f"Size: {size_kb:.1f} KB\n"
                f"Format: {ext.upper().lstrip('.')} Scan"
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
        self.current_image_path = None
        self._preview_container.grid_forget()
        self._loading_overlay.grid_forget()
        self._placeholder.grid(row=0, column=0, sticky="nsew")
        self._dropzone.configure(border_color=PALETTE["border"])

        self._meta_label.configure(
            text="No scan currently selected.\nChoose an MRI file to begin analysis.",
            text_color=PALETTE["text_muted"],
        )
        self._set_status("Select an MRI scan to begin.", error=False)
        self._update_analyze_state()

    def _set_status(self, message: str, error: bool = False):
        self.status_var.set(message)
        self.status_label.configure(
            text_color=PALETTE["error"] if error else PALETTE["text_muted"]
        )

    def _update_analyze_state(self):
        model_ok = bool(getattr(self.app_controller, "model_loaded", False))
        image_ok = self.current_image_path is not None

        if model_ok and image_ok and not self._loading:
            self.analyze_btn.configure(
                state="normal",
                text="Analyze MRI Scan",
                fg_color=PALETTE["primary"],
            )
        elif not model_ok:
            self.analyze_btn.configure(
                state="disabled",
                text="Waiting for Model…",
                fg_color=PALETTE["disabled"],
            )
        else:
            self.analyze_btn.configure(
                state="disabled",
                text="Analyze MRI Scan",
                fg_color=PALETTE["primary"],
            )

    def _refresh_model_status(self):
        model_ok = bool(getattr(self.app_controller, "model_loaded", False))
        if model_ok:
            self.model_badge.configure(
                text="● CNN Model Ready",
                text_color=PALETTE["success"],
            )
        else:
            self.model_badge.configure(
                text="● Model Loading…",
                text_color=PALETTE["warn"],
            )
        self._update_analyze_state()

    def _on_analyze(self):
        if not self.current_image_path:
            messagebox.showwarning("Scan Required", "Please select an MRI image scan first.")
            return

        if not getattr(self.app_controller, "model_loaded", False):
            messagebox.showerror(
                "Model Not Initialized",
                "The deep learning CNN model is still initializing. Please wait a few seconds and try again.",
            )
            return

        patient_code = self.patient_code_var.get().strip()
        self.app_controller.run_analysis(self.current_image_path, patient_code)

    def set_loading(self, active: bool):
        self._loading = active
        if active:
            self._preview_container.grid_forget()
            self._placeholder.grid_forget()
            self._loading_overlay.grid(row=0, column=0, sticky="nsew")
            self.analyze_btn.configure(state="disabled", text="Evaluating Scan…")
            self._set_status("Running CNN inference pipeline…", error=False)
            self._start_spinner()
        else:
            self._stop_spinner()
            self._loading_overlay.grid_forget()
            if self.current_image_path:
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

    def refresh(self):
        self._refresh_model_status()
