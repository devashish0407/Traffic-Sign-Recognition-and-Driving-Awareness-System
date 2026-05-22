"""Train the YOLO detector and CNN classifier.

Usage:
    python scripts/train.py --mode yolo
    python scripts/train.py --mode cnn
    python scripts/train.py --mode all
"""

import argparse
from pathlib import Path
import sys

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from traffic_sign_system.evaluation.classifier import evaluate_classifier
from traffic_sign_system.models.cnn_classifier import ClassifierTrainer
from traffic_sign_system.paths import DEFAULT_CONFIG_PATH
from traffic_sign_system.vision.detector import TrafficSignDetector
from traffic_sign_system.vision.preprocessor import build_dataloaders, load_config


def train_yolo(cfg: dict):
    print("\n" + "=" * 55)
    print("  PHASE 1 - YOLO DETECTION TRAINING")
    print("=" * 55)
    detector = TrafficSignDetector(cfg=cfg)
    detector.train(
        data_yaml=cfg["paths"]["yolo_data"],
        output_dir=cfg["paths"]["checkpoints"],
    )


def train_cnn(cfg: dict):
    print("\n" + "=" * 55)
    print("  PHASE 2 - CNN CLASSIFIER TRAINING")
    print("=" * 55)
    train_loader, val_loader = build_dataloaders(cfg)
    trainer = ClassifierTrainer(cfg)
    history = trainer.train(train_loader, val_loader)

    print("\n[Train] Evaluating best checkpoint...")
    evaluate_classifier(cfg, val_loader)
    return history


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["yolo", "cnn", "all"], default="all")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    args = parser.parse_args()

    cfg = load_config(args.config)

    print(f"\n[Train] Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    print(f"[Train] Mode: {args.mode}")

    if args.mode in ("yolo", "all"):
        train_yolo(cfg)

    if args.mode in ("cnn", "all"):
        train_cnn(cfg)

    print("\nTraining complete. Checkpoints saved to:", cfg["paths"]["checkpoints"])


if __name__ == "__main__":
    main()
