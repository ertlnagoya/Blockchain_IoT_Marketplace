import argparse
import os
import cv2
from ultralytics import YOLO
from datetime import datetime


def count_people_in_video(video_path, output_dir, model_path="yolov5nu.pt", timestamp=1):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise FileNotFoundError(f"動画ファイルを開けませんでした: {video_path}")

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    target_frame = int(fps * timestamp)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

    ret, frame = cap.read()
    if not ret:
        raise ValueError("指定されたフレームを取得できませんでした。")

    model = YOLO(model_path)
    detection_results = model(frame)
    person_count = sum(1 for obj in detection_results[0].boxes if obj.cls == 0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = os.path.join(output_dir, f"people_count_{timestamp}.txt")
    os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(f"動画: {os.path.basename(video_path)}\n")
        f.write(f"検出人数: {person_count} 人\n")

    cap.release()
    print(os.path.abspath(output_path))


def main():
    parser = argparse.ArgumentParser(description="動画内の人数をYOLOでカウントして保存")
    parser.add_argument("--input_video", required=True, help="入力動画ファイルのパス")
    parser.add_argument("--output_dir", required=True, help="出力ディレクトリ")
    parser.add_argument("--model", default="yolov5nu.pt", help="YOLOのモデルパス")
    parser.add_argument("--timestamp", type=int, default=1, help="解析する時点（秒）")
    args = parser.parse_args()

    count_people_in_video(args.input_video, args.output_dir,
                          args.model, args.timestamp)


if __name__ == "__main__":
    main()
