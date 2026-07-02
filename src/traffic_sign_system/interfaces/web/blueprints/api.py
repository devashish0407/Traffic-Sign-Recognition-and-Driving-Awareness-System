import time
import uuid
from pathlib import Path
import cv2
import numpy as np
from flask import Blueprint, Response, current_app, jsonify, request, send_file, abort
from werkzeug.utils import secure_filename

from traffic_sign_system.paths import project_path
from traffic_sign_system.config.sign_classes import SIGN_LABELS, HAZARD_RULES

api_bp = Blueprint("api", __name__)

ALLOWED_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v", ".mpg", ".mpeg"}
MAX_UPLOAD_MB = 200

def get_placeholder_frame():
    """Generates a high-tech dark placeholder JPEG to avoid 404 errors when feed is idle."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Slate background color matching the dashboard theme
    img[:] = (26, 17, 13) 
    
    cv2.putText(img, "TRAFFIC LENS", (230, 210), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230, 180, 90), 2, cv2.LINE_AA)
    cv2.putText(img, "WAITING FOR STREAM INGEST", (170, 250), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1, cv2.LINE_AA)
    
    success, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes() if success else b""

@api_bp.route("/video_feed")
def video_feed():
    """Streams the real-time annotated camera or video frame stream."""
    pipeline = current_app.config["PIPELINE"]
    source = request.args.get("source")
    session_id = request.args.get("session_id")
    upload_dir = project_path("artifacts/uploads")
    
    if source:
        try:
            candidate = Path(source).resolve()
            upload_dir_resolved = upload_dir.resolve()
            
            candidate_str = str(candidate).lower()
            upload_dir_str = str(upload_dir_resolved).lower()
            
            if not candidate_str.startswith(upload_dir_str):
                abort(400)
            if not candidate.is_file():
                abort(404)
            source = str(candidate)
        except Exception:
            abort(400)

    def generate():
        for jpeg in pipeline.iter_frames(source=source, session_id=session_id):
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@api_bp.route("/api/frame")
def api_frame():
    """Returns a snapshot of the latest annotated frame or a placeholder if none is active."""
    pipeline = current_app.config["PIPELINE"]
    frame = pipeline._latest_annotated
    
    if frame is None:
        resp = Response(get_placeholder_frame(), mimetype="image/jpeg")
        resp.headers["Cache-Control"] = "no-cache, no-store"
        return resp
        
    success, buf = cv2.imencode(".jpg", frame)
    if not success:
        abort(500)
        
    resp = Response(buf.tobytes(), mimetype="image/jpeg")
    resp.headers["Cache-Control"] = "no-cache, no-store"
    return resp

@api_bp.route("/api/stats")
def api_stats():
    """Returns raw pipeline stats."""
    pipeline = current_app.config["PIPELINE"]
    return jsonify(pipeline.get_stats())

@api_bp.route("/api/summary")
def api_summary():
    """Returns the processed summary details for the current active/ended session."""
    pipeline = current_app.config["PIPELINE"]
    return jsonify(pipeline.get_session_summary())

@api_bp.route("/api/hazard_rules")
def api_hazard_rules():
    """Returns configured rules and alert messages mapped to classes."""
    rules = {}
    for cid, label in SIGN_LABELS.items():
        rule = HAZARD_RULES.get(cid, {"level": "info", "color": "#8890aa"})
        rules[str(cid)] = {
            "label": label,
            "level": rule.get("level", "info"),
            "color": rule.get("color", "#8890aa"),
            "message": rule.get("message", label),
            "action": rule.get("action", ""),
        }
    return jsonify({"rules": rules})

@api_bp.route("/api/upload", methods=["POST"])
def api_upload():
    """Processes uploaded video files up to 200MB for custom local inference runs."""
    video_file = request.files.get("video")
    if not video_file or not video_file.filename:
        return jsonify({"error": "No file provided"}), 400
        
    ext = Path(video_file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"Unsupported format: {ext}"}), 400
        
    upload_dir = project_path("artifacts/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = secure_filename(video_file.filename) or "video"
    destination = upload_dir / f"{uuid.uuid4().hex[:10]}_{safe_name}"
    video_file.save(destination)
    
    # Reset stats on backend to prevent race condition on start
    pipeline = current_app.config["PIPELINE"]
    pipeline._stats.update({
        "fps":          0.0,
        "frame_count":  0,
        "detections":   0,
        "current_dets": [],
        "stream_active": False,
        "video_ended":   False,
    })
    
    return jsonify({"source": str(destination), "filename": video_file.filename})

@api_bp.route("/api/download/csv")
def api_download_csv():
    """Retrieves the session log in CSV format for the active session or latest run."""
    pipeline = current_app.config["PIPELINE"]
    session_id = request.args.get("session_id")
    logs_dir = project_path(pipeline.cfg.get("paths", {}).get("logs", "artifacts/logs/"))
    
    if session_id:
        filename = f"session_{session_id}.csv"
        target_path = Path(logs_dir) / filename
        if target_path.is_file():
            return send_file(target_path, as_attachment=True, download_name=filename, mimetype="text/csv")
            
    csv_files = sorted(
        Path(logs_dir).glob("session_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not csv_files:
        return jsonify({"error": "No session log yet — start a stream first"}), 404
        
    latest = csv_files[0]
    return send_file(latest, as_attachment=True, download_name=latest.name, mimetype="text/csv")

@api_bp.app_errorhandler(413)
def file_too_large(_error):
    """Gracefully catch Payload Too Large errors and return JSON warning."""
    return jsonify({"error": f"Upload exceeds the maximum limit of {MAX_UPLOAD_MB} MB"}), 413

@api_bp.route("/api/stream/pause", methods=["POST"])
def stream_pause():
    """Pauses the active stream frame processing."""
    pipeline = current_app.config["PIPELINE"]
    pipeline.paused = True
    return jsonify({"status": "paused"})

@api_bp.route("/api/stream/resume", methods=["POST"])
def stream_resume():
    """Resumes the active stream frame processing."""
    pipeline = current_app.config["PIPELINE"]
    pipeline.paused = False
    return jsonify({"status": "resumed"})

@api_bp.route("/api/stream/stop", methods=["POST"])
def stream_stop():
    """Terminates active camera or video streams and resets stats."""
    pipeline = current_app.config["PIPELINE"]
    pipeline.running = False
    pipeline.paused = False
    pipeline._stats["stream_active"] = False
    pipeline._stats["video_ended"] = False
    pipeline._stats["frame_count"] = 0
    pipeline._stats["current_dets"] = []
    pipeline._last_alerts = []
    pipeline._latest_annotated = None
    return jsonify({"status": "stopped"})
