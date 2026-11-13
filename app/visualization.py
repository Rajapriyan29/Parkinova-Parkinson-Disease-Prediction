"""
visualization.py
================
Image Visualization panel for Parkinova.

Side-by-side display of the original MRI and the preprocessed (model-input)
version, with a preprocessing metadata card, an explanatory note, and an
optional pixel-intensity histogram rendered via matplotlib.

Author: Parkinova Team
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Optional

import customtkinter as ctk
import numpy as np
from PIL import Image

# Matplotlib is optional — histogram is shown only when available
try:
    import matplotlib
    matplotlib.use("Agg")                       # non-interactive back-end
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    _MATPLOTLIB_OK = True
except ImportError:                             # pragma: no cover
    _MATPLOTLIB_OK = False

# ---------------------------------------------------------------------------
# Vintage Editorial Palette (Warm Cream, Deep Forest Green, Coral Red)
# ---------------------------------------------------------------------------
BG_COLOR        = "#F5F0D8"   # Warm cream
CARD_COLOR      = "#FFF9E9"   # Warm off-white
NAVY            = "#123F2D"   # Deep forest green
CYAN            = "#F0442E"   # Vibrant coral red
BORDER_COLOR    = "#B8C4A5"   # Muted sage green
TEXT_PRIMARY    = "#123F2D"   # Deep forest green
TEXT_SECONDARY  = "#365747"   # Muted dark green
TEXT_MUTED      = "#365747"   # Muted dark green
ROW_ALT         = "#EAE5CC"   # Pale beige


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_card(parent: ctk.CTkFrame, **kwargs) -> ctk.CTkFrame:
    """Return a white rounded CTkFrame styled as a card."""
    defaults = dict(
        fg_color=CARD_COLOR,
        corner_radius=12,
        border_width=1,
        border_color=BORDER_COLOR,
    )
    defaults.update(kwargs)
    return ctk.CTkFrame(parent, **defaults)


def _label(
    parent,
    text: str = "",
    font_size: int = 13,
    bold: bool = False,
    italic: bool = False,
    color: str = TEXT_PRIMARY,
    wraplength: int = 0,
    justify: str = "left",
) -> ctk.CTkLabel:
    """Convenience CTkLabel factory."""
    weight = "bold"   if bold   else "normal"
    slant  = "italic" if italic else "roman"
    font   = ctk.CTkFont(size=font_size, weight=weight, slant=slant)
    kw: dict[str, Any] = dict(text=text, font=font, text_color=color,
                               justify=justify)
    if wraplength:
        kw["wraplength"] = wraplength
    return ctk.CTkLabel(parent, **kw)


def _array_to_pil(arr: np.ndarray) -> Image.Image:
    """
    Convert a numpy array to a PIL RGB image.

    Supports shapes: ``(H, W)``, ``(H, W, 1)``, ``(H, W, 3)``, ``(H, W, 4)``.
    Float arrays in [0, 1] are scaled to [0, 255]; other float arrays are
    min-max normalised.
    """
    arr = np.squeeze(arr).copy()
    if arr.dtype != np.uint8:
        lo, hi = float(arr.min()), float(arr.max())
        if hi <= 1.0:
            arr = (arr * 255).clip(0, 255).astype(np.uint8)
        else:
            arr = ((arr - lo) / (hi - lo + 1e-9) * 255).clip(0, 255).astype(np.uint8)

    if arr.ndim == 2:
        return Image.fromarray(arr, mode="L").convert("RGB")
    if arr.ndim == 3 and arr.shape[2] == 1:
        return Image.fromarray(arr[:, :, 0], mode="L").convert("RGB")
    if arr.ndim == 3 and arr.shape[2] == 3:
        return Image.fromarray(arr, mode="RGB")
    if arr.ndim == 3 and arr.shape[2] == 4:
        return Image.fromarray(arr, mode="RGBA").convert("RGB")
    raise ValueError(f"Unsupported array shape: {arr.shape}")


# ---------------------------------------------------------------------------
# Panel widget: a single image pane (label + image label + dimensions text)
# ---------------------------------------------------------------------------
class _ImagePanel(ctk.CTkFrame):
    """
    A titled card that shows one image plus its dimension string.

    Parameters
    ----------
    parent:
        Parent widget.
    title:
        Panel heading (e.g. "Original Image").
    max_size:
        Tuple ``(width, height)`` — thumbnail bounding box.
    """

    MAX_SIZE = (280, 280)

    def __init__(self, parent: Any, title: str,
                 max_size: tuple[int, int] = MAX_SIZE) -> None:
        super().__init__(parent, fg_color="transparent")
        self._max = max_size
        self._ctk_image: Optional[ctk.CTkImage] = None

        self.grid_columnconfigure(0, weight=1)

        card = _make_card(self)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        _label(card, title, font_size=13, bold=True,
               color=NAVY).pack(pady=(14, 6))

        self._img_lbl = ctk.CTkLabel(
            card,
            text="No image",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11, slant="italic"),
        )
        self._img_lbl.pack(padx=16, pady=(0, 6))

        self._dim_lbl = _label(card, "", font_size=11, color=TEXT_MUTED)
        self._dim_lbl.pack(pady=(0, 12))

    def set_image(self, arr: np.ndarray) -> None:
        """Display *arr* as a thumbnail; update dimension label."""
        try:
            pil = _array_to_pil(arr)
        except Exception as exc:
            self._img_lbl.configure(image=None, text=f"Error: {exc}")  # type: ignore[arg-type]
            self._dim_lbl.configure(text="")
            return

        h, w = arr.shape[:2]
        ch   = arr.shape[2] if arr.ndim == 3 else 1
        self._dim_lbl.configure(text=f"{w} × {h} px  |  {ch} ch")

        pil.thumbnail(self._max, Image.LANCZOS)
        self._ctk_image = ctk.CTkImage(
            light_image=pil, dark_image=pil, size=pil.size
        )
        self._img_lbl.configure(image=self._ctk_image, text="")

    def clear(self) -> None:
        """Reset to placeholder state."""
        self._ctk_image = None
        self._img_lbl.configure(image=None, text="No image")  # type: ignore[arg-type]
        self._dim_lbl.configure(text="")


# ---------------------------------------------------------------------------
# Main frame
# ---------------------------------------------------------------------------
class VisualizationFrame(ctk.CTkFrame):
    """
    Visualization panel showing original vs. preprocessed MRI images,
    preprocessing metadata, and an optional pixel-intensity histogram.

    Parameters
    ----------
    parent:
        The parent Tkinter / CTk widget.
    app_controller:
        Top-level controller (reserved for future navigation calls;
        not actively used in this frame).
    """

    def __init__(self, parent: Any, app_controller: Any) -> None:
        super().__init__(parent, fg_color=BG_COLOR, corner_radius=0)
        self._app = app_controller

        # Keep references to avoid GC
        self._hist_canvas: Optional[Any]  = None
        self._hist_fig:    Optional[Any]  = None

        self.build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def build_ui(self) -> None:
        """Construct all widgets. Called once from ``__init__``."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ──────────────────────────────────────────────────────
        self._build_header()

        # ── Scrollable content ──────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_COLOR, corner_radius=0
        )
        self._scroll.grid(row=1, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        row = 0
        row = self._build_image_panels(row)
        row = self._build_info_card(row)
        row = self._build_note(row)
        if _MATPLOTLIB_OK:
            row = self._build_histogram_card(row)

    # ── Header ──────────────────────────────────────────────────────────
    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=CARD_COLOR,
                              corner_radius=0, border_width=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(padx=32, pady=18, anchor="w")

        _label(inner, "Image Visualization",
               font_size=24, bold=True, color=NAVY).pack(anchor="w")
        _label(inner,
               "Original scan vs. preprocessed model input",
               font_size=12, color=TEXT_SECONDARY).pack(anchor="w", pady=(2, 0))

        # Cyan accent line
        ctk.CTkFrame(self, fg_color=CYAN, height=3,
                     corner_radius=0).grid(row=0, column=0, sticky="sew")

    # ── Two-panel image row ─────────────────────────────────────────────
    def _build_image_panels(self, start_row: int) -> int:
        container = ctk.CTkFrame(self._scroll, fg_color="transparent")
        container.grid(row=start_row, column=0, sticky="ew",
                       padx=24, pady=(20, 0))
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

        self._panel_original = _ImagePanel(container, "Original Image")
        self._panel_original.grid(row=0, column=0, sticky="nsew",
                                  padx=(0, 8))

        self._panel_preprocessed = _ImagePanel(
            container, "Preprocessed  (Model Input)"
        )
        self._panel_preprocessed.grid(row=0, column=1, sticky="nsew",
                                      padx=(8, 0))

        return start_row + 1

    # ── Info card ───────────────────────────────────────────────────────
    def _build_info_card(self, start_row: int) -> int:
        card = _make_card(self._scroll)
        card.grid(row=start_row, column=0, sticky="ew",
                  padx=24, pady=(16, 0))
        card.grid_columnconfigure(0, weight=1)

        _label(card, "Preprocessing Details",
               font_size=14, bold=True, color=NAVY).pack(
            anchor="w", padx=20, pady=(14, 8)
        )

        self._info_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._info_frame.pack(fill="x", padx=20, pady=(0, 14))

        return start_row + 1

    def _populate_info(self, info: dict) -> None:
        """Render preprocessing key-value pairs inside ``_info_frame``."""
        for w in self._info_frame.winfo_children():
            w.destroy()

        self._info_frame.grid_columnconfigure(0, weight=1)
        self._info_frame.grid_columnconfigure(1, weight=2)

        fields = [
            ("Original Size",  str(info.get("original_size", "—"))),
            ("Target Size",    str(info.get("target_size",   "—"))),
            ("Channels",       str(info.get("channels",      "—"))),
            ("Normalized",     "Yes" if info.get("normalized") else "No"),
        ]

        for row_i, (key, val) in enumerate(fields):
            bg = ROW_ALT if row_i % 2 == 0 else CARD_COLOR
            row_f = ctk.CTkFrame(self._info_frame, fg_color=bg,
                                 corner_radius=6)
            row_f.grid(row=row_i, column=0, columnspan=2,
                       sticky="ew", pady=2)
            row_f.grid_columnconfigure(0, weight=1)
            row_f.grid_columnconfigure(1, weight=2)

            _label(row_f, key, font_size=12, bold=True,
                   color=TEXT_SECONDARY).grid(
                row=0, column=0, sticky="w", padx=12, pady=5
            )
            _label(row_f, val, font_size=12,
                   color=TEXT_PRIMARY).grid(
                row=0, column=1, sticky="w", padx=12, pady=5
            )

    # ── Explanatory note ─────────────────────────────────────────────────
    def _build_note(self, start_row: int) -> int:
        note_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        note_frame.grid(row=start_row, column=0, sticky="ew",
                        padx=24, pady=(10, 0))

        _label(
            note_frame,
            "ℹ  The preprocessed image shown above is the exact input "
            "supplied to the CNN model.",
            font_size=11,
            italic=True,
            color=TEXT_MUTED,
            wraplength=860,
        ).pack(anchor="w")

        return start_row + 1

    # ── Histogram card (matplotlib) ─────────────────────────────────────
    def _build_histogram_card(self, start_row: int) -> int:
        card = _make_card(self._scroll)
        card.grid(row=start_row, column=0, sticky="ew",
                  padx=24, pady=(16, 24))
        card.grid_columnconfigure(0, weight=1)

        _label(card, "Pixel Intensity Histogram",
               font_size=14, bold=True, color=NAVY).pack(
            anchor="w", padx=20, pady=(14, 8)
        )

        self._hist_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._hist_frame.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        self._hist_placeholder = _label(
            self._hist_frame,
            "Load an image to see the intensity histogram.",
            font_size=11, italic=True, color=TEXT_MUTED,
        )
        self._hist_placeholder.pack(pady=20)

        return start_row + 1

    def _render_histogram(self, original: np.ndarray,
                          preprocessed: np.ndarray) -> None:
        """Embed a side-by-side matplotlib histogram into the card."""
        if not _MATPLOTLIB_OK:
            return

        # Remove previous canvas
        if self._hist_canvas is not None:
            try:
                self._hist_canvas.get_tk_widget().destroy()
            except Exception:
                pass
            self._hist_canvas = None
        if self._hist_fig is not None:
            plt.close(self._hist_fig)
            self._hist_fig = None

        self._hist_placeholder.pack_forget()

        fig, axes = plt.subplots(1, 2, figsize=(9, 2.8), dpi=90)
        fig.patch.set_facecolor(CARD_COLOR)

        for ax, arr, title in [
            (axes[0], original,      "Original"),
            (axes[1], preprocessed,  "Preprocessed"),
        ]:
            flat = arr.ravel().astype(float)
            ax.hist(flat, bins=64, color=CYAN, edgecolor="none", alpha=0.85)
            ax.set_title(title, fontsize=10, color=NAVY, fontweight="bold")
            ax.set_xlabel("Pixel value", fontsize=8, color=TEXT_SECONDARY)
            ax.set_ylabel("Count",       fontsize=8, color=TEXT_SECONDARY)
            ax.tick_params(labelsize=7, colors=TEXT_SECONDARY)
            ax.set_facecolor(BG_COLOR)
            for spine in ax.spines.values():
                spine.set_edgecolor(BORDER_COLOR)

        fig.tight_layout(pad=1.5)

        canvas = FigureCanvasTkAgg(fig, master=self._hist_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        self._hist_canvas = canvas
        self._hist_fig    = fig

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def display_images(
        self,
        original_array: np.ndarray,
        preprocessed_array: np.ndarray,
        info: dict,
    ) -> None:
        """
        Populate every panel with image and metadata.

        Parameters
        ----------
        original_array:
            Raw MRI pixel data as loaded from disk (before preprocessing).
            Shape: ``(H, W)``, ``(H, W, 1)``, or ``(H, W, 3)``.
        preprocessed_array:
            The array fed to the model (after resize + normalisation).
            Displayed un-normalised (auto-scaled) for visual clarity.
        info:
            Preprocessing metadata dict with keys:

            - ``original_size`` — e.g. ``(512, 512)``
            - ``target_size``   — e.g. ``(224, 224)``
            - ``channels``      — int
            - ``normalized``    — bool
        """
        self._panel_original.set_image(original_array)
        self._panel_preprocessed.set_image(preprocessed_array)
        self._populate_info(info)

        if _MATPLOTLIB_OK:
            self._render_histogram(original_array, preprocessed_array)

    def clear(self) -> None:
        """Reset all panels to their default empty state."""
        self._panel_original.clear()
        self._panel_preprocessed.clear()

        for w in self._info_frame.winfo_children():
            w.destroy()

        if _MATPLOTLIB_OK and self._hist_canvas is not None:
            try:
                self._hist_canvas.get_tk_widget().destroy()
            except Exception:
                pass
            self._hist_canvas = None
        if _MATPLOTLIB_OK and self._hist_fig is not None:
            plt.close(self._hist_fig)
            self._hist_fig = None
        if _MATPLOTLIB_OK and hasattr(self, "_hist_placeholder"):
            self._hist_placeholder.pack(pady=20)
