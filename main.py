"""
Parkinova — Parkinson's MRI Analysis System
main.py — Application entry point

Optimized architecture:
- Instant cold-start with lazy loading (TensorFlow imported only in background thread)
- Modern clinical light theme navigation sidebar and layout
- Secure session management with login and logout flows
- Multi-threaded background model loading with non-blocking status updates
- High-precision inference pipeline without confidence score displays
"""

import os
import sys
import time
import logging
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

_T0_START = time.perf_counter()

# ---------------------------------------------------------------------------
# Path setup (supports PyInstaller frozen executable)
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", ROOT_DIR))
else:
    ROOT_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = ROOT_DIR

sys.path.insert(0, str(ROOT_DIR))
if BUNDLE_DIR != ROOT_DIR:
    sys.path.insert(0, str(BUNDLE_DIR))

# ---------------------------------------------------------------------------
# Logging setup — writes to logs/app.log
# ---------------------------------------------------------------------------
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("parkinova.main")

# ---------------------------------------------------------------------------
# GUI imports (CustomTkinter)
# ---------------------------------------------------------------------------
try:
    import customtkinter as ctk
    from tkinter import messagebox, filedialog
except ImportError as exc:
    print(f"[FATAL] CustomTkinter is not installed: {exc}")
    print("Run: pip install customtkinter")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Lightweight imports (Heavy modules are lazy loaded)
# ---------------------------------------------------------------------------
from app.login import show_login
from app.auth import auth_service
from app.database import AnalysisDatabase

# ---------------------------------------------------------------------------
# Application Constants & Clinical Light Palette
# ---------------------------------------------------------------------------
APP_NAME = "Parkinova"
APP_SUBTITLE = "Parkinson's MRI Analysis Platform"
APP_VERSION = "2.0.0"

_CANDIDATE_MODELS = [
    r"C:\Users\Raj Priyan\Parkinson disease\Parkinson-2000.keras",
    str(ROOT_DIR / "models" / "Parkinson-2000.keras"),
    str(ROOT_DIR / "models" / "parkinson_cnn.keras"),
    str(ROOT_DIR / "models" / "parkinson_model.tflite"),
    str(BUNDLE_DIR / "models" / "parkinson_cnn.keras"),
]
DEFAULT_MODEL_PATH = next(
    (p for p in _CANDIDATE_MODELS if Path(p).exists()),
    r"C:\Users\Raj Priyan\Parkinson disease\Parkinson-2000.keras",
)

REPORTS_DIR = ROOT_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

NAV_ITEMS = [
    ("🏠  Dashboard", "dashboard"),
    ("📋  Patient Details", "patient_form"),
    ("📂  MRI Scans", "upload"),
    ("🌀  Spiral Analysis", "spiral"),
    ("📊  Assessment Report", "results"),
    ("🌿  Health & Lifestyle Guide", "lifestyle"),
    ("🖼️  Visualization", "visualization"),
    ("🗂️  History", "history"),
    ("⚙️  Settings", "settings"),
]

# Vintage Editorial Palette (Warm Cream, Deep Forest Green, Coral Red)
COLORS = {
    "bg": "#F5F0D8",               # Primary Background: Warm cream / vintage ivory
    "sidebar_bg": "#FFF9E9",       # Highlight Color: Warm off-white
    "nav_text": "#123F2D",         # Primary Text: Deep forest green
    "nav_selected_bg": "#EAE5CC",  # Subtle Background: Pale beige
    "nav_selected_text": "#123F2D",# Deep forest green
    "nav_accent": "#F0442E",       # Vibrant coral red accent
    "nav_hover": "#EAE5CC",        # Subtle background: Pale beige
    "border": "#B8C4A5",           # Border Color: Muted sage green
    "primary": "#F0442E",          # Accent Color: Vibrant coral red
    "primary_hover": "#D43823",    # Slightly darker coral
    "primary_text": "#FFF9E9",     # Warm off-white
    "secondary": "#EAE5CC",        # Subtle Pale beige
    "secondary_text": "#123F2D",   # Forest green
    "text_dark": "#123F2D",        # Primary Text: Deep forest green
    "text_muted": "#365747",       # Secondary Text: Muted dark green
    "success": "#123F2D",          # Forest green
    "warn": "#D77B65",             # Secondary Accent: Soft terracotta
    "error": "#F0442E",            # Coral red
}


# ===========================================================================
# Main Application Controller
# ===========================================================================
class ParkinovaApp(ctk.CTk):
    """
    Main application controller managing views, background CNN initialization,
    session state, and inference routing.
    """

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME} — {APP_SUBTITLE}")
        self.geometry("1300x820")
        self.minsize(1180, 750)
        self.configure(fg_color=COLORS["bg"])

        # ------------------------------------------------------------------
        # State
        # ------------------------------------------------------------------
        self.model_loaded: bool = False
        self.is_loading_model: bool = False
        self.model = None
        self.model_info: Dict[str, Any] = {}
        self.preprocessor = None
        self.inference_engine = None
        self.class_labels: list = []
        self._model_path: str = DEFAULT_MODEL_PATH

        self.current_image_path: str = ""
        self.current_result: Dict[str, Any] = {}
        self.current_spiral_result: Optional[Dict[str, Any]] = None
        self.current_analysis_id: str = ""
        self.current_patient_code: str = ""
        self.patient_data: Dict[str, Any] = {}

        self.logged_in_user: str = ""
        self.logged_in_display: str = ""
        self.session_token: str = ""

        self._frames: Dict[str, ctk.CTkFrame] = {}
        self._frames_built: bool = False
        self._current_frame_key: str = ""

        # ------------------------------------------------------------------
        # Local Database
        # ------------------------------------------------------------------
        try:
            self.db = AnalysisDatabase()
        except Exception as exc:
            logger.error(f"Failed to initialize database: {exc}")
            self.db = None

        # Lazy services
        self._report_generator = None

        # Start loading CNN in background immediately (single thread)
        self._load_model_async(DEFAULT_MODEL_PATH)

        # Withdraw root window so login screen appears FIRST
        self.withdraw()

        # Pre-build basic frame structure in background while window is withdrawn
        self._build_layout()
        self._build_nav()
        self._build_frames()
        self._frames_built = True

        # Center main window on screen ready for post-login presentation
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - 1300) // 2)
        y = max(0, (sh - 820) // 2)
        self.geometry(f"1300x820+{x}+{y}")

        # Show login screen FIRST
        self._show_login_screen()

        logger.info(f"Parkinova desktop application initialized in {time.perf_counter() - _T0_START:.3f} s; login presented first")

    # -----------------------------------------------------------------------
    # Authentication & Session Handling
    # -----------------------------------------------------------------------

    def _show_login_screen(self):
        """Display standalone clinical login window in front of main window."""
        self._login_win = show_login(
            on_success=self._on_login_success,
            on_cancel=self._on_login_cancel,
            parent=self,
        )

    def _on_login_success(self, username: str, display_name: str, session_token: str):
        """Invoked upon successful authentication."""
        t_login_start = time.perf_counter()
        self.logged_in_user = username
        self.logged_in_display = display_name
        self.session_token = session_token
        logger.info(f"User signed in: {username} ({display_name})")

        if not self._frames_built:
            self._build_layout()
            self._build_nav()
            self._build_frames()
            self._frames_built = True

        self._update_nav_user()
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(350, lambda: self.attributes("-topmost", False))
        self.focus_force()
        self.navigate_to("dashboard")

        post_login_ms = (time.perf_counter() - t_login_start) * 1000.0
        logger.info(f"Dashboard presented in {post_login_ms:.2f} ms after login")

        # Cooperatively preload remaining frames in background after main page is visible
        self.after(500, self._preload_next_frame)

    def _on_login_cancel(self):
        """User dismissed login window."""
        logger.info("Login dismissed.")
        if not self.logged_in_user:
            self.destroy()
            sys.exit(0)

    def logout(self):
        """End current user session and display sign-in window."""
        if self.session_token:
            auth_service.logout_session(self.session_token)
            self.session_token = ""
        self.logged_in_user = ""
        self.logged_in_display = ""
        self.withdraw()
        self._show_login_screen()

    # -----------------------------------------------------------------------
    # Layout and Navigation
    # -----------------------------------------------------------------------

    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)  # fixed width sidebar
        self.grid_columnconfigure(1, weight=1)  # expandable content

    def _build_nav(self):
        """Build the left navigation sidebar in clinical light style."""
        self.nav_frame = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=0,
            fg_color=COLORS["sidebar_bg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        self.nav_frame.grid(row=0, column=0, sticky="nsew")
        self.nav_frame.grid_rowconfigure(len(NAV_ITEMS) + 4, weight=1)
        self.nav_frame.grid_propagate(False)

        # App branding header
        nav_header = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        nav_header.grid(row=0, column=0, padx=16, pady=(24, 4), sticky="w")

        candidates = [
            BUNDLE_DIR / "assets" / "logo_circle.png",
            ROOT_DIR / "assets" / "logo_circle.png",
            BUNDLE_DIR / "assets" / "logo.png",
            ROOT_DIR / "assets" / "logo.png",
        ]
        logo_path = next((p for p in candidates if p.exists()), None)
        self._nav_logo_img = None
        if logo_path:
            try:
                from PIL import Image
                _pil = Image.open(str(logo_path)).resize((30, 30), Image.LANCZOS)
                self._nav_logo_img = ctk.CTkImage(light_image=_pil, dark_image=_pil, size=(30, 30))
                ctk.CTkLabel(nav_header, image=self._nav_logo_img, text="").pack(side="left", padx=(0, 8))
            except Exception:
                ctk.CTkLabel(nav_header, text="🧠", font=ctk.CTkFont(size=22)).pack(side="left", padx=(0, 8))
        else:
            ctk.CTkLabel(nav_header, text="🧠", font=ctk.CTkFont(size=22)).pack(side="left", padx=(0, 8))

        logo_label = ctk.CTkLabel(
            nav_header,
            text=APP_NAME,
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLORS["text_dark"],
        )
        logo_label.pack(side="left")

        version_label = ctk.CTkLabel(
            self.nav_frame,
            text=f"v{APP_VERSION}  ·  Research Edition",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLORS["text_muted"],
        )
        version_label.grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")

        # Navigation buttons
        self._nav_buttons: Dict[str, ctk.CTkButton] = {}
        for idx, (label, key) in enumerate(NAV_ITEMS):
            btn = ctk.CTkButton(
                self.nav_frame,
                text=label,
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                hover_color=COLORS["nav_hover"],
                text_color=COLORS["nav_text"],
                font=ctk.CTkFont(family="Segoe UI", size=13),
                command=lambda k=key: self.navigate_to(k),
            )
            btn.grid(row=idx + 2, column=0, padx=12, pady=3, sticky="ew")
            self._nav_buttons[key] = btn

        # Spacer row
        spacer_row = len(NAV_ITEMS) + 2
        self.nav_frame.grid_rowconfigure(spacer_row, weight=1)

        # Bottom info card (User session, model status & logout)
        bottom_frame = ctk.CTkFrame(self.nav_frame, fg_color="#EAE5CC", corner_radius=8, border_width=1, border_color=COLORS["border"])
        bottom_frame.grid(row=spacer_row + 1, column=0, padx=12, pady=(0, 16), sticky="ew")

        self.nav_user_label = ctk.CTkLabel(
            bottom_frame,
            text="👤  Dr. Researcher",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLORS["text_dark"],
            anchor="w",
        )
        self.nav_user_label.pack(fill="x", padx=10, pady=(8, 2))

        self.nav_model_status = ctk.CTkLabel(
            bottom_frame,
            text="● Model Loading…",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=COLORS["warn"],
            anchor="w",
        )
        self.nav_model_status.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkButton(
            bottom_frame,
            text="Sign Out",
            height=26,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#FDF0EE",
            border_width=1,
            border_color="#F8C0B8",
            text_color=COLORS["error"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self.logout,
        ).pack(fill="x", padx=10, pady=(0, 8))

    def _update_nav_user(self):
        if hasattr(self, "nav_user_label"):
            disp = self.logged_in_display or self.logged_in_user or "Researcher"
            self.nav_user_label.configure(text=f"👤  {disp[:18]}")

    def _build_frames(self):
        """Construct content area and initial landing screen (dashboard) lazily."""
        self.content_area = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["bg"])
        self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        # Lazy frame factories: imported and constructed on-demand
        self._frame_factories = {
            "patient_form": self._create_patient_form_frame,
            "upload": self._create_upload_frame,
            "spiral": self._create_spiral_frame,
            "results": self._create_results_frame,
            "lifestyle": self._create_lifestyle_frame,
            "visualization": self._create_visualization_frame,
            "history": self._create_history_frame,
            "settings": self._create_settings_frame,
        }

        # Build initial landing frame (dashboard) immediately
        from app.dashboard import DashboardFrame
        dash_frame = DashboardFrame(self.content_area, app_controller=self)
        dash_frame.grid(row=0, column=0, sticky="nsew")
        self._frames["dashboard"] = dash_frame

        # Cooperative idle preload queue (loaded in background after dashboard is visible)
        self._preload_queue = [
            "upload",
            "patient_form",
            "spiral",
            "results",
            "lifestyle",
            "visualization",
            "history",
            "settings",
        ]

    def _create_patient_form_frame(self):
        from app.patient_form import PatientFormFrame
        return PatientFormFrame(self.content_area, app_controller=self)

    def _create_upload_frame(self):
        from app.upload import UploadFrame
        return UploadFrame(self.content_area, app_controller=self)

    def _create_spiral_frame(self):
        from app.spiral import SpiralFrame
        return SpiralFrame(self.content_area, app_controller=self)

    def _create_results_frame(self):
        from app.results import ResultsFrame
        return ResultsFrame(self.content_area, app_controller=self)

    def _create_lifestyle_frame(self):
        from app.lifestyle import LifestyleFrame
        return LifestyleFrame(self.content_area, app_controller=self)

    def _create_visualization_frame(self):
        from app.visualization import VisualizationFrame
        return VisualizationFrame(self.content_area, app_controller=self)

    def _create_history_frame(self):
        from app.history import HistoryFrame
        return HistoryFrame(self.content_area, app_controller=self)

    def _create_settings_frame(self):
        from app.settings import SettingsFrame
        return SettingsFrame(self.content_area, app_controller=self)

    def _get_or_create_frame(self, key: str):
        """Retrieve existing frame or instantiate it lazily on demand."""
        if key in self._frames:
            return self._frames[key]
        return self._instantiate_frame(key)

    def _instantiate_frame(self, key: str):
        """Instantiate a frame on demand from the registry."""
        if key in self._frames:
            return self._frames[key]

        factory = getattr(self, "_frame_factories", {}).get(key)
        if not factory:
            return None

        try:
            frame = factory()
            frame.grid(row=0, column=0, sticky="nsew")
            self._frames[key] = frame
            if hasattr(self, "_preload_queue") and key in self._preload_queue:
                self._preload_queue.remove(key)
            return frame
        except Exception as exc:
            logger.error(f"Failed to construct frame '{key}': {exc}")
            traceback.print_exc()
            return None

    def _preload_next_frame(self):
        """Cooperatively preload non-essential frames during idle time."""
        if not hasattr(self, "_preload_queue") or not self._preload_queue:
            return
        if not self.logged_in_user:
            return

        next_key = self._preload_queue.pop(0)
        if next_key not in self._frames:
            self._instantiate_frame(next_key)
            # Ensure the currently active frame remains raised on top
            if hasattr(self, "_current_frame_key") and self._current_frame_key in self._frames:
                self._frames[self._current_frame_key].tkraise()

        if self._preload_queue:
            self.after(150, self._preload_next_frame)

    def navigate_to(self, key: str):
        """Navigate to specific screen with authentication verification and lazy loading."""
        if not self.session_token or not self.logged_in_user:
            logger.warning("Blocked unauthenticated navigation attempt to '%s'", key)
            return

        frame = self._get_or_create_frame(key)
        if not frame:
            return

        for nav_key, btn in self._nav_buttons.items():
            if nav_key == key:
                btn.configure(
                    fg_color=COLORS["nav_selected_bg"],
                    text_color=COLORS["nav_selected_text"],
                    border_width=1,
                    border_color=COLORS["nav_accent"],
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLORS["nav_text"],
                    border_width=0,
                )

        frame.tkraise()
        self._current_frame_key = key

        if hasattr(frame, "refresh"):
            try:
                frame.refresh()
            except Exception as e:
                logger.warning("Frame refresh error on %s: %s", key, e)

    # -----------------------------------------------------------------------
    # Background Model Preloading & Lifecycle
    # -----------------------------------------------------------------------

    def _load_model_async(self, model_path: str):
        """Load model in background daemon thread."""
        if getattr(self, "is_loading_model", False):
            logger.info("Model load already in progress; ignoring duplicate request for '%s'", model_path)
            return
        self.is_loading_model = True
        thread = threading.Thread(
            target=self._load_model_worker,
            args=(model_path,),
            daemon=True,
            name="ModelLoaderThread",
        )
        thread.start()

    def _load_model_worker(self, model_path: str):
        """Worker thread for model loading."""
        t_start = time.perf_counter()
        try:
            logger.info("Background thread loading model from: %s", model_path)
            from utils.model_loader import ModelLoader
            from utils.preprocessing import ImagePreprocessor
            from app.inference import InferenceEngine

            loader = ModelLoader()
            model, info = loader.load_model(model_path)
            labels = loader.get_class_labels(info["num_classes"])

            input_shape = info.get("input_shape", (244, 244, 3))
            normalize = info.get("normalize_input", False)

            preprocessor = ImagePreprocessor(input_shape=input_shape, normalize=normalize)
            engine = InferenceEngine(
                model=model,
                model_info=info,
                preprocessor=preprocessor,
                class_labels=labels,
            )

            load_time = time.perf_counter() - t_start
            logger.info(f"Model successfully initialized in {load_time:.2f} s")

            try:
                self.after(
                    0,
                    lambda: self._on_model_loaded(model, info, preprocessor, engine, labels),
                )
            except Exception:
                pass
        except Exception as exc:
            logger.error(f"Background model loading failed: {exc}")
            try:
                self.after(0, lambda: self._on_model_load_error(str(exc)))
            except Exception:
                pass
        finally:
            self.is_loading_model = False

    def _on_model_loaded(self, model, info, preprocessor, engine, labels):
        self.model = model
        self.model_info = info
        self.preprocessor = preprocessor
        self.inference_engine = engine
        self.class_labels = labels
        self.model_loaded = True
        self.is_loading_model = False

        if hasattr(self, "nav_model_status"):
            self.nav_model_status.configure(
                text="● CNN Model Ready",
                text_color=COLORS["success"],
            )

        # Notify dashboard and upload frames
        for key in ("dashboard", "upload", "settings"):
            if key in self._frames and hasattr(self._frames[key], "refresh"):
                try:
                    self._frames[key].refresh()
                except Exception:
                    pass

    def _on_model_load_error(self, err_msg: str):
        self.model_loaded = False
        self.is_loading_model = False
        if hasattr(self, "nav_model_status"):
            self.nav_model_status.configure(
                text="● Model Offline",
                text_color=COLORS["error"],
            )
        logger.warning("Application running in offline mode (no model loaded)")

    def reload_model(self, new_path: str):
        """User triggered model reload from Settings."""
        self._model_path = new_path
        self.is_loading_model = False
        self._load_model_async(new_path)

    # -----------------------------------------------------------------------
    # Analysis & Inference Coordination
    # -----------------------------------------------------------------------

    def set_current_image(self, path: str):
        self.current_image_path = path

    def set_patient_data(self, data: dict):
        self.patient_data = data
        self.current_patient_code = data.get("patient_code", "")

    def set_spiral_result(self, res: dict):
        self.current_spiral_result = res

    def run_analysis(self, image_path: str, patient_code: str = ""):
        """Trigger analysis with background thread processing."""
        if not self.model_loaded or self.inference_engine is None:
            messagebox.showerror(
                "Model Not Initialized",
                "The CNN model is still loading or could not be found.\n"
                "Please verify models/parkinson_cnn.keras exists.",
            )
            return

        self.current_image_path = image_path
        self.current_patient_code = patient_code

        upload_frame = self._get_or_create_frame("upload")
        if upload_frame and hasattr(upload_frame, "set_loading"):
            upload_frame.set_loading(True)

        def worker():
            t_inf_start = time.perf_counter()
            try:
                result = self.inference_engine.analyze(image_path)
                latency = time.perf_counter() - t_inf_start
                logger.info("Inference completed in %.3f s", latency)
                result["latency_sec"] = latency
                self.after(0, lambda: self._on_analysis_complete(result))
            except Exception as exc:
                logger.exception("Inference error: %s", exc)
                self.after(0, lambda: self._on_analysis_error(str(exc)))

        threading.Thread(target=worker, daemon=True, name="InferenceWorker").start()

    def _on_analysis_complete(self, result: Dict[str, Any]):
        upload_frame = self._get_or_create_frame("upload")
        if upload_frame and hasattr(upload_frame, "set_loading"):
            upload_frame.set_loading(False)

        if not result.get("success", False):
            err = result.get("error", "Unknown inference error.")
            messagebox.showerror("Evaluation Error", f"Analysis could not be completed:\n\n{err}")
            return

        result["image_path"] = self.current_image_path
        result["patient_code"] = self.current_patient_code
        self.current_result = result

        # Save record to database
        analysis_id = self._save_analysis_to_db(result)
        self.current_analysis_id = analysis_id

        # Update Results View
        results_frame = self._get_or_create_frame("results")
        if results_frame and hasattr(results_frame, "display_result"):
            results_frame.display_result(result, analysis_id, self.current_patient_code)

        # Update Visualization View
        viz_frame = self._get_or_create_frame("visualization")
        if viz_frame and hasattr(viz_frame, "display_images"):
            viz_frame.display_images(
                result.get("original_array"),
                result.get("preprocessed_array"),
                result.get("preprocessing_info", {}),
            )

        self.navigate_to("results")

    def _on_analysis_error(self, err_msg: str):
        upload_frame = self._get_or_create_frame("upload")
        if upload_frame and hasattr(upload_frame, "set_loading"):
            upload_frame.set_loading(False)
        messagebox.showerror("Analysis Error", f"An unexpected error occurred during analysis:\n\n{err_msg}")

    def _save_analysis_to_db(self, result: Dict[str, Any]) -> str:
        if not self.db:
            import uuid
            return str(uuid.uuid4())

        record = {
            "patient_code": self.current_patient_code,
            "image_filename": Path(self.current_image_path).name,
            "image_path": self.current_image_path,
            "predicted_class": result.get("predicted_class", ""),
            "model_scores": {"raw_score": result.get("raw_score", 0.0)},
            "model_version": APP_VERSION,
            "model_name": self.model_info.get("model_name", "parkinson_cnn"),
            "input_shape": str(self.model_info.get("input_shape", "(244, 244, 3)")),
            "preprocessing_info": result.get("preprocessing_info", {}),
            "patient_data": self.patient_data,
            "spiral_data": self.current_spiral_result,
            "logged_in_user": self.logged_in_user or "anonymous",
        }
        try:
            return self.db.save_analysis(record)
        except Exception as exc:
            logger.error("Failed to save record to SQLite: %s", exc)
            import uuid
            return str(uuid.uuid4())

    def generate_report(self, result: dict, analysis_id: str, patient_code: str) -> bool:
        """Export PDF report."""
        if self._report_generator is None:
            from app.reports import ReportGenerator
            self._report_generator = ReportGenerator()

        default_name = f"Parkinova_Report_{analysis_id[:8]}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        save_path = filedialog.asksaveasfilename(
            title="Export Clinical PDF Report",
            defaultextension=".pdf",
            initialdir=str(REPORTS_DIR),
            initialfile=default_name,
            filetypes=[("PDF Documents", "*.pdf")],
        )
        if not save_path:
            return False

        include_image = messagebox.askyesno(
            "Include Scan Image",
            "Embed the brain MRI scan thumbnail in the exported PDF report?",
        )

        try:
            ok = self._report_generator.generate_combined_report(
                mri_result=result,
                spiral_result=self.current_spiral_result,
                analysis_id=analysis_id,
                patient_code=patient_code,
                include_images=include_image,
                save_path=save_path,
                patient_data=self.patient_data,
            )
            if ok:
                messagebox.showinfo("Report Exported", f"PDF report saved successfully to:\n{save_path}")
                try:
                    import subprocess
                    subprocess.Popen(["explorer", "/select,", save_path.replace("/", "\\")])
                except Exception:
                    pass
                return True
            else:
                messagebox.showerror("Export Failed", "Failed to compile PDF report. See logs/app.log.")
                return False
        except Exception as e:
            messagebox.showerror("Export Error", f"Report generation failed: {e}")
            return False

    def on_closing(self):
        """Clean shutdown."""
        if self.db:
            try:
                self.db.close()
            except Exception:
                pass
        self.destroy()


def main():
    """Application entry point."""
    if "--server" in sys.argv:
        # Launch Mobile / Web server
        from server import start_server
        start_server()
        return

    logger.info(f"Launching {APP_NAME} v{APP_VERSION}")
    app = ParkinovaApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
