"""Evaluate the saved CNN classifier on the GTSRB test split."""

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from traffic_sign_system.evaluation.classifier import evaluate_classifier
from traffic_sign_system.paths import DEFAULT_CONFIG_PATH, project_path
from traffic_sign_system.vision.preprocessor import build_dataloaders, load_config


def main():
    parser = argparse.ArgumentParser(description="Evaluate CNN classifier metrics.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    _, val_loader = build_dataloaders(cfg)
    metrics = evaluate_classifier(cfg, val_loader, save_plots=not args.no_plots)

    print("\n[Summary]")
    print(f"Samples : {metrics['num_samples']}")
    print(f"Top-1   : {metrics['top1'] * 100:.2f}%")
    print(f"Top-5   : {metrics['top5'] * 100:.2f}%")
    print(f"JSON    : {project_path(cfg['paths']['logs']) / 'classifier_metrics.json'}")


if __name__ == "__main__":
    main()
