"""Evaluate the trained YOLO detector when validation data is available."""

import argparse
from pathlib import Path
import sys

import torch
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from traffic_sign_system.paths import DEFAULT_CONFIG_PATH, project_path
from traffic_sign_system.vision.preprocessor import load_config


def main():
    parser = argparse.ArgumentParser(description="Evaluate YOLO detector metrics.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--data", default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    weights = project_path(cfg["paths"]["yolo_weights"])
    data_yaml = project_path(args.data or cfg["paths"]["yolo_data"])

    if not weights.exists():
        raise FileNotFoundError(
            f"Missing trained YOLO checkpoint: {weights}. "
            "Train YOLO first so mAP can be measured truthfully."
        )
    if not data_yaml.exists():
        raise FileNotFoundError(
            f"Missing YOLO validation config: {data_yaml}. "
            "Create YOLO-format train/val images and labels first."
        )

    requested_device = str(cfg.get("yolo", {}).get("device", "auto")).lower()
    if requested_device in ("auto", "", "none"):
        device = 0 if torch.cuda.is_available() else "cpu"
    elif requested_device in ("cuda", "gpu", "0"):
        device = 0 if torch.cuda.is_available() else "cpu"
    else:
        device = requested_device

    model = YOLO(str(weights))
    metrics = model.val(
        data=str(data_yaml),
        imgsz=cfg.get("yolo", {}).get("img_size", 320),
        conf=cfg.get("yolo", {}).get("conf_threshold", 0.5),
        iou=cfg.get("yolo", {}).get("iou_threshold", 0.5),
        device=device,
        project=cfg["paths"]["logs"],
        name="yolo_eval",
        exist_ok=True,
    )

    print("\n[YOLO Summary]")
    print(f"mAP50    : {metrics.box.map50:.4f}")
    print(f"mAP50-95 : {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall   : {metrics.box.mr:.4f}")


if __name__ == "__main__":
    main()
