from flask import Blueprint, render_template, Response, send_from_directory, current_app
import os

views_bp = Blueprint("views", __name__)

@views_bp.route("/")
def index():
    return render_template("index.html")

@views_bp.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(current_app.static_folder, "logo"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon"
    )
