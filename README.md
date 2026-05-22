# Traffic Sign Recognition and Driving Awareness System

This project is a real-time traffic sign recognition and hazard alerting system. It combines a YOLOv8 detector, a CNN traffic-sign classifier, OpenCV video processing, rule-based hazard prediction, telemetry logging, and an optional Flask dashboard.

The system can process a webcam feed or a video file, detect possible traffic signs, classify them into GTSRB traffic sign classes, display annotated output, raise driving-awareness alerts, and save runtime logs for later analysis.

## Main Features

- Real-time traffic sign detection from webcam or video input.
- CNN classifier trained for 43 GTSRB traffic sign classes.
- YOLOv8 detector wrapper for custom traffic sign detection training and inference.
- OpenCV window mode for local demo.
- Flask and Socket.IO dashboard mode with live video, detections, FPS, and alerts.
- Rule-based hazard engine for warning, critical, and informational alerts.
- CSV telemetry logging for FPS, detections, confidence, latency, and hazard level.
- Evaluation scripts for classifier metrics and YOLO validation when detector validation data is available.

## Project Structure

```text
traffic_sign_system-main/
+-- src/traffic_sign_system/
|   +-- config/          # YAML config and GTSRB class labels
|   +-- domain/          # Hazard rules and alert generation
|   +-- evaluation/      # Classifier evaluation and metrics helpers
|   +-- interfaces/      # Flask dashboard
|   +-- models/          # CNN classifier and trainer
|   +-- telemetry/       # Runtime CSV logger
|   +-- vision/          # YOLO detector, preprocessing, and pipeline
+-- scripts/             # Run, train, evaluate, and preview scripts
+-- data/                # Raw and processed datasets
+-- artifacts/           # Checkpoints, logs, plots, and model weights
+-- assets/              # Sample videos and media
+-- docs/                # Reports and project notes
+-- requirements.txt     # Python dependencies
+-- pyproject.toml       # Package metadata
```

## Requirements

Use Python 3.9 or newer.

Recommended system requirements:

- Python 3.9+
- pip
- Webcam or local video file for real-time demo
- CUDA-capable GPU is optional but recommended for faster training and inference

Python libraries used by this project include:

- `torch`
- `torchvision`
- `ultralytics`
- `opencv-python`
- `numpy`
- `pillow`
- `scikit-learn`
- `matplotlib`
- `pandas`
- `tqdm`
- `pyyaml`
- `tensorboard`
- `albumentations`
- `flask`
- `flask-socketio`
- `pyttsx3`
- `pygame`
- `seaborn`

All required Python packages are listed in `requirements.txt`.

## Installation

Clone or open the project folder, then install the dependencies.

```bash
cd traffic_sign_system-main
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install libraries:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you want to use the package in editable mode:

```bash
pip install -e .
```

## Dataset

The classifier is built around the GTSRB dataset with 43 traffic sign classes.

Expected local dataset/artifact locations:

```text
data/raw/gtsrb/
artifacts/checkpoints/
artifacts/logs/
```

The repository already contains local GTSRB files and generated artifacts. If the dataset is missing in another environment, the training/data-loading workflow can download or prepare the required GTSRB data depending on the configured loader.

The main configuration file is:

```text
src/traffic_sign_system/config/config.yaml
```

## How to Run the Project

### 1. Run With Webcam in OpenCV Window

```bash
python scripts/run.py
```

This opens the default camera configured in `config.yaml`. Press `q` to quit the OpenCV window.

### 2. Run With a Sample Video

```bash
python scripts/run.py --source example.mp4
```

### 3. Run the Web Dashboard

```bash
python scripts/run.py --mode dashboard
```

Open the dashboard in a browser:

```text
http://localhost:5000
```

### 4. Run Dashboard With Sample Video

```bash
python scripts/run.py --mode dashboard --source example.mp4
```

### 5. Use a Different Port

```bash
python scripts/run.py --mode dashboard --port 8080
```

Then open:

```text
http://localhost:8080
```

## Training

### Train CNN Classifier

```bash
python scripts/train.py --mode cnn
```

The trained classifier checkpoint is saved to:

```text
artifacts/checkpoints/cnn_classifier.pt
```

### Train YOLO Detector

```bash
python scripts/train.py --mode yolo
```

YOLO training requires a YOLO-format dataset configuration file:

```text
data/yolo_data.yaml
```

When training completes successfully, the best detector weights are copied to:

```text
artifacts/checkpoints/yolo_tsr.pt
```

### Train Both Models

```bash
python scripts/train.py --mode all
```

## Evaluation

### Evaluate CNN Classifier

```bash
python scripts/evaluate_cnn.py
```

To skip plot generation:

```bash
python scripts/evaluate_cnn.py --no-plots
```

Outputs:

```text
artifacts/logs/classifier_metrics.json
artifacts/logs/confusion_matrix.png
```

### Evaluate YOLO Detector

```bash
python scripts/evaluate_yolo.py
```

YOLO evaluation needs both:

```text
artifacts/checkpoints/yolo_tsr.pt
data/yolo_data.yaml
```

If either file is missing, detector mAP cannot be measured truthfully.

## Current Results

The saved CNN classifier was evaluated on the GTSRB final test set.

| Metric | Result |
|---|---:|
| Test samples | 12,630 |
| Classes | 43 |
| Top-1 accuracy | 99.01% |
| Top-5 accuracy | 99.81% |
| Macro precision | 99.01% |
| Macro recall | 97.96% |
| Macro F1-score | 98.33% |
| Weighted precision | 99.04% |
| Weighted recall | 99.01% |
| Weighted F1-score | 98.98% |

Runtime telemetry from the latest complete logged runs shows:

| Runtime Metric | Result |
|---|---:|
| Rows analyzed | 3,408 |
| Average FPS | 40.34 FPS |
| Average detections per frame | 2.51 |
| Maximum detections in one frame | 10 |
| Average detector latency | 14.47 ms |
| Average classifier latency | 11.73 ms |
| Average hazard latency | 0.22 ms |
| Average total frame latency | 29.69 ms |

Hazard distribution in the analyzed runtime logs:

| Hazard Level | Count |
|---|---:|
| None | 2,943 |
| Info | 312 |
| Warning | 117 |
| Critical | 36 |

Current project status:

- CNN classification target is passed with 99.01% Top-1 accuracy.
- Real-time processing target is passed with about 40 FPS average in the latest logs.
- Average frame latency is below 200 ms.
- YOLO detector mAP is not yet certified because a trained traffic-sign YOLO checkpoint and validation YAML are required for truthful measurement.

## Runtime Artifacts

Important generated files:

```text
artifacts/checkpoints/cnn_classifier.pt
artifacts/checkpoints/yolo_tsr.pt
artifacts/models/yolov8n.pt
artifacts/logs/classifier_metrics.json
artifacts/logs/confusion_matrix.png
artifacts/logs/session_*.csv
```

Note: if `artifacts/checkpoints/yolo_tsr.pt` is not present, the detector falls back to the configured base YOLO model. Train YOLO with a valid YOLO-format dataset to generate the custom traffic-sign detector checkpoint.

## System Workflow

```text
Video source / webcam
  -> YOLO detector finds candidate sign regions
  -> CNN classifier predicts GTSRB sign class
  -> Hazard engine applies alert rules and cooldown
  -> OpenCV window or Flask dashboard displays output
  -> Telemetry logger stores CSV runtime results
```

## Useful Configuration Options

Edit `src/traffic_sign_system/config/config.yaml` to change:

- Camera index or video source behavior
- YOLO confidence threshold and image size
- CNN image size, epochs, batch size, and learning rate
- Alert cooldown and audio/TTS settings
- Dashboard host and port
- Artifact, checkpoint, and log paths

## Troubleshooting

If the camera does not open, check the webcam index in `config.yaml` or pass a video path with `--source`.

If the dashboard starts but the browser cannot connect, try:

```bash
python scripts/run.py --mode dashboard --host 127.0.0.1 --port 5000
```

If `torch` or `ultralytics` installation is slow or fails, install a PyTorch build that matches your CPU/GPU environment, then run `pip install -r requirements.txt` again.

If YOLO evaluation fails, confirm that both `artifacts/checkpoints/yolo_tsr.pt` and `data/yolo_data.yaml` exist.
