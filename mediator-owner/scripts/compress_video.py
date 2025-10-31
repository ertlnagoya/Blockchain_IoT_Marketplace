import argparse
import cv2
import os
from datetime import datetime


def compress_video(input_path, output_path, target_width, target_height, target_fps=30):
    cap = cv2.VideoCapture(input_path)

    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video file: {input_path}")

    original_fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_interval = max(1, original_fps // target_fps)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    file_path = os.path.join(output_path, f"compressed_{timestamp}.mp4")
    output = cv2.VideoWriter(
        file_path, fourcc, target_fps, (target_width, target_height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if int(cap.get(cv2.CAP_PROP_POS_FRAMES)) % frame_interval == 0:
            resized_frame = cv2.resize(frame, (target_width, target_height))
            output.write(resized_frame)

    cap.release()
    output.release()
    print(os.path.abspath(file_path))


def main():
    parser = argparse.ArgumentParser(description="Resize video and save")
    parser.add_argument("--input_video", required=True, help="Path to input video file")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    parser.add_argument("--width", type=int, default=640, help="Output video width")
    parser.add_argument("--height", type=int, default=360, help="Output video height")
    parser.add_argument("--fps", type=int, default=12, help="Output video frame rate")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    return compress_video(args.input_video, args.output_dir, args.width, args.height, args.fps)


if __name__ == "__main__":
    main()
