from flask import Blueprint, render_template, Response

views_bp = Blueprint("views", __name__)

@views_bp.route("/")
def index():
    return render_template("index.html")

@views_bp.route("/favicon.ico")
def favicon():
    # Return 204 No Content so browser favicon requests succeed cleanly without cluttering logs
    return Response(status=204)
