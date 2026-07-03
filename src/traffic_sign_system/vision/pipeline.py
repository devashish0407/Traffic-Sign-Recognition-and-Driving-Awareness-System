"""Real-time inference pipeline from frame source to annotated output.

Only two things changed from the original version:
  1. iter_frames() gained a stream-ID guard so page-reloads or source
     switches don't leave a zombie generator running.
  2. iter_frames() creates a fresh per-session PipelineLogger instead of
     re-using self.logger (which self.logger.close() had already destroyed).
Everything else – _process_frame, run(), HazardEngine, FPS math – is
byte-for-byte identical to the original.
"""

import os
import queue
import threading
import time

import torch

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
        self.target_fps  = inf.get("target_fps", 30)
        self.cam_index   = inf.get("camera_index", 0)
        self.buf_size    = inf.get("frame_buffer_size", 1)
        self.frame_skip  = inf.get("classification_frame_skip", 2)

        # Optimize CPU threads for container deployment to prevent thread contention
        self.is_container = (os.environ.get("SPACE_ID") is not None) or os.path.exists("/.dockerenv")
        if self.is_container:
            torch.set_num_threads(2)
            print("[Pipeline] Running in container. Capped PyTorch threads to 2.")

        # Cache for intermediate frame predictions to boost FPS on CPU
        self._cached_detections = []
        self._cached_alerts = []
        self._cached_timings = {
            "detect_ms": 0.0,
            "classify_ms": 0.0,
            "hazard_ms": 0.0,
            "total_ms": 0.0,
        }

        yolo_w = cfg["paths"]["yolo_weights"]
        cnn_w  = cfg["paths"]["cnn_weights"]

        self.detector     = TrafficSignDetector(yolo_w, cfg)
        self.classifier   = TrafficSignClassifier(cnn_w, cfg)
        self.preprocessor = FramePreprocessor(cfg["cnn"]["img_size"])
        self.hazard       = HazardEngine(cfg)

        # Dynamically set detection frame skip based on hardware:
        # If CPU-only, default to 4-frame skip to maintain high FPS. If GPU is available, default to 1 (no skip).
        is_cpu = (self.detector.device == "cpu")
        default_skip = 4 if is_cpu else 1
        self.detection_frame_skip = inf.get("detection_frame_skip", default_skip)
        print(f"[Pipeline] Inference device: {self.detector.device}. Detection frame skip set to: {self.detection_frame_skip}")

        # self.logger is used only by run() (OpenCV window mode).
        # iter_frames() creates its own per-session logger so close() on one
        # session never corrupts the next.
        self.logger = PipelineLogger(cfg["paths"]["logs"])

        self.running = False
        self._frame_queue: queue.Queue = queue.Queue(maxsize=self.buf_size)
        self._latest_annotated: np.ndarray = None
        self._last_alerts = []
        self._stats = {
            "fps":          0.0,
            "detections":   0,
            "frame_count":  0,
            "current_dets": [],
            # --- dashboard-only bookkeeping (no effect on window mode) --------
            "stream_active": False,
            "video_ended":   False,
        }
        self._session = self._new_session()

        # Stream-ID guard: prevents a stale generator from the previous
        # /video_feed request from writing into _stats at the same time as
        # the new one.
        self._stream_id   = 0
        self._stream_lock = threading.Lock()
        self.paused = False

    # ------------------------------------------------------------------
    @staticmethod
    def _new_session() -> dict:
        return {
            "started_at":  None,
            "ended_at":    None,
            "frames":      0,
            "sign_hits":   0,
            "alert_counts": {"critical": 0, "warning": 0, "info": 0},
            "label_counts": {},
            "fps_samples": [],
        }

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    def _process_frame(self, frame: np.ndarray):
        total_start = time.perf_counter()
        is_file = getattr(self, "is_file_source", False)
        resize_dim = (416, 312) if is_file else (640, 480)
        frame = cv2.resize(frame, resize_dim)

        frame_count = self._stats["frame_count"]
        # Skip detection/classification on intermediate frames to maintain high FPS on CPU
        run_full_inference = (
            self.detection_frame_skip <= 1 or 
            frame_count % self.detection_frame_skip == 0 or 
            frame_count == 0
        )

        if run_full_inference:
            detect_start = time.perf_counter()
            detections   = self.detector.detect(frame)
            detect_ms    = (time.perf_counter() - detect_start) * 1000.0

            classified   = []
            classify_ms  = 0.0
            for det in detections:
                if self.frame_skip > 1 and frame_count % self.frame_skip != 0:
                    classified.append(det)
                    continue
                tensor = self.preprocessor.preprocess_crop(frame, det["bbox"])
                if tensor is None:
                    continue
                classify_start = time.perf_counter()
                result         = self.classifier.classify(tensor)
                classify_ms   += (time.perf_counter() - classify_start) * 1000.0
                det["class_id"]  = result["class_id"]
                det["confidence"] = result["confidence"]
                det["label"]     = SIGN_LABELS.get(result["class_id"], "Unknown")
                det["top_k"]     = result["top_k"]
                classified.append(det)

            hazard_start = time.perf_counter()
            alerts       = self.hazard.update(classified)
            hazard_ms    = (time.perf_counter() - hazard_start) * 1000.0

            self._cached_detections = classified
            self._cached_alerts = alerts
            self._cached_timings = {
                "detect_ms":   detect_ms,
                "classify_ms": classify_ms,
                "hazard_ms":   hazard_ms,
                "total_ms":    (time.perf_counter() - total_start) * 1000.0,
            }
        else:
            classified = self._cached_detections
            alerts     = self._cached_alerts
            detect_ms    = 0.0
            classify_ms  = 0.0
            hazard_ms    = 0.0

        annotated = TrafficSignDetector.draw_detections(frame, classified, alerts)
        annotated = self._overlay_hud(annotated, classified, alerts)

        if run_full_inference:
            timings = self._cached_timings
        else:
            timings = {
                "detect_ms":   detect_ms,
                "classify_ms": classify_ms,
                "hazard_ms":   hazard_ms,
                "total_ms":    (time.perf_counter() - total_start) * 1000.0,
            }
        return annotated, classified, alerts, timings

    # ------------------------------------------------------------------
    def iter_frames(self, source=None, session_id=None):
        """
        Main frame generator for the Flask video stream.

        ``source`` is either None (use configured camera_index) or an
        absolute path to an uploaded video file.  Behaviour when source=None
        is identical to the original implementation.
        """
        # --- 1. Claim this stream slot, shut down any previous generator ------
        with self._stream_lock:
            self.running = False          # signal old generator to exit its loop
            self._stream_id += 1
            my_id = self._stream_id

        time.sleep(0.10)                  # brief pause so old loop can notice

        # --- 2. Open capture --------------------------------------------------
        active_source = source if source is not None else self.cam_index
        self.is_file_source = (source is not None)
        
        cap = cv2.VideoCapture(active_source)
        
        # If webcam (index 0) fails to open, try fallback sources
        if not cap.isOpened() and active_source == 0:
            print("[Pipeline] WARNING: Cannot open default webcam (index 0). Trying index 1...")
            cap = cv2.VideoCapture(1)
            
            if not cap.isOpened():
                # Fall back to any uploaded video file to simulate the live feed
                from traffic_sign_system.paths import project_path
                upload_dir = project_path("artifacts/uploads")
                fallback_videos = sorted(
                    upload_dir.glob("*.mp4"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )
                if fallback_videos:
                    fallback_source = str(fallback_videos[0])
                    print(f"[Pipeline] Webcam failed. Simulating live camera feed using uploaded video: {fallback_source}")
                    cap = cv2.VideoCapture(fallback_source)
                    self.is_file_source = True
                else:
                    print("[Pipeline] No uploaded video files found for fallback.")

        if not cap.isOpened():
            print(f"[Pipeline] ERROR: Cannot open video source: {active_source!r}")
            # Yield a clean offline placeholder frame to the browser instead of crashing the HTTP stream
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            placeholder[:] = (26, 17, 13) # dark background matching theme
            cv2.putText(placeholder, "VIDEO SOURCE OFFLINE / CAMERA ERROR", (50, 220),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (90, 90, 220), 2, cv2.LINE_AA)
            cv2.putText(placeholder, "Please upload a video or connect a webcam.", (80, 260),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)
            success, encoded = cv2.imencode(".jpg", placeholder)
            if success:
                yield encoded.tobytes()
            self.running = False
            return

        # --- 3. Fresh per-session logger (avoids "I/O on closed file" crash) --
        session_logger = PipelineLogger(self.cfg["paths"]["logs"], session_id=session_id)

        # --- 4. Reset stats ---------------------------------------------------
        self._session = self._new_session()
        self._session["started_at"] = time.time()
        self._stats.update({
            "fps":          0.0,
            "frame_count":  0,
            "detections":   0,
            "current_dets": [],
            "stream_active": True,
            "video_ended":   False,
        })
        self._last_alerts = []

        self.running  = True
        self.paused   = False
        prev_time     = time.time()
        frame_idx     = 0

        try:
            while self.running and self._stream_id == my_id:
                if self.paused:
                    time.sleep(0.1)
                    continue
                
                frame_start = time.time()
                ret, frame = cap.read()
                if not ret:
                    break                 # natural end of file / camera closed

                frame_idx += 1
                # Skip alternate frames for video files to hit 16-18 FPS
                if self.is_file_source and frame_idx % 2 != 0:
                    continue

                annotated, dets, alerts, timings = self._process_frame(frame)

                self._stats["frame_count"] += 1
                self._stats["detections"]   = len(dets)
                self._stats["current_dets"] = dets
                self._last_alerts           = alerts
                self._latest_annotated      = annotated

                session_logger.log_frame(
                    self._stats["frame_count"], dets, alerts,
                    self._stats["fps"], timings,
                )
                self._record_session(dets, alerts)

                ok, encoded = cv2.imencode(".jpg", annotated)
                if ok:
                    yield encoded.tobytes()

                # Calculate processing duration and sleep only for the remaining time
                elapsed = time.time() - frame_start
                if self.is_file_source:
                    video_fps = cap.get(cv2.CAP_PROP_FPS)
                    if video_fps <= 0:
                        video_fps = 25.0
                    
                    # Target 16-18+ FPS by setting the target processed frame rate
                    frame_delay = 2.0 / video_fps
                    if frame_delay > 1.0 / 22.0:
                        frame_delay = 1.0 / 22.0
                        
                    sleep_time = frame_delay - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                        elapsed = time.time() - frame_start

                if elapsed > 0:
                    self._stats["fps"] = (0.9 * self._stats["fps"]
                                          + 0.1 * (1.0 / elapsed))

        finally:
            # Only the currently-active generator marks the stream as ended.
            if self._stream_id == my_id:
                self.running = False
                self._stats["stream_active"] = False
                self._stats["video_ended"]   = True
                self._session["ended_at"]    = time.time()
            cap.release()
            session_logger.close()

    # ------------------------------------------------------------------
    def _record_session(self, dets, alerts):
        s = self._session
        s["frames"]    += 1
        s["sign_hits"] += len(dets)
        s["fps_samples"].append(self._stats["fps"])
        for d in dets:
            lbl = d.get("label", "Unknown")
            s["label_counts"][lbl] = s["label_counts"].get(lbl, 0) + 1
        for a in alerts:
            lvl = a.get("level", "info")
            if lvl in s["alert_counts"]:
                s["alert_counts"][lvl] += 1

    def get_session_summary(self):
        s = self._session
        end      = s["ended_at"] or time.time()
        duration = round(end - s["started_at"], 1) if s["started_at"] else None
        avg_fps  = (round(sum(s["fps_samples"]) / len(s["fps_samples"]), 1)
                    if s["fps_samples"] else 0.0)
        top_labels = sorted(s["label_counts"].items(),
                            key=lambda kv: kv[1], reverse=True)[:8]
        return {
            "duration_sec":       duration,
            "frames_processed":   s["frames"],
            "sign_hits":          s["sign_hits"],
            "avg_fps":            avg_fps,
            "alert_counts":       dict(s["alert_counts"]),
            "top_labels":         top_labels,
        }

    def get_stats(self):
        stats = dict(self._stats)
        stats["alerts"] = list(self._last_alerts)
        return stats

    # ------------------------------------------------------------------
    def _overlay_hud(self, frame, detections, alerts):
        cv2.putText(frame, f"FPS: {self._stats['fps']:.1f}", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        if alerts:
            top = alerts[0]
            cv2.putText(frame, top["message"], (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        return frame

    # ------------------------------------------------------------------
    def run(self):
        """OpenCV-window mode (--mode window).  Unchanged from original."""
        cap = cv2.VideoCapture(self.cam_index)
        if not cap.isOpened():
            raise RuntimeError("Cannot open source")

        self.running = True
        threading.Thread(target=self._camera_reader, args=(cap,),
                         daemon=True).start()
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

                now     = time.time()
                elapsed = now - prev_time
                if elapsed > 0:
                    self._stats["fps"] = (0.9 * self._stats["fps"]
                                          + 0.1 * (1.0 / elapsed))
                prev_time = now

                self._stats["frame_count"] += 1
                self._stats["detections"]   = len(dets)
                self._stats["current_dets"] = dets
                self._last_alerts           = alerts
                self._latest_annotated      = annotated

                self.logger.log_frame(
                    self._stats["frame_count"], dets, alerts,
                    self._stats["fps"], timings,
                )

                cv2.imshow("Traffic System", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        finally:
            self.running = False
            cap.release()
            cv2.destroyAllWindows()
            self.logger.close()
