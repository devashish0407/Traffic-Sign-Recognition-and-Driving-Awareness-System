"""Launch the real-time traffic sign recognition pipeline.

Usage:
    python scripts/run.py
    python scripts/run.py --mode dashboard
    python scripts/run.py --source assets/samples/test.mp4
    python scripts/run.py --mode dashboard --port 8080
"""

import argparse
from pathlib import Path
import sys

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from traffic_sign_system.paths import DEFAULT_CONFIG_PATH
from traffic_sign_system.vision.pipeline import RealtimePipeline


def load_config(path: str = None) -> dict:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Traffic sign recognition and hazard prediction system"
    )
    parser.add_argument(
        "--mode",
        choices=["window", "dashboard"],
        default="window",
        help="Output mode: OpenCV window or web dashboard",
    )
    parser.add_argument("--source", default=None, help="Video path or camera index")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    cfg = load_config(args.config)

    # 🔥 FORCE FP16 OFF (GLOBAL FIX)
    cfg.setdefault("inference", {})
    cfg["inference"]["fp16"] = False

    if args.source:
        cfg["inference"]["camera_index"] = args.source

    pipeline = RealtimePipeline(cfg)

    if args.mode == "dashboard":
        from traffic_sign_system.interfaces.dashboard import run_dashboard

        print(f"[Run] Starting dashboard at http://{args.host}:{args.port}")
        run_dashboard(pipeline, host=args.host, port=args.port)
    else:
        print("[Run] Starting OpenCV window. Press 'q' to quit.")
        pipeline.run()

if __name__ == "__main__":
    main()
