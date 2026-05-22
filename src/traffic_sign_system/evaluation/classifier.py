"""Classifier accuracy, confusion matrix, and per-class metric reporting."""

import torch
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import (classification_report, confusion_matrix,
                             accuracy_score, top_k_accuracy_score)

from traffic_sign_system.config.sign_classes import SIGN_LABELS
from traffic_sign_system.models.cnn_classifier import build_classifier
from traffic_sign_system.paths import project_path


def _safe_device(cfg: dict) -> torch.device:
    requested = str(cfg["cnn"].get("device", "auto")).lower()
    if requested in ("cuda", "gpu") and not torch.cuda.is_available():
        print("[Eval] CUDA requested but unavailable; using CPU.")
        return torch.device("cpu")
    if requested in ("auto", "", "none"):
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(requested)


def evaluate_classifier(cfg: dict, val_loader, save_plots: bool = True,
                        save_json: bool = True):
    device = _safe_device(cfg)
    num_classes = cfg["dataset"]["num_classes"]
    ckpt_path = project_path(cfg["paths"]["cnn_weights"])
    log_dir = project_path(cfg["paths"]["logs"])
    log_dir.mkdir(parents=True, exist_ok=True)

    model = build_classifier(
        backbone    = cfg["cnn"]["backbone"],
        num_classes = num_classes,
        pretrained  = False,
    ).to(device)
    try:
        state_dict = torch.load(ckpt_path, map_location=device, weights_only=True)
    except TypeError:
        state_dict = torch.load(ckpt_path, map_location=device)
    model.load_state_dict(state_dict)
    model.eval()

    all_preds, all_labels, all_probs = [], [], []

    with torch.no_grad():
        for imgs, labels in val_loader:
            imgs   = imgs.to(device)
            logits = model(imgs)
            probs  = torch.softmax(logits, dim=1)
            preds  = probs.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs  = np.array(all_probs)

    acc    = accuracy_score(all_labels, all_preds)
    top5   = top_k_accuracy_score(all_labels, all_probs, k=5)

    print(f"\n[Eval] Top-1 Accuracy : {acc:.4f} ({acc*100:.2f}%)")
    print(f"[Eval] Top-5 Accuracy : {top5:.4f} ({top5*100:.2f}%)")
    report = classification_report(
        all_labels, all_preds,
        target_names=[SIGN_LABELS[i] for i in range(num_classes)],
        zero_division=0,
        output_dict=True,
    )
    print("\n" + classification_report(
        all_labels, all_preds,
        target_names=[SIGN_LABELS[i] for i in range(num_classes)],
        zero_division=0,
    ))

    if save_plots:
        # Confusion matrix (normalised)
        cm = confusion_matrix(all_labels, all_preds, normalize="true")
        fig, ax = plt.subplots(figsize=(18, 16))
        sns.heatmap(cm, annot=False, fmt=".2f", cmap="Blues", ax=ax,
                    xticklabels=range(num_classes),
                    yticklabels=range(num_classes))
        ax.set_title("Normalised Confusion Matrix", fontsize=14)
        ax.set_xlabel("Predicted"); ax.set_ylabel("True")
        plt.tight_layout()
        plt.savefig(log_dir / "confusion_matrix.png", dpi=150)
        plt.close()
        print(f"[Eval] Confusion matrix saved to {log_dir / 'confusion_matrix.png'}")

    cm_raw = confusion_matrix(all_labels, all_preds)
    metrics = {
        "checkpoint": str(ckpt_path),
        "device": str(device),
        "num_samples": int(len(all_labels)),
        "num_classes": int(num_classes),
        "top1": float(acc),
        "top5": float(top5),
        "classification_report": report,
        "confusion_matrix": cm_raw.tolist(),
    }

    if save_json:
        out_path = log_dir / "classifier_metrics.json"
        with open(out_path, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"[Eval] Metrics JSON saved to {out_path}")

    return metrics
