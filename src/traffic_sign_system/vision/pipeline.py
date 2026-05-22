"""Real-time inference pipeline from frame source to annotated output."""

import queue
import threading
import time

import cv2
import numpy as np

from traffic_sign_system.config.sign_classes import SIGN_LABELS
from traffic_sign_system.domain.hazard_engine import HazardEngine
from traffic_sign_system.models.cnn_classifier import TrafficSignClassifier
from traffic_sign_system.telemetry.logger import PipelineLogger
from traffic_sign_system.vision.detector import TrafficSignDetector
from traffic_sign_system.vision.preprocessor import FramePreprocessor


class RealtimePipeline:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        inf = cfg.get("inference", {})
        self.target_fps = inf.get("target_fps", 30)
        self.cam_index = inf.get("camera_index", 0)
        self.buf_size = inf.get("frame_buffer_size", 1)
        self.frame_skip = inf.get("classification_frame_skip", 2)

        yolo_w = cfg["paths"]["yolo_weights"]
        cnn_w = cfg["paths"]["cnn_weights"]

        self.detector = TrafficSignDetector(yolo_w, cfg)
        self.classifier = TrafficSignClassifier(cnn_w, cfg)
        self.preprocessor = FramePreprocessor(cfg["cnn"]["img_size"])
        self.hazard = HazardEngine(cfg)
        self.logger = PipelineLogger(cfg["paths"]["logs"])

        self.running = False
        self._frame_queue: queue.Queue = queue.Queue(maxsize=self.buf_size)
        self._latest_annotated: np.ndarray = None
        self._last_alerts = []
        self._stats = {
            "fps": 0.0,
            "detections": 0,
            "frame_count": 0,
            "current_dets": [],
        }

    def _camera_reader(self, cap: cv2.VideoCapture):
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if video_fps <= 0:
            video_fps = 30

        frame_delay = 1.0 / video_fps

        while self.running:
            start_time = time.time()

            ret, frame = cap.read()
            if not ret:
                self.running = False
                break

            if not self._frame_queue.full():
                self._frame_queue.put(frame)

            elapsed = time.time() - start_time
            time.sleep(max(0, frame_delay - elapsed))

    def _process_frame(self, frame: np.ndarray):
        total_start = time.perf_counter()
        frame = cv2.resize(frame, (640, 480))

        detect_start = time.perf_counter()
        detections = self.detector.detect(frame)
        detect_ms = (time.perf_counter() - detect_start) * 1000.0

        classified = []
        classify_ms = 0.0
        for det in detections:
            if self.frame_skip > 1 and self._stats["frame_count"] % self.frame_skip != 0:
                classified.append(det)
                continue

            tensor = self.preprocessor.preprocess_crop(frame, det["bbox"])
            if tensor is None:
                continue

            classify_start = time.perf_counter()
            result = self.classifier.classify(tensor)
            classify_ms += (time.perf_counter() - classify_start) * 1000.0

            det["class_id"] = result["class_id"]
            det["confidence"] = result["confidence"]
            det["label"] = SIGN_LABELS.get(result["class_id"], "Unknown")
            det["top_k"] = result["top_k"]
            classified.append(det)

        hazard_start = time.perf_counter()
        alerts = self.hazard.update(classified)
        hazard_ms = (time.perf_counter() - hazard_start) * 1000.0

        annotated = TrafficSignDetector.draw_detections(frame, classified, alerts)
        annotated = self._overlay_hud(annotated, classified, alerts)

        timings = {
            "detect_ms": detect_ms,
            "classify_ms": classify_ms,
            "hazard_ms": hazard_ms,
            "total_ms": (time.perf_counter() - total_start) * 1000.0,
        }
        return annotated, classified, alerts, timings

    def iter_frames(self):
        """Yield JPEG frames for the dashboard stream."""
        cap = cv2.VideoCapture(self.cam_index)
        if not cap.isOpened():
            raise RuntimeError("Cannot open source")

        self.running = True
        prev_time = time.time()

        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break

                annotated, dets, alerts, timings = self._process_frame(frame)

                now = time.time()
                elapsed = now - prev_time
                if elapsed > 0:
                    self._stats["fps"] = 0.9 * self._stats["fps"] + 0.1 * (1.0 / elapsed)
                prev_time = now

                self._stats["frame_count"] += 1
                self._stats["detections"] = len(dets)
                self._stats["current_dets"] = dets
                self._last_alerts = alerts
                self._latest_annotated = annotated

                self.logger.log_frame(
                    self._stats["frame_count"],
                    dets,
                    alerts,
                    self._stats["fps"],
                    timings,
                )

                ok, encoded = cv2.imencode(".jpg", annotated)
                if ok:
                    yield encoded.tobytes()
        finally:
            self.running = False
            cap.release()
            self.logger.close()

    def get_stats(self):
        stats = dict(self._stats)
        stats["alerts"] = list(self._last_alerts)
        return stats

    def _overlay_hud(self, frame, detections, alerts):
        cv2.putText(frame, f"FPS: {self._stats['fps']:.1f}", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        if alerts:
            top = alerts[0]
            cv2.putText(frame, top["message"], (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        return frame

    def run(self):
        cap = cv2.VideoCapture(self.cam_index)
        if not cap.isOpened():
            raise RuntimeError("Cannot open source")

        self.running = True
        threading.Thread(target=self._camera_reader, args=(cap,), daemon=True).start()
        prev_time = time.time()

        print("[Pipeline] Running - press 'q' to quit")

        try:
            while self.running:
                try:
                    frame = self._frame_queue.get(timeout=1.0)
                except queue.Empty:
                    if not self.running:
                        break
                    continue

                annotated, dets, alerts, timings = self._process_frame(frame)

                now = time.time()
                elapsed = now - prev_time
                if elapsed > 0:
                    self._stats["fps"] = 0.9 * self._stats["fps"] + 0.1 * (1.0 / elapsed)
                prev_time = now

                self._stats["frame_count"] += 1
                self._stats["detections"] = len(dets)
                self._stats["current_dets"] = dets
                self._last_alerts = alerts
                self._latest_annotated = annotated

                self.logger.log_frame(
                    self._stats["frame_count"],
                    dets,
                    alerts,
                    self._stats["fps"],
                    timings,
                )

                cv2.imshow("Traffic System", annotated)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        finally:
            self.running = False
            cap.release()
            cv2.destroyAllWindows()
            self.logger.close()
