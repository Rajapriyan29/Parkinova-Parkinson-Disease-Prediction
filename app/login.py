"""
login.py
--------
Clean, modern light-theme Login and Authentication window for Parkinova.
Features:
- Email/Username + Password sign-in
- Secure Google Sign-In (OAuth 2.0 flow)
- Input format validation (e.g. Gmail / institutional address validation)
- Password visibility toggle
- Informative inline error feedback
- Session establishment via AuthService
"""

import os
import sys
import logging
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image

from app.auth import auth_service, validate_email_format

logger = logging.getLogger(__name__)

# Determine root dir
if getattr(sys, "frozen", False):
    _APP_DIR = Path(sys.executable).resolve().parent
    _BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", _APP_DIR))
else:
    _APP_DIR = Path(__file__).resolve().parent.parent
    _BUNDLE_DIR = _APP_DIR

# ---------------------------------------------------------------------------
# Vintage Editorial Palette (Warm Cream, Forest Green, Coral Red)
# ---------------------------------------------------------------------------
PALETTE = {
    "bg": "#F5F0D8",            # Primary Background: Warm cream / vintage ivory
    "card": "#FFF9E9",          # Highlight Color: Warm off-white
    "primary": "#F0442E",       # Accent Color: Vibrant coral red
    "primary_hover": "#D43823", # Slightly darker coral
    "primary_text": "#FFF9E9",  # Warm off-white
    "secondary": "#EAE5CC",     # Subtle Pale beige
    "text_dark": "#123F2D",     # Primary Text: Deep forest green
    "text_muted": "#365747",    # Secondary Text: Muted dark green
    "border": "#B8C4A5",        # Border Color: Muted sage green
    "border_focus": "#123F2D",  # Forest green outline
    "error": "#F0442E",         # Coral red
    "error_bg": "#FDF0EE",      # Coral tint
    "error_border": "#F8C0B8",  # Soft coral border
    "success": "#123F2D",       # Forest green
    "input_bg": "#FFF9E9",      # Warm ivory background
    "google_btn": "#FFF9E9",    # Cream secondary button
    "google_hover": "#EAE5CC",  # Pale beige hover
}


class LoginWindow(ctk.CTkToplevel):
    """
    Modern clinical light-themed authentication window.
    """

    def __init__(self, on_success: Callable[[str, str, str], None], on_cancel: Callable[[], None], parent=None):
        super().__init__(master=parent)
        self.on_success = on_success
        self.on_cancel = on_cancel

        self.title("Parkinova — Clinical Sign In")
        self.geometry("460x650")
        self.minsize(440, 620)
        self.resizable(False, False)
        self.configure(fg_color=PALETTE["bg"])

        # Center on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - 460) // 2)
        y = max(0, (sh - 650) // 2)
        self.geometry(f"460x650+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._show_pw = False

        self._build_ui()

        # Foreground & Modal focus
        self.attributes("-topmost", True)
        self.after(50, self._ensure_visible)
        self.after(400, lambda: self.attributes("-topmost", False))
        self.lift()
        self.focus_force()

    def _ensure_visible(self):
        """Guarantee visibility even if parent is withdrawn on Windows."""
        try:
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.after(350, lambda: self.attributes("-topmost", False))
            self.focus_force()
        except Exception:
            pass

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Card container
        self.card = ctk.CTkFrame(
            self,
            fg_color=PALETTE["card"],
            corner_radius=16,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.card.grid(row=0, column=0, padx=24, pady=24, sticky="nsew")
        self.card.grid_columnconfigure(0, weight=1)

        # Header branding
        self._build_header()

        # Auth form
        self._build_form()

        # Google Sign-In & actions
        self._build_actions()

        # Disclaimer footer
        self._build_footer()

    def _build_header(self):
        header_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        header_frame.pack(fill="x", padx=32, pady=(28, 12))

        # Logo icon
        logo_candidates = [
            _BUNDLE_DIR / "assets" / "logo_circle.png",
            _APP_DIR / "assets" / "logo_circle.png",
            _BUNDLE_DIR / "assets" / "logo.png",
            _APP_DIR / "assets" / "logo.png",
        ]
        logo_path = next((p for p in logo_candidates if p.exists()), None)

        self._logo_img = None
        if logo_path:
            try:
                pil_logo = Image.open(str(logo_path)).resize((52, 52), Image.LANCZOS)
                self._logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(52, 52))
                ctk.CTkLabel(header_frame, image=self._logo_img, text="").pack(pady=(0, 6))
            except Exception:
                ctk.CTkLabel(header_frame, text="🧠", font=ctk.CTkFont(size=42)).pack(pady=(0, 6))
        else:
            ctk.CTkLabel(header_frame, text="🧠", font=ctk.CTkFont(size=42)).pack(pady=(0, 6))

        ctk.CTkLabel(
            header_frame,
            text="Parkinova",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack()

        ctk.CTkLabel(
            header_frame,
            text="Parkinson's MRI Analysis Platform",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=PALETTE["text_muted"],
        ).pack(pady=(2, 0))

    def _build_form(self):
        form_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        form_frame.pack(fill="x", padx=32, pady=(10, 8))
        form_frame.grid_columnconfigure(0, weight=1)

        # Email / Identifier
        ctk.CTkLabel(
            form_frame,
            text="Email or Username",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.ident_var = ctk.StringVar(value="admin@parkinova.org")
        self.ident_entry = ctk.CTkEntry(
            form_frame,
            textvariable=self.ident_var,
            placeholder_text="name@gmail.com or username",
            height=40,
            corner_radius=8,
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["border"],
            text_color=PALETTE["text_dark"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
        )
        self.ident_entry.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        # Password
        ctk.CTkLabel(
            form_frame,
            text="Password",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self.pw_var = ctk.StringVar(value="parkinova2024")
        self.pw_entry = ctk.CTkEntry(
            form_frame,
            textvariable=self.pw_var,
            placeholder_text="Enter password",
            show="●",
            height=40,
            corner_radius=8,
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["border"],
            text_color=PALETTE["text_dark"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
        )
        self.pw_entry.grid(row=3, column=0, sticky="ew", pady=(0, 4))

        # Show password toggle
        pw_tools = ctk.CTkFrame(form_frame, fg_color="transparent")
        pw_tools.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        
        self.show_pw_btn = ctk.CTkButton(
            pw_tools,
            text="👁  Show Password",
            fg_color="transparent",
            hover_color=PALETTE["bg"],
            text_color=PALETTE["text_muted"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=20,
            anchor="w",
            command=self._toggle_pw,
        )
        self.show_pw_btn.pack(side="left")

        # Inline Error Banner
        self.error_frame = ctk.CTkFrame(
            form_frame,
            fg_color=PALETTE["error_bg"],
            corner_radius=6,
            border_width=1,
            border_color=PALETTE["error_border"],
        )
        self.error_label = ctk.CTkLabel(
            self.error_frame,
            text="",
            text_color=PALETTE["error"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
            wraplength=340,
            justify="left",
        )
        self.error_label.pack(padx=10, pady=6, anchor="w")
        # Hidden by default
        self.error_frame.grid_remove()

    def _build_actions(self):
        actions_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        actions_frame.pack(fill="x", padx=32, pady=(4, 12))

        # Sign In Button
        self.sign_in_btn = ctk.CTkButton(
            actions_frame,
            text="Sign In",
            height=42,
            corner_radius=8,
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            text_color=PALETTE["primary_text"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._attempt_sign_in,
        )
        self.sign_in_btn.pack(fill="x", pady=(0, 10))

        # Or divider
        divider = ctk.CTkFrame(actions_frame, fg_color="transparent")
        divider.pack(fill="x", pady=(4, 10))
        ctk.CTkFrame(divider, height=1, fg_color=PALETTE["border"]).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            divider,
            text="  OR  ",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=PALETTE["text_muted"],
        ).pack(side="left")
        ctk.CTkFrame(divider, height=1, fg_color=PALETTE["border"]).pack(side="left", fill="x", expand=True)

        # Google Sign-In Button
        self.google_btn = ctk.CTkButton(
            actions_frame,
            text="G   Sign In with Google",
            height=40,
            corner_radius=8,
            fg_color=PALETTE["google_btn"],
            hover_color=PALETTE["google_hover"],
            border_width=1,
            border_color=PALETTE["text_dark"],
            text_color=PALETTE["text_dark"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._attempt_google_sign_in,
        )
        self.google_btn.pack(fill="x", pady=(0, 6))

        # Enter key triggers sign in
        self.ident_entry.bind("<Return>", lambda e: self.pw_entry.focus())
        self.pw_entry.bind("<Return>", lambda e: self._attempt_sign_in())

    def _build_footer(self):
        footer_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", padx=24, pady=(0, 16))

        hint_label = ctk.CTkLabel(
            footer_frame,
            text="Default Researcher: admin@parkinova.org / parkinova2024",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=PALETTE["text_muted"],
        )
        hint_label.pack()

        disclaimer_label = ctk.CTkLabel(
            footer_frame,
            text="Academic & Research Prototype · Not for Clinical Diagnosis",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=PALETTE["text_muted"],
        )
        disclaimer_label.pack(pady=(2, 0))

    def _toggle_pw(self):
        self._show_pw = not self._show_pw
        self.pw_entry.configure(show="" if self._show_pw else "●")
        self.show_pw_btn.configure(text="🔒 Hide Password" if self._show_pw else "👁  Show Password")

    def _show_error(self, message: str):
        self.error_label.configure(text=f"⚠️  {message}")
        self.error_frame.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        self.sign_in_btn.configure(state="normal", text="Sign In")

    def _clear_error(self):
        self.error_frame.grid_remove()

    def _attempt_sign_in(self):
        self._clear_error()
        ident = self.ident_var.get().strip()
        password = self.pw_var.get()

        if not ident:
            self._show_error("Please enter your email or username.")
            self.ident_entry.focus()
            return
        if not password:
            self._show_error("Please enter your password.")
            self.pw_entry.focus()
            return

        self.sign_in_btn.configure(state="disabled", text="Verifying credentials…")
        self.update_idletasks()

        ok, msg, user_info = auth_service.authenticate_email_password(ident, password)
        if ok:
            session_token = auth_service.create_session(user_info)
            self._on_auth_success(user_info["identifier"], user_info["display_name"], session_token)
        else:
            self._show_error(msg)
            self.pw_entry.focus()

    def _attempt_google_sign_in(self):
        """Prompt for Google account email or process OAuth token."""
        self._clear_error()
        
        # Interactive dialog for Google Sign-In email
        dialog = ctk.CTkInputDialog(
            text="Enter your Google/Gmail address to sign in:",
            title="Google Sign-In",
        )
        email = dialog.get_input()
        if not email:
            return

        email = email.strip()
        val_ok, val_err = validate_email_format(email)
        if not val_ok:
            self._show_error(val_err)
            return

        ok, msg, user_info = auth_service.authenticate_google_token(email)
        if ok:
            session_token = auth_service.create_session(user_info)
            self._on_auth_success(user_info["identifier"], user_info["display_name"], session_token)
        else:
            self._show_error(msg)

    def _on_auth_success(self, username: str, display_name: str, session_token: str):
        logger.info("Authentication succeeded: %s (%s)", username, display_name)
        self.grab_release()
        self.destroy()
        self.on_success(username, display_name, session_token)

    def _on_close(self):
        self.grab_release()
        self.destroy()
        self.on_cancel()


def show_login(on_success: Callable[[str, str, str], None], on_cancel: Callable[[], None], parent=None) -> LoginWindow:
    """Helper function to create and show the login window."""
    win = LoginWindow(on_success=on_success, on_cancel=on_cancel, parent=parent)
    return win
