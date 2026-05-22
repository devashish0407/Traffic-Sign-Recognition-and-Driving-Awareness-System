"""Preview a sample video with OpenCV."""

import argparse
from pathlib import Path

import cv2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="assets/samples/test.mp4")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {Path(args.source)}")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("End of stream.")
            break

        cv2.imshow("video", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
