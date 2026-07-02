import time
import threading
from pathlib import Path
from flask import Flask
from flask_socketio import SocketIO
from traffic_sign_system.paths import project_path

MAX_UPLOAD_MB = 200
_here = Path(__file__).parent

def create_app(pipeline):
    """Configures Flask application, registers blueprints, and hooks SocketIO."""
    app = Flask(
        __name__,
        template_folder=str(_here / "web" / "templates"),
        static_folder=str(_here / "web" / "static"),
        static_url_path="/static",
    )
    
    app.config["SECRET_KEY"] = "tsr"
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
    app.config["PIPELINE"] = pipeline

    # Register modular route blueprints
    from traffic_sign_system.interfaces.web.blueprints.views import views_bp
    from traffic_sign_system.interfaces.web.blueprints.api import api_bp
    
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)

    # Disable session cookie to avoid 431 errors
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode="threading",
        manage_session=False,
        logger=False,
        engineio_logger=False,
        ping_timeout=60,
        ping_interval=25,
    )

    upload_dir = project_path("artifacts/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    def _emit_stats():
        """Broadcasts live pipeline telemetry to all connected socket clients."""
        while True:
            try:
                socketio.emit("stats", pipeline.get_stats())
            except Exception:
                pass
            time.sleep(0.25)

    threading.Thread(target=_emit_stats, daemon=True).start()
    
    return app, socketio

def run_dashboard(pipeline, host="0.0.0.0", port=5000):
    """Initializes and runs the web dashboard server."""
    app, socketio = create_app(pipeline)
    print(f"[Dashboard] Starting server on http://localhost:{port}")
    socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True)