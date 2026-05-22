
This section reflects the newly added results in `artifacts/logs/`. The classifier metric file is `artifacts/logs/classifier_metrics.json`; runtime telemetry was measured from the meaningful session CSV files, especially the two newest full May 4 runs:

- `artifacts/logs/session_20260504_233332.csv`
- `artifacts/logs/session_20260504_233722.csv`

### Ground-Truth Classifier Results

The saved CNN classifier was measured on the GTSRB final test set with 12,630 labeled images across 43 classes.

| Metric | Result |
|---|---:|
| Test samples | 12,630 |
| Classes | 43 |
| Device used | CUDA |
| Top-1 accuracy | 99.01% |
| Top-5 accuracy | 99.81% |
| Macro precision | 99.01% |
| Macro recall | 97.96% |
| Macro F1 | 98.33% |
| Weighted precision | 99.04% |
| Weighted recall | 99.01% |
| Weighted F1 | 98.98% |
| Classes with perfect F1 | 10 / 43 |

### Weakest Classifier Classes

These are the lowest-F1 classes in the latest truthful classifier report.

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Pedestrians | 100.00% | 58.33% | 73.68% | 60 |
| End of speed limit (80km/h) | 100.00% | 86.00% | 92.47% | 150 |
| Beware of ice/snow | 93.67% | 98.67% | 96.10% | 150 |
| Bumpy road | 100.00% | 93.33% | 96.55% | 120 |
| Right-of-way at intersection | 93.93% | 99.52% | 96.65% | 420 |
| Double curve | 94.74% | 100.00% | 97.30% | 90 |
| End of no passing | 98.31% | 96.67% | 97.48% | 60 |
| End of all speed & passing limits | 95.24% | 100.00% | 97.56% | 60 |

### Latest Runtime Results

The newest complete May 4 runtime logs contain 3,408 frame rows.

| Runtime Metric | Result |
|---|---:|
| Rows analyzed | 3,408 |
| Average FPS | 40.34 FPS |
| Minimum FPS | 0.03 FPS |
| Maximum FPS | 51.54 FPS |
| Average top confidence | 0.5958 |
| Average detections per frame | 2.51 |
| Maximum detections in a frame | 10 |
| Average detector latency | 14.47 ms |
| Average classifier latency | 11.73 ms |
| Average hazard latency | 0.22 ms |
| Average total frame latency | 29.69 ms |
| Maximum total frame latency | 3003.45 ms |

### Runtime Hazard Distribution

| Hazard Level | Count |
|---|---:|
| None | 2,943 |
| Info | 312 |
| Warning | 117 |
| Critical | 36 |

### Updated Project Qualification Scorecard

| Category | Score | Evidence |
|---|---:|---|
| Project structure | 8 / 10 | Clear separation across vision, model, evaluation, telemetry, domain, and interface modules |
| Dataset readiness | 8 / 10 | GTSRB train/test assets are present with 43 classes |
| Classifier quality | 9 / 10 | Top-1 is 99.01%, Top-5 is 99.81%, weighted F1 is 98.98% |
| Detector readiness | 3 / 10 | Base YOLO model exists, but trained traffic-sign YOLO checkpoint and YOLO validation config are still missing |
| Runtime performance | 8 / 10 | Latest full logs average 40.34 FPS, above the 20 FPS target; startup spikes still affect min/max latency |
| Measurement/reproducibility | 8 / 10 | Classifier JSON, confusion matrix, evaluation scripts, and latency CSV logs exist |
| Deployment/demo readiness | 7 / 10 | Pipeline and dashboard are present; detector mAP still cannot be certified |
| Overall current quality | 7.3 / 10 | Strong classifier and runtime logs, but detector mAP remains the main truth gap |

### Updated Pass / Fail Against Targets

| Target | Required | Latest Result | Status |
|---|---:|---:|---|
| Classification Top-1 | >= 95% | 99.01% | Pass |
| Detection mAP@0.5 | >= 85% | Not measurable | Blocked by missing `artifacts/checkpoints/yolo_tsr.pt` and `data/yolo_data.yaml` |
| Real-time FPS | >= 20 FPS | 40.34 FPS average from latest full logs | Pass |
| Alert latency | < 200 ms | 29.69 ms average total frame latency | Pass on average; max spike is 3003.45 ms |
| Reproducible metrics | Required | JSON metrics and CSV telemetry present | Pass for CNN/runtime, pending for YOLO |

### Current Truth Result

The project now qualifies as a strong traffic-sign classification prototype: the CNN classifier passes the stated accuracy target on the labeled GTSRB final test set, and the newest runtime logs pass the average FPS and average latency targets. The one major unresolved truth result is detector mAP. That cannot be claimed until a trained traffic-sign YOLO checkpoint and YOLO validation dataset config exist locally.
