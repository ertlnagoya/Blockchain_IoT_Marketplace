import argparse
import os
import cv2
from ultralytics import YOLO
from datetime import datetime


def count_people_in_video(video_path, output_dir, model_path="yolov5nu.pt", timestamp=1):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video file: {video_path}")

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    target_frame = int(fps * timestamp)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

    ret, frame = cap.read()
    if not ret:
        raise ValueError("Could not retrieve the specified frame.")

    model = YOLO(model_path)
    detection_results = model(frame)
    person_count = sum(1 for obj in detection_results[0].boxes if obj.cls == 0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = os.path.join(output_dir, f"people_count_{timestamp}.txt")
    os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(f"Video: {os.path.basename(video_path)}\n")
        f.write(f"Detected people: {person_count}\n")

    cap.release()
    print(os.path.abspath(output_path))


def main():
    parser = argparse.ArgumentParser(description="Count people in a video with YOLO and save the result")
    parser.add_argument("--input_video", required=True, help="Path to input video file")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    parser.add_argument("--model", default="yolov5nu.pt", help="Path to YOLO model")
    parser.add_argument("--timestamp", type=int, default=1, help="Timestamp in seconds to analyze")
    args = parser.parse_args()

    count_people_in_video(args.input_video, args.output_dir, args.model, args.timestamp)


if __name__ == "__main__":
    main()
