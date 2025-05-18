import argparse
import cv2
import os
from datetime import datetime


def compress_video(input_path, output_path, target_width, target_height, target_fps=30):
    cap = cv2.VideoCapture(input_path)

    if not cap.isOpened():
        raise FileNotFoundError(f"動画ファイルを開けませんでした: {input_path}")

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
    parser = argparse.ArgumentParser(description="動画の解像度を変更して保存")
    parser.add_argument("--input_video", required=True, help="入力動画ファイルのパス")
    parser.add_argument("--output_dir", required=True, help="出力ディレクトリ")
    parser.add_argument("--width", type=int, default=640, help="出力動画の幅")
    parser.add_argument("--height", type=int, default=360, help="出力動画の高さ")
    parser.add_argument("--fps", type=int, default=12, help="出力動画のフレームレート")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    return compress_video(args.input_video, args.output_dir, args.width, args.height, args.fps)


if __name__ == "__main__":
    main()
