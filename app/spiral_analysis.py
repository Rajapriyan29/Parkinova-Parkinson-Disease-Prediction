"""
spiral_analysis.py
==================
Spiral Drawing Analysis Engine for Parkinova Parkinson's Analysis Platform.

Features:
- Image validation (PNG, JPG, JPEG, BMP) with dimension and readability checks
- Drawing stroke presence verification (ensures valid non-blank drawing)
- Integration interface for trained spiral classification models (.keras, .h5, .tflite, .onnx, .pt)
- Honest, unmanipulated status reporting when a trained spiral model is pending:
  * No mock predictions or hardcoded diagnosis scores
  * Clear model information, visual characteristics, limitations, and recommendations
- Ready for hot-loading any trained spiral model dropped into models/
"""

import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger("parkinova.spiral")

SPIRAL_DISCLAIMER = (
    "Spiral Drawing Assessment Notice: Spiral analysis is an investigational neuromotor "
    "assessment aid used in Parkinson's research to study kinematic and motor stability patterns. "
    "A static 2D spiral image alone cannot independently confirm or exclude Parkinson's disease. "
    "Clinical diagnosis requires direct neurological evaluation, UPDRS motor scoring, and "
    "consultation with a movement disorder specialist."
)

ALLOWED_SPIRAL_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}
CANDIDATE_SPIRAL_MODELS = [
    r"C:\Users\Raj Priyan\Parkinson disease\runs\classify\Parkinson_YOLO26\Spiral_Classification-2\weights\best.pt",
    r"C:\Users\Raj Priyan\Parkinson disease\Parkinson-spiral-2000.keras",
    "models/Parkinson-spiral.keras",
    "models/spiral_model.keras",
    "models/spiral_model.h5",
    "models/spiral_model.tflite",
    "models/spiral_model.onnx",
    "models/spiral_model.pt",
    "models/spiral_cnn.keras",
]


def validate_spiral_image(image_path: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate that image exists, is readable, meets dimension requirements,
    and contains discernible drawing strokes.

    Returns
    -------
    (is_valid, error_message, observations_dict)
    """
    path = Path(image_path)
    if not path.exists():
        return False, f"Spiral image file not found: {image_path}", {}
    if not path.is_file():
        return False, f"Path is not a regular file: {image_path}", {}
    if path.stat().st_size == 0:
        return False, "Spiral image file is empty (0 bytes).", {}
    if path.suffix.lower() not in ALLOWED_SPIRAL_EXTS:
        return (
            False,
            f"Unsupported format '{path.suffix}'. Supported formats: PNG, JPG, JPEG, BMP.",
            {},
        )

    try:
        with Image.open(str(path)) as img:
            img.verify()
    except Exception as exc:
        return False, f"Image file is corrupted or cannot be decoded: {exc}", {}

    try:
        with Image.open(str(path)) as img:
            img_rgb = img.convert("RGB")
            w, h = img_rgb.size
            arr = np.array(img_rgb)
    except Exception as exc:
        return False, f"Failed to read image data: {exc}", {}

    if w < 64 or h < 64:
        return False, f"Image resolution ({w}x{h}) is too low for spiral analysis. Minimum 64x64 required.", {}

    # Check for stroke contrast / drawing presence
    # Convert to grayscale to check luminance variance
    gray = np.mean(arr, axis=2)
    std_dev = float(np.std(gray))
    min_val = float(np.min(gray))
    max_val = float(np.max(gray))
    range_val = max_val - min_val

    if range_val < 15.0 or std_dev < 3.0:
        return (
            False,
            "The uploaded image appears completely blank or uniform. Please upload a clear spiral drawing.",
            {},
        )

    # Calculate stroke pixel ratio
    # Typically spirals are dark strokes on light paper (or light strokes on dark tablet)
    mean_val = float(np.mean(gray))
    is_dark_bg = mean_val < 128.0
    if is_dark_bg:
        stroke_pixels = np.sum(gray > (mean_val + 20))
    else:
        stroke_pixels = np.sum(gray < (mean_val - 20))
    total_pixels = float(w * h)
    stroke_density = (stroke_pixels / total_pixels) * 100.0

    aspect_ratio = round(w / h, 3)

    observations = {
        "dimensions": f"{w} × {h} pixels",
        "aspect_ratio": f"{aspect_ratio}:1",
        "stroke_density_pct": round(stroke_density, 2),
        "canvas_style": "Dark background (digitized)" if is_dark_bg else "Light background (paper / digital canvas)",
        "contrast_range": round(range_val, 1),
        "file_size_kb": round(path.stat().st_size / 1024.0, 1),
    }

    return True, "", observations


import threading

class SpiralEngine:
    """
    Engine for spiral drawing evaluation and model execution.
    Inspects available models and provides a standardized prediction interface.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        if root_dir is None:
            if getattr(sys, "frozen", False):
                self.root_dir = Path(sys.executable).resolve().parent
            else:
                self.root_dir = Path(__file__).resolve().parent.parent
        else:
            self.root_dir = Path(root_dir)

        self.model = None
        self.model_path: Optional[str] = None
        self.model_info: Dict[str, Any] = {}
        self.model_loaded: bool = False
        self.load_error: Optional[str] = None
        self._loading: bool = False
        self._load_thread: Optional[threading.Thread] = None
        self._load_event = threading.Event()
        self._find_and_load_model_async()

    def _find_and_load_model_async(self):
        """Search for installed spiral analysis models and load asynchronously in background."""
        found_path = None
        for candidate in CANDIDATE_SPIRAL_MODELS:
            p = Path(candidate)
            if not p.is_absolute():
                p = self.root_dir / candidate
            if p.exists() and p.stat().st_size > 0:
                found_path = str(p.resolve())
                break

        if not found_path:
            logger.info("No trained spiral model file found in models/. Spiral engine is in interface standby mode.")
            self.model_loaded = False
            self.model_info = {
                "model_name": "Spiral Analysis Interface",
                "version": "1.0.0",
                "status": "Standby (Awaiting trained model file)",
                "description": "Interface ready for spiral neural network integration.",
            }
            self._load_event.set()
            return

        self.model_path = found_path
        self._loading = True
        self._load_thread = threading.Thread(
            target=self._background_load_worker,
            args=(found_path,),
            daemon=True,
            name="SpiralModelLoaderThread",
        )
        self._load_thread.start()

    def reload_model(self, model_path: str):
        """Reload or switch spiral model file dynamically at runtime."""
        self.model_path = model_path
        self.model_loaded = False
        self.load_error = None
        self._load_event.clear()
        self._loading = True
        self._load_thread = threading.Thread(
            target=self._background_load_worker,
            args=(model_path,),
            daemon=True,
            name="SpiralModelReloadThread",
        )
        self._load_thread.start()

    def _background_load_worker(self, model_path: str):
        """Background worker thread to load spiral model without blocking UI."""
        try:
            self.load_error = None
            self._load_spiral_model(model_path)
            self.load_error = None
        except Exception as exc:
            logger.warning("Failed to load spiral model from %s: %s", model_path, exc)
            self.model_loaded = False
            self.load_error = str(exc)
        finally:
            self._loading = False
            self._load_event.set()

    def ensure_model_loaded(self, timeout: float = 12.0) -> bool:
        """Wait for background loading to complete, or load synchronously if needed."""
        if self._load_thread and self._load_thread.is_alive():
            self._load_event.wait(timeout)
        elif not self.model_loaded and self.model_path and not self._loading:
            try:
                self._load_spiral_model(self.model_path)
            except Exception as exc:
                logger.warning("Failed to load spiral model from %s: %s", self.model_path, exc)
        return self.model_loaded

    def _load_spiral_model(self, model_path: str):
        """Load trained spiral classifier (Keras, TFLite, or YOLO .pt)."""
        p = Path(model_path)
        ext = p.suffix.lower()
        if ext in (".keras", ".h5"):
            model = None
            try:
                import keras
                model = keras.models.load_model(model_path, compile=False)
                logger.info("Loaded Keras spiral model via keras engine from %s", model_path)
            except Exception as k_err:
                logger.debug("keras.models.load_model failed (%s); trying tf.keras...", k_err)

            if model is None:
                import tensorflow as tf
                model = tf.keras.models.load_model(model_path, compile=False)
                logger.info("Loaded Keras spiral model via tf.keras engine from %s", model_path)

            self.model = model
            self.model_path = model_path
            self.model_loaded = True

            raw_in = getattr(self.model, "input_shape", None)
            if isinstance(raw_in, list):
                raw_in = raw_in[0]
            if raw_in is not None:
                spatial = [d for d in raw_in if d is not None]
                in_shape = tuple(spatial) if len(spatial) == 3 else (244, 244, 3)
            else:
                in_shape = (244, 244, 3)

            # Detect internal normalization / rescaling
            normalize_input = True
            for layer in getattr(self.model, "layers", [])[:3]:
                lname = layer.__class__.__name__.lower()
                if "rescaling" in lname or "normalization" in lname:
                    normalize_input = False
                    logger.info("Spiral model has internal %s layer. Preprocessor normalization disabled.", layer.__class__.__name__)
                    break

            raw_out = getattr(self.model, "output_shape", None)
            if isinstance(raw_out, list):
                raw_out = raw_out[0]
            num_classes = raw_out[-1] if raw_out is not None and len(raw_out) > 0 else 2

            self.model_info = {
                "model_name": p.stem,
                "version": "1.0.0",
                "input_shape": in_shape,
                "num_classes": num_classes,
                "normalize_input": normalize_input,
                "is_tflite": False,
                "is_yolo": False,
                "status": "Active (Model Loaded)",
            }
            logger.info("Loaded Keras spiral model from %s | input=%s | classes=%s", model_path, in_shape, num_classes)

        elif ext == ".tflite":
            import tensorflow as tf
            interpreter = tf.lite.Interpreter(model_path=model_path)
            interpreter.allocate_tensors()
            self.model = interpreter
            self.model_path = model_path
            self.model_loaded = True
            in_details = interpreter.get_input_details()
            out_details = interpreter.get_output_details()
            in_shape = tuple(in_details[0]["shape"][1:])
            num_classes = out_details[0]["shape"][-1] if out_details else 1
            self.model_info = {
                "model_name": p.stem,
                "version": "1.0.0",
                "input_shape": in_shape,
                "num_classes": num_classes,
                "normalize_input": False,
                "is_tflite": True,
                "is_yolo": False,
                "status": "Active (Model Loaded)",
            }
            logger.info("Loaded TFLite spiral model from %s", model_path)

        elif ext == ".pt":
            from ultralytics import YOLO
            yolo_model = YOLO(model_path)
            self.model = yolo_model
            self.model_path = model_path
            self.model_loaded = True
            # YOLO classify models accept any resolution; use 224 as default
            in_shape = (224, 224, 3)
            # Derive class count from model names if available
            names = getattr(yolo_model, "names", {})
            num_classes = len(names) if names else 2
            self.model_info = {
                "model_name": p.stem,
                "version": "1.0.0",
                "input_shape": in_shape,
                "num_classes": num_classes,
                "normalize_input": False,
                "is_tflite": False,
                "is_yolo": True,
                "class_names": names,
                "status": "Active (YOLO Model Loaded)",
            }
            logger.info("Loaded YOLO spiral model from %s | classes=%s", model_path, names)

    def analyze_spiral(self, image_path: str, patient_code: str = "") -> Dict[str, Any]:
        """
        Perform analysis on an uploaded spiral drawing.
        If a model is loaded, executes real model prediction.
        If no model is loaded, executes validation and structural observations without fabrication.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        is_valid, err_msg, observations = validate_spiral_image(image_path)

        if not is_valid:
            return {
                "success": False,
                "status": "Invalid Image",
                "error": err_msg,
                "image_path": image_path,
                "patient_code": patient_code,
                "timestamp": timestamp,
                "model_prediction": None,
                "observations": {},
                "model_info": self.model_info,
                "disclaimer": SPIRAL_DISCLAIMER,
            }

        # Ensure background model load has completed if in progress
        self.ensure_model_loaded(timeout=10.0)

        # If a trained model is loaded, run inference
        if self.model_loaded and self.model is not None:
            try:
                prediction, raw_score, obs, is_pd = self._run_model_inference(image_path, observations)
                return {
                    "success": True,
                    "status": "Completed (Model Prediction)",
                    "error": None,
                    "image_path": image_path,
                    "patient_code": patient_code,
                    "timestamp": timestamp,
                    "model_prediction": prediction,
                    "is_parkinson": is_pd,
                    "raw_score": raw_score,
                    "observations": obs,
                    "model_info": self.model_info,
                    "limitations": (
                        "Model-based spiral analysis represents pattern classification on isolated drawings. "
                        "Sensory, visual, or non-Parkinsonian tremors (essential tremor, dystonia) can produce "
                        "similar visual deviations. Static 2D sketches cannot independently confirm or exclude Parkinson's disease."
                    ),
                    "next_steps": (
                        "Correlate with clinical motor UPDRS examination and neurologist assessment. "
                        "Consider computerized tablet Archimedean spiral tracking with continuous pen velocity and pressure data."
                    ),
                    "disclaimer": SPIRAL_DISCLAIMER,
                }
            except Exception as exc:
                logger.exception("Spiral model inference failed: %s", exc)
                return {
                    "success": False,
                    "status": "Model Execution Error",
                    "error": f"Spiral model execution failed: {exc}",
                    "image_path": image_path,
                    "patient_code": patient_code,
                    "timestamp": timestamp,
                    "model_prediction": None,
                    "observations": observations,
                    "model_info": self.model_info,
                    "disclaimer": SPIRAL_DISCLAIMER,
                }

        # Model is NOT loaded — Interface Standby mode (No fabricated predictions)
        return {
            "success": True,
            "status": "Model Standby (Awaiting Trained Spiral Model File)",
            "error": None,
            "image_path": image_path,
            "patient_code": patient_code,
            "timestamp": timestamp,
            "model_prediction": "Standby — Integration Interface Ready (No fake score generated)",
            "raw_score": None,
            "observations": {
                "Image Geometry": observations.get("dimensions", "Verified"),
                "Aspect Ratio": observations.get("aspect_ratio", "1:1"),
                "Stroke Coverage": f"{observations.get('stroke_density_pct', 0)}% canvas coverage",
                "Canvas Surface": observations.get("canvas_style", "Standard"),
                "Stroke Contrast": f"{observations.get('contrast_range', 0)} greyscale range",
                "Validation Status": "Valid spiral drawing detected (non-blank, clear strokes)",
            },
            "model_info": {
                "name": "Parkinova Spiral Analysis Module",
                "status": "Integration Architecture Active",
                "model_file": "None (Place trained weights in models/spiral_model.keras)",
                "framework_support": "TensorFlow / Keras / TFLite / PyTorch",
            },
            "limitations": (
                "No trained spiral classification model is currently placed in the models/ folder. "
                "The application provides validated image ingestion, geometry verification, and "
                "reporting structure without fabricating clinical predictions. "
                "An ordinary spiral drawing image cannot independently diagnose Parkinson's disease."
            ),
            "next_steps": (
                "1. If a trained spiral classification weights file is available, place it in 'models/spiral_model.keras'.\n"
                "2. Conduct clinical UPDRS motor evaluation with a qualified neurologist.\n"
                "3. Use dynamic tablet-based digitizers for velocity and pressure tremor tracking if available."
            ),
            "disclaimer": SPIRAL_DISCLAIMER,
        }

    def _run_model_inference(self, image_path: str, base_obs: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any], bool]:
        """Preprocess and run actual model prediction (Keras, TFLite, or YOLO)."""
        target_shape = self.model_info.get("input_shape", (224, 224, 3))
        h, w = target_shape[0], target_shape[1]

        # ── YOLO classify inference ──────────────────────────────────────────
        if self.model_info.get("is_yolo", False):
            results = self.model.predict(source=image_path, imgsz=w, verbose=False)
            r = results[0]
            probs = r.probs          # ultralytics Probs object
            pred_idx = int(probs.top1)
            pd_prob = float(probs.data[1]) if hasattr(probs, "data") and len(probs.data) > 1 else float(probs.top1conf)
            score = pd_prob

            names = self.model_info.get("class_names", {})
            pred_label = names.get(pred_idx, str(pred_idx)).lower()

            # Map class name to PD / healthy outcome
            pd_keywords = ("parkinson", "pd", "patient", "spiral_patient")
            healthy_keywords = ("healthy", "control", "normal", "spiral_healthy")
            if any(k in pred_label for k in pd_keywords):
                spiral_is_pd = True
            elif any(k in pred_label for k in healthy_keywords):
                spiral_is_pd = False
            else:
                # Fall back: class index 1 → PD convention
                spiral_is_pd = pred_idx == 1

            if spiral_is_pd:
                pred = "Spiral drawing shows motor irregularities correlated with Parkinsonian tremor patterns"
            else:
                pred = "Spiral drawing exhibits regular trajectory without distinctive Parkinsonian tremor pattern"

            obs = dict(base_obs)
            obs["Model Status"] = f"YOLO Model Active ({self.model_info.get('model_name', 'best')})"
            obs["Input Resolution"] = f"{w}x{h} px"
            obs["Predicted Class"] = names.get(pred_idx, str(pred_idx))
            return pred, score, obs, spiral_is_pd

        # ── Keras / TFLite inference ─────────────────────────────────────────
        with Image.open(image_path) as img:
            rgb = img.convert("RGB")
            resized = rgb.resize((w, h), Image.LANCZOS)
            arr = np.array(resized, dtype=np.float32)
            if self.model_info.get("normalize_input", True):
                arr = arr / 255.0
            tensor = np.expand_dims(arr, axis=0)

        if self.model_info.get("is_tflite", False):
            in_det = self.model.get_input_details()
            out_det = self.model.get_output_details()
            self.model.set_tensor(in_det[0]["index"], tensor)
            self.model.invoke()
            raw_out = self.model.get_tensor(out_det[0]["index"])
        else:
            raw_out = self.model.predict(tensor, verbose=0)

        output = np.squeeze(raw_out)
        if output.ndim == 0 or (output.ndim == 1 and len(output) == 1):
            score = float(output)
            pred_idx = 1 if score >= 0.5 else 0
        else:
            flat = output.flatten()
            pred_idx = int(np.argmax(flat))
            score = float(flat[pred_idx])

        spiral_is_pd = (pred_idx == 1)
        if spiral_is_pd:
            pred = "Spiral drawing shows motor irregularities correlated with Parkinsonian tremor patterns"
        else:
            pred = "Spiral drawing exhibits regular trajectory without distinctive Parkinsonian tremor pattern"

        obs = dict(base_obs)
        obs["Model Status"] = f"Trained Model Active ({self.model_info.get('model_name', 'spiral_model')})"
        obs["Input Resolution"] = f"{w}x{h} px"
        obs["Raw Model Output"] = f"{score:.4f}"
        return pred, score, obs, spiral_is_pd


# Global instance
spiral_engine = SpiralEngine()
