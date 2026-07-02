import zipfile
from pathlib import Path

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZIP_OUT = PROJECT_ROOT / "dist_web_upgrade.zip"

FILES_TO_PACKAGE = [
    # Refactored server entry
    "src/traffic_sign_system/interfaces/dashboard.py",
    
    # Pipeline core (with pause/resume support)
    "src/traffic_sign_system/vision/pipeline.py",
    
    # Python Blueprints
    "src/traffic_sign_system/interfaces/web/__init__.py",
    "src/traffic_sign_system/interfaces/web/blueprints/__init__.py",
    "src/traffic_sign_system/interfaces/web/blueprints/views.py",
    "src/traffic_sign_system/interfaces/web/blueprints/api.py",
    
    # Redesigned Dashboard View Template
    "src/traffic_sign_system/interfaces/web/templates/index.html",
    
    # Styling stylesheets
    "src/traffic_sign_system/interfaces/web/static/css/main.css",
    "src/traffic_sign_system/interfaces/web/static/css/variables.css",
    "src/traffic_sign_system/interfaces/web/static/css/layout.css",
    "src/traffic_sign_system/interfaces/web/static/css/components.css",
    "src/traffic_sign_system/interfaces/web/static/css/animations.css",
    
    # Modular JavaScript Files
    "src/traffic_sign_system/interfaces/web/static/js/app.js",
    "src/traffic_sign_system/interfaces/web/static/js/api.js",
    "src/traffic_sign_system/interfaces/web/static/js/socket.js",
    "src/traffic_sign_system/interfaces/web/static/js/charts.js",
    "src/traffic_sign_system/interfaces/web/static/js/ui.js",
]

def main():
    print(f"[Packager] Starting packaging process from project root: {PROJECT_ROOT}")
    
    with zipfile.ZipFile(ZIP_OUT, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for rel_path in FILES_TO_PACKAGE:
            full_path = PROJECT_ROOT / rel_path
            if full_path.exists():
                print(f" -> Adding file: {rel_path}")
                zip_file.write(full_path, arcname=rel_path)
            else:
                print(f" [WARNING] File not found, skipping: {rel_path}")
                
    print(f"[Packager] Successfully generated ZIP update package at: {ZIP_OUT}")

if __name__ == "__main__":
    main()
