"""YOLOv8-based traffic sign detector for training and inference."""

import shutil
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np
import torch
import yaml
from ultralytics import YOLO

from traffic_sign_system.paths import project_path


class TrafficSignDetector:
    """
    Wraps YOLOv8 for:
      - Training on a custom annotated traffic sign dataset.
      - Real-time inference on video frames.
    """

    def __init__(self, weights_path: str = None, cfg: dict = None):
        self.cfg = cfg or {}

        yolo_cfg = self.cfg.get("yolo", {})
        inference_cfg = self.cfg.get("inference", {})

        self.conf_threshold = yolo_cfg.get("conf_threshold", 0.45)
        self.iou_threshold = yolo_cfg.get("iou_threshold", 0.50)
        self.img_size = yolo_cfg.get("img_size", 640)

        self.device = self._resolve_device(yolo_cfg.get("device", "auto"))

        # ✅ FIX: FP16 now controlled ONLY by config
        self.use_half = inference_cfg.get("fp16", False)

        weights = project_path(weights_path) if weights_path else None

        if weights and weights.exists():
            print(f"[Detector] Loading weights: {weights}")
            self.model = YOLO(str(weights))
        else:
            base = yolo_cfg.get("base_model", "yolov8n.pt")
            base = project_path(base)
            print(f"[Detector] Loading base model: {base}")
            self.model = YOLO(str(base))

        # ✅ FIX: Safe precision handling
        if self.use_half:
            try:
                self.model.model.half()
                print("[Detector] Using FP16 (half precision)")
            except Exception as exc:
                print(f"[Detector] FP16 failed, falling back to FP32: {exc}")
                self.model.model.float()
                self.use_half = False
        else:
            self.model.model.float()
            print("[Detector] Using FP32 (full precision)")

        torch.backends.cudnn.benchmark = self.device != "cpu"

    @staticmethod
    def _resolve_device(requested_device):
        """Return a safe Ultralytics device value for the current machine."""
        if requested_device in (None, "", "auto"):
            return 0 if torch.cuda.is_available() else "cpu"

        requested = str(requested_device).strip().lower()

        if requested in ("cuda", "gpu", "0"):
            if torch.cuda.is_available():
                return 0
            print("[Detector] CUDA requested but unavailable; falling back to CPU.")
            return "cpu"

        if requested == "mps":
            return "mps" if torch.backends.mps.is_available() else "cpu"

        return requested_device

    def train(self, data_yaml: str, output_dir: str = "checkpoints/"):
        data_yaml = project_path(data_yaml)
        output_dir = project_path(output_dir)

        batch_size = self.cfg.get("yolo", {}).get("batch_size") or 16

        results = self.model.train(
            data=str(data_yaml),
            epochs=self.cfg.get("yolo", {}).get("epochs", 50),
            imgsz=self.img_size,
            batch=batch_size,
            device=self.device,
            project=str(output_dir),
            name="yolo_tsr",
            exist_ok=True,
            patience=self.cfg.get("yolo", {}).get("patience", 15),
            save=True,
            val=True,
        )

        best_pt = Path(output_dir) / "yolo_tsr" / "weights" / "best.pt"
        target_pt = project_path(
            self.cfg.get("paths", {}).get(
                "yolo_weights", "artifacts/checkpoints/yolo_tsr.pt"
            )
        )

        if best_pt.exists():
            target_pt.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(best_pt, target_pt)
            print(f"[Detector] Copied best weights to: {target_pt}")

        print(f"[Detector] Training complete. Best weights: {best_pt}")
        return results

    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Run inference on a single BGR frame.
        Returns list of dicts: {bbox, confidence, class_id, label}.
        """
        predict_args = {
            "source": frame,
            "imgsz": self.img_size,
            "conf": self.conf_threshold,
            "iou": self.iou_threshold,
            "device": self.device,
            "verbose": False,
        }
        if self.use_half:
            predict_args["half"] = True

        with torch.no_grad():
            results = self.model.predict(**predict_args)

        detections = []

        for r in results:
            if r.boxes is None:
                continue

            for box in r.boxes[:10]:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                label = r.names.get(cls, str(cls))

                detections.append({
                    "bbox": (x1, y1, x2, y2),
                    "confidence": conf,
                    "class_id": cls,
                    "label": label,
                })

        return detections

    @staticmethod
    def draw_detections(frame: np.ndarray, detections: list[dict],
                        hazards: list[dict] = None) -> np.ndarray:
        vis = frame.copy()
        hazard_map = {}

        if hazards:
            for h in hazards:
                cid = h.get("class_id")
                if cid is not None:
                    hazard_map.setdefault(cid, []).append(h)

        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
            cls_id = det["class_id"]
            conf = det["confidence"]
            label = det.get("label", str(cls_id))

            hz_list = hazard_map.get(cls_id, [])
            hz = hz_list[0] if hz_list else {}
            level = hz.get("level", "info")

            color = {
                "critical": (0, 0, 255),
                "warning": (0, 165, 255),
                "info": (0, 255, 0),
            }.get(level, (128, 128, 128))

            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)

            text = f"{label} {conf:.2f}"
            cv2.putText(
                vis,
                text,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )

        return vis

    @staticmethod
    def generate_data_yaml(train_path: str, val_path: str,
                           nc: int, names: list,
                           out: str = "data/yolo_data.yaml"):
        data = {
            "train": train_path,
            "val": val_path,
            "nc": nc,
            "names": names,
        }

        with open(out, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        print(f"[Detector] data.yaml written to {out}")