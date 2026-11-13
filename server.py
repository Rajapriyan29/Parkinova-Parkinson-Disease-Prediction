"""
server.py
=========
Web Server & Mobile API for Parkinova.
Serves:
- Responsive mobile & desktop healthcare research web app
- REST API for Android/iOS mobile devices and Flutter integration
- Local network testing with automated IP discovery
- Secure authenticated endpoints with session management
"""

import os
import sys
import socket
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from app.auth import auth_service
from app.database import AnalysisDatabase
from utils.model_loader import ModelLoader
from utils.preprocessing import ImagePreprocessor
from app.inference import InferenceEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("parkinova.server")

app = Flask(__name__, static_folder="web")
CORS(app)

# Global model state
_MODEL = None
_MODEL_INFO = {}
_PREPROCESSOR = None
_INFERENCE_ENGINE = None
_DB = None


def get_local_ip() -> str:
    """Detect machine's local network IP for phone connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def init_engine():
    """Load model and initialize inference engine once."""
    global _MODEL, _MODEL_INFO, _PREPROCESSOR, _INFERENCE_ENGINE, _DB
    if _INFERENCE_ENGINE is not None:
        return

    _DB = AnalysisDatabase()

    model_candidates = [
        Path(r"C:\Users\Raj Priyan\Parkinson disease\Parkinson-2000.keras"),
        ROOT_DIR / "models" / "Parkinson-2000.keras",
        ROOT_DIR / "models" / "parkinson_cnn.keras",
        ROOT_DIR / "models" / "parkinson_model.tflite",
    ]
    model_path = next((str(p) for p in model_candidates if p.exists()), str(model_candidates[0]))
    logger.info("Initializing server model from: %s", model_path)

    loader = ModelLoader()
    _MODEL, _MODEL_INFO = loader.load_model(model_path)
    labels = loader.get_class_labels(_MODEL_INFO["num_classes"])

    input_shape = _MODEL_INFO.get("input_shape", (244, 244, 3))
    normalize = _MODEL_INFO.get("normalize_input", False)

    _PREPROCESSOR = ImagePreprocessor(input_shape=input_shape, normalize=normalize)
    _INFERENCE_ENGINE = InferenceEngine(
        model=_MODEL,
        model_info=_MODEL_INFO,
        preprocessor=_PREPROCESSOR,
        class_labels=labels,
    )
    logger.info("Server inference engine initialized.")


# ---------------------------------------------------------------------------
# Static Web Assets (Mobile Frontend)
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    if os.path.exists(os.path.join("web", path)):
        return send_from_directory("web", path)
    if os.path.exists(os.path.join(ROOT_DIR, path)):
        return send_from_directory(ROOT_DIR, path)
    return send_from_directory("web", "index.html")


# ---------------------------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email_or_user = data.get("email_or_user", "")
    password = data.get("password", "")

    ok, msg, user_info = auth_service.authenticate_email_password(email_or_user, password)
    if not ok:
        return jsonify({"success": False, "message": msg}), 401

    token = auth_service.create_session(user_info)
    return jsonify({
        "success": True,
        "token": token,
        "user": user_info,
        "message": "Login successful.",
    })


@app.route("/api/auth/google", methods=["POST"])
def api_google_login():
    data = request.get_json() or {}
    token_or_email = data.get("token_or_email", "")

    ok, msg, user_info = auth_service.authenticate_google_token(token_or_email)
    if not ok:
        return jsonify({"success": False, "message": msg}), 401

    token = auth_service.create_session(user_info)
    return jsonify({
        "success": True,
        "token": token,
        "user": user_info,
        "message": "Google Sign-In successful.",
    })


# ---------------------------------------------------------------------------
# Inference & Analysis API (Without Confidence Scores)
# ---------------------------------------------------------------------------

@app.route("/api/status", methods=["GET"])
def api_status():
    init_engine()
    return jsonify({
        "status": "online",
        "app": "Parkinova",
        "version": "2.0.0",
        "model_loaded": _INFERENCE_ENGINE is not None,
        "model_name": _MODEL_INFO.get("model_name", "parkinson_cnn"),
        "input_shape": _MODEL_INFO.get("input_shape"),
    })


@app.route("/api/predict", methods=["POST"])
def api_predict():
    init_engine()

    # Optional bearer auth check
    auth_header = request.headers.get("Authorization", "")
    user_identifier = "mobile_user"
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        valid, user = auth_service.validate_session(token)
        if valid and user:
            user_identifier = user.get("identifier", "mobile_user")

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No image file provided."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    patient_code = request.form.get("patient_code", "")

    # Save to temporary upload file
    temp_dir = ROOT_DIR / "data" / "uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"upload_{datetime.now():%Y%m%d_%H%M%S}_{file.filename}"
    file.save(str(temp_path))

    try:
        result = _INFERENCE_ENGINE.analyze(str(temp_path))
        if not result.get("success"):
            return jsonify({"success": False, "error": result.get("error")}), 422

        # Record into database
        record = {
            "patient_code": patient_code,
            "image_filename": file.filename,
            "image_path": str(temp_path),
            "predicted_class": result.get("predicted_class"),
            "model_scores": {"raw_score": result.get("raw_score", 0.0)},
            "model_version": "2.0.0",
            "model_name": _MODEL_INFO.get("model_name", "parkinson_cnn"),
            "input_shape": str(_MODEL_INFO.get("input_shape", "(244, 244, 3)")),
            "preprocessing_info": result.get("preprocessing_info", {}),
            "patient_data": None,
            "logged_in_user": user_identifier,
        }
        analysis_id = _DB.save_analysis(record)

        # Return results without confidence score numbers or percentages
        return jsonify({
            "success": True,
            "analysis_id": analysis_id,
            "predicted_class": result.get("predicted_class"),
            "predicted_index": result.get("predicted_index"),
            "explanation": result.get("explanation"),
            "disclaimer": result.get("disclaimer"),
            "timestamp": result.get("analysis_timestamp"),
            "filename": file.filename,
        })
    except Exception as exc:
        logger.exception("Prediction failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Spiral Analysis API
# ---------------------------------------------------------------------------

@app.route("/api/spiral/predict", methods=["POST"])
def api_spiral_predict():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No spiral image file provided."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    patient_code = request.form.get("patient_code", "")

    temp_dir = ROOT_DIR / "data" / "uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"spiral_{datetime.now():%Y%m%d_%H%M%S}_{file.filename}"
    file.save(str(temp_path))

    try:
        from app.spiral_analysis import spiral_engine
        res = spiral_engine.analyze_spiral(str(temp_path), patient_code)
        res["filename"] = file.filename
        res["image_url"] = f"/data/uploads/{temp_path.name}"
        return jsonify(res)
    except Exception as exc:
        logger.exception("Spiral analysis failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Health & Lifestyle Guide API
# ---------------------------------------------------------------------------

@app.route("/api/lifestyle/guide", methods=["GET"])
def api_lifestyle_guide():
    diet = request.args.get("diet", "vegetarian")
    concern = request.args.get("concern", "general")
    cuisine = request.args.get("cuisine", "all")
    try:
        from app.lifestyle_data import get_personalized_lifestyle_guide
        guide = get_personalized_lifestyle_guide(diet, cuisine, concern)
        return jsonify({"success": True, "guide": guide})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Assessment Report PDF Generation API
# ---------------------------------------------------------------------------

@app.route("/api/report/export_pdf", methods=["POST"])
def api_report_export_pdf():
    init_engine()
    data = request.get_json() or {}
    mri_result = data.get("mri_result") or {}
    spiral_result = data.get("spiral_result")
    patient_data = data.get("patient_data")
    patient_code = data.get("patient_code", "")
    analysis_id = data.get("analysis_id", f"REP-{datetime.now():%Y%m%d%H%M%S}")

    reports_dir = ROOT_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"Parkinova_Report_{analysis_id[:8]}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    out_path = reports_dir / out_name

    try:
        from app.reports import ReportGenerator
        rg = ReportGenerator()
        ok = rg.generate_combined_report(
            mri_result=mri_result,
            spiral_result=spiral_result,
            analysis_id=analysis_id,
            patient_code=patient_code,
            include_images=True,
            save_path=str(out_path),
            patient_data=patient_data,
        )
        if ok:
            return jsonify({
                "success": True,
                "filename": out_name,
                "download_url": f"/reports/{out_name}",
            })
        return jsonify({"success": False, "error": "Report compilation failed."}), 500
    except Exception as exc:
        logger.exception("PDF export failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


# ---------------------------------------------------------------------------
# History API
# ---------------------------------------------------------------------------

@app.route("/api/history", methods=["GET"])
def api_history():
    init_engine()
    try:
        records = _DB.get_recent_analyses(limit=50)
        formatted = []
        for r in records:
            formatted.append({
                "id": r.get("id"),
                "image_filename": r.get("image_filename"),
                "predicted_class": r.get("predicted_class"),
                "patient_code": r.get("patient_code"),
                "created_at": r.get("created_at"),
            })
        return jsonify({"success": True, "analyses": formatted})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/history/<analysis_id>", methods=["DELETE"])
def api_delete_history(analysis_id):
    init_engine()
    try:
        ok = _DB.delete_analysis(analysis_id)
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def start_server(host="0.0.0.0", port=5000):
    """Run Flask server."""
    local_ip = get_local_ip()
    print("=" * 64)
    print("  PARKINOVA - CLINICAL MRI ANALYSIS PLATFORM")
    print("=" * 64)
    print(f"Desktop Access:   http://localhost:{port}")
    print(f"Mobile Access:    http://{local_ip}:{port}")
    print("=" * 64)
    print("Open this on your Android or iPhone connected to the same Wi-Fi:")
    print(f"Direct Mobile URL: http://{local_ip}:{port}")
    print("=" * 64)

    init_engine()
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    start_server()
