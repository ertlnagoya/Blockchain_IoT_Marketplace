import argparse
import cv2
import os
from datetime import datetime


def extract_frame(video_path, output_dir, timestamp=1):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise FileNotFoundError(f"動画ファイルを開けませんでした: {video_path}")

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    target_frame = int(fps * timestamp)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

    ret, frame = cap.read()
    if ret:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = os.path.join(output_dir, f"frame_{timestamp}.jpg")
        os.makedirs(output_dir, exist_ok=True)
        cv2.imwrite(output_path, frame)
    else:
        raise ValueError("指定されたフレームを取得できませんでした。")

    cap.release()
    print(os.path.abspath(output_path))


def main():
    parser = argparse.ArgumentParser(description="指定した時点のフレームを画像として保存")
    parser.add_argument("--input_video", required=True, help="入力動画ファイルのパス")
    parser.add_argument("--output_dir", required=True, help="出力ディレクトリ")
    parser.add_argument("--timestamp", type=int, default=1, help="抽出する時点（秒）")
    args = parser.parse_args()

    return extract_frame(args.input_video, args.output_dir, args.timestamp)


if __name__ == "__main__":
    main()
