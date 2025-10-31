import argparse
import cv2
import os
from datetime import datetime


def extract_frame(video_path, output_dir, timestamp=1):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video file: {video_path}")

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    target_frame = int(fps * timestamp)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

    ret, frame = cap.read()
    if ret:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = os.path.join(output_dir, f"frame_{ts}.jpg")
        os.makedirs(output_dir, exist_ok=True)
        cv2.imwrite(output_path, frame)
    else:
        raise ValueError("Could not retrieve the specified frame.")

    cap.release()
    print(os.path.abspath(output_path))


def main():
    parser = argparse.ArgumentParser(description="Save the frame at the specified timestamp as an image")
    parser.add_argument("--input_video", required=True, help="Path to the input video file")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    parser.add_argument("--timestamp", type=int, default=1, help="Timestamp (seconds) to extract")
    args = parser.parse_args()

    return extract_frame(args.input_video, args.output_dir, args.timestamp)


if __name__ == "__main__":
    main()
