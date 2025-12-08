import argparse
import os
import cv2
import sys
from ultralytics import YOLO
from datetime import datetime


def count_people_in_video(video_path, model_path="yolov5nu.pt", timestamp=1, interval=1, limit=10):
    print(f"Analyzing {video_path}")

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Discarding")
        raise FileNotFoundError(f"動画ファイルを開けませんでした: {video_path}")

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    for i in range(limit):
        target_frame = int(fps * (timestamp+interval*i))
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

        ret, frame = cap.read()
        if not ret:
            print("Discarding")
            raise ValueError("指定されたフレームを取得できませんでした。")

        model = YOLO(model_path)
        detection_results = model(frame)
        person_count = sum(1 for obj in detection_results[0].boxes if obj.cls == 0)
        if person_count != 0:
            cap.release()
            print(f"Found {person_count} person at {timestamp+interval*i}s mark, keeping")
            return

    cap.release()
    print("Discarding")
    return


def main():
    parser = argparse.ArgumentParser(description="動画内の人数をYOLOでカウントして保存")
    parser.add_argument("--input_video", required=True, help="入力動画ファイルのパス")
    parser.add_argument("--model", default="yolov5nu.pt", help="YOLOのモデルパス")
    parser.add_argument("--timestamp", type=int, default=10, help="解析開始時点（秒）")
    parser.add_argument("--interval", type=int, default=10, help="解析間隔（秒）")
    parser.add_argument("--limit", type=int, default=5, help="解析回数")
    args = parser.parse_args()

    count_people_in_video(args.input_video,
                          args.model, args.timestamp, args.interval, args.limit)


if __name__ == "__main__":
    main()
